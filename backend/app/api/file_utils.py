"""Shared file-loading utilities for API endpoints."""
import os
import logging

import pandas as pd
import requests
from fastapi import HTTPException

from app.core.config import settings
from app.core.path_security import (
    sanitize_filename,
    InvalidFilenameError,
    PathTraversalError,
)

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.file")

UPLOAD_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets")
)


def resolve_user_file(filename: str, user_id: int) -> str:
    """Return the absolute path for a file belonging to a specific user.

    Checks local disk first; falls back to downloading from Cloudinary
    when the file is missing locally (e.g. after an ephemeral-disk restart).
    """
    try:
        safe_name = sanitize_filename(filename)
    except (InvalidFilenameError, PathTraversalError) as exc:
        security_logger.warning(
            "FILENAME_REJECTED | user_id=%s | filename='%s' | reason=%s",
            user_id, filename, exc,
        )
        raise HTTPException(status_code=400, detail="Invalid filename")

    user_dir = os.path.join(UPLOAD_FOLDER, str(user_id))
    user_path = os.path.join(user_dir, safe_name)

    # Verify resolved path stays inside UPLOAD_FOLDER
    real_path = os.path.realpath(user_path)
    real_base = os.path.realpath(UPLOAD_FOLDER)
    if not real_path.startswith(real_base + os.sep):
        security_logger.error(
            "PATH_TRAVERSAL_BLOCKED | user_id=%s | resolved='%s'", user_id, real_path,
        )
        raise HTTPException(status_code=400, detail="Invalid file path")

    if os.path.isfile(user_path):
        return user_path

    # Cloudinary fallback
    if settings.USE_CLOUDINARY and settings.CLOUDINARY_CLOUD_NAME:
        try:
            from app.core.cloudinary_config import cloudinary_download_url

            public_id = f"datalens/datasets/{user_id}/{safe_name}"
            url = cloudinary_download_url(public_id)
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                os.makedirs(user_dir, exist_ok=True)
                with open(user_path, "wb") as fh:
                    fh.write(resp.content)
                logger.info("Downloaded %s from Cloudinary", safe_name)
                return user_path
        except Exception as exc:
            logger.warning("Cloudinary fallback failed for %s: %s", safe_name, exc)

    raise HTTPException(status_code=404, detail=f"File not found: {filename}")


def load_df(filename: str, user_id: int) -> pd.DataFrame:
    """Load a CSV or JSON file as a DataFrame, resolving via user isolation."""
    path = resolve_user_file(filename, user_id)
    if path.endswith(".csv"):
        return pd.read_csv(path)
    elif path.endswith(".json"):
        return pd.read_json(path)
    raise HTTPException(status_code=400, detail="Unsupported file format")
