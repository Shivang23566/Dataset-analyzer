"""
Persistent cache backends for ML models and DataFrames.
Supports file-based (dev/default) and Redis (production) backends.
"""
import hashlib
import io
import logging
import os
import pickle
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import joblib
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Abstract Backend ────────────────────────────────────────

class CacheBackend(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        ...

    @abstractmethod
    def set(self, key: str, value: bytes, ttl: int = 3600) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...


# ── File-based Backend ──────────────────────────────────────

class FileCacheBackend(CacheBackend):
    """Persists cache entries as files on disk. Survives server restarts."""

    def __init__(self, cache_dir: str):
        self._dir = os.path.abspath(cache_dir)
        os.makedirs(self._dir, exist_ok=True)

    def _path(self, key: str) -> str:
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return os.path.join(self._dir, safe_key)

    def _meta_path(self, key: str) -> str:
        return self._path(key) + ".meta"

    def get(self, key: str) -> Optional[bytes]:
        path = self._path(key)
        meta_path = self._meta_path(key)
        if not os.path.exists(path):
            return None
        # Check TTL
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    expires = float(f.read().strip())
                if time.time() > expires:
                    self.delete(key)
                    return None
            except Exception:
                pass
        with open(path, "rb") as f:
            return f.read()

    def set(self, key: str, value: bytes, ttl: int = 3600) -> None:
        path = self._path(key)
        with open(path, "wb") as f:
            f.write(value)
        with open(self._meta_path(key), "w") as f:
            f.write(str(time.time() + ttl))

    def delete(self, key: str) -> None:
        for p in (self._path(key), self._meta_path(key)):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass

    def exists(self, key: str) -> bool:
        return self.get(key) is not None


# ── Redis Backend ───────────────────────────────────────────

class RedisCacheBackend(CacheBackend):
    """Uses Redis for shared, scalable caching across workers."""

    def __init__(self, redis_url: str):
        import redis
        self._client = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[bytes]:
        return self._client.get(key)

    def set(self, key: str, value: bytes, ttl: int = 3600) -> None:
        self._client.setex(key, ttl, value)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def exists(self, key: str) -> bool:
        return bool(self._client.exists(key))


# ── High-level caches ──────────────────────────────────────

class ModelCache:
    """Serialize/deserialize ML models via joblib to a cache backend."""

    def __init__(self, backend: CacheBackend, default_ttl: int = 86400):
        self.backend = backend
        self.default_ttl = default_ttl

    def store_model(self, key: str, model: Any, metadata: dict, ttl: int | None = None) -> None:
        buf = io.BytesIO()
        joblib.dump({"model": model, "metadata": metadata}, buf)
        self.backend.set(f"model:{key}", buf.getvalue(), ttl or self.default_ttl)

    def get_model(self, key: str) -> Optional[Tuple[Any, dict]]:
        data = self.backend.get(f"model:{key}")
        if data is None:
            return None
        obj = joblib.load(io.BytesIO(data))
        return obj["model"], obj["metadata"]

    def delete_model(self, key: str) -> None:
        self.backend.delete(f"model:{key}")

    def exists(self, key: str) -> bool:
        return self.backend.exists(f"model:{key}")


class DataFrameCache:
    """Serialize DataFrames as Parquet to a cache backend."""

    def __init__(self, backend: CacheBackend, default_ttl: int = 3600):
        self.backend = backend
        self.default_ttl = default_ttl

    def store_df(self, key: str, df: pd.DataFrame, ttl: int | None = None) -> None:
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        self.backend.set(f"df:{key}", buf.getvalue(), ttl or self.default_ttl)

    def get_df(self, key: str) -> Optional[pd.DataFrame]:
        data = self.backend.get(f"df:{key}")
        if data is None:
            return None
        return pd.read_parquet(io.BytesIO(data))

    def delete_df(self, key: str) -> None:
        self.backend.delete(f"df:{key}")

    def exists(self, key: str) -> bool:
        return self.backend.exists(f"df:{key}")


# ── Factory ─────────────────────────────────────────────────

def _create_backend() -> CacheBackend:
    if settings.CACHE_BACKEND == "redis" and settings.REDIS_URL:
        try:
            backend = RedisCacheBackend(settings.REDIS_URL)
            logger.info("Using Redis cache backend")
            return backend
        except Exception as e:
            logger.warning("Redis unavailable, falling back to file cache: %s", e)
    logger.info("Using file cache backend at %s", settings.CACHE_DIR)
    return FileCacheBackend(settings.CACHE_DIR)


_backend = _create_backend()
model_cache = ModelCache(_backend, default_ttl=settings.MODEL_CACHE_TTL)
df_cache = DataFrameCache(_backend, default_ttl=settings.DF_CACHE_TTL)
