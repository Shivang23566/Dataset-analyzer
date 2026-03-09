import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.api.EDA import router as eda_router
from app.api.visualization import router as visualization_router
from app.api.preprocess import router as preprocess_router
from app.api.ml import router as ml_router
from app.core.config import settings
from app.core.database import engine, Base
from app.core.limiter import limiter

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate limiter ─────────────────────────────────────────────
app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS — allow_credentials=True requires explicit origins, not "*" ──
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Register API routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(eda_router, prefix="/api/eda", tags=["eda"])
app.include_router(visualization_router, prefix="/api/visualization", tags=["visualization"])
app.include_router(preprocess_router, prefix="/api/preprocess", tags=["preprocess"])
app.include_router(ml_router, prefix="/api/ml", tags=["ml"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# ── Frontend serving ─────────────────────────────────────────
frontend_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

active_frontend_dir = None

if os.path.exists(frontend_dist_dir):
    active_frontend_dir = frontend_dist_dir
    logger.info("Frontend active directory: %s", frontend_dist_dir)
elif os.path.exists(frontend_dir):
    active_frontend_dir = frontend_dir
    logger.info("Frontend active directory: %s", frontend_dir)
else:
    logger.warning("Frontend directory not found at %s or %s", frontend_dir, frontend_dist_dir)


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve built frontend assets and fallback to index.html for SPA routes.
    """
    if not active_frontend_dir:
        raise HTTPException(status_code=404, detail="Frontend not available")

    if full_path.startswith("api/") or full_path.startswith("auth/"):
        raise HTTPException(status_code=404, detail="Not Found")

    requested = full_path.lstrip("/")
    if requested:
        candidate = os.path.abspath(os.path.join(active_frontend_dir, requested))

        if os.path.commonpath([active_frontend_dir, candidate]) == active_frontend_dir and os.path.isfile(candidate):
            return FileResponse(candidate)

    index_file = os.path.join(active_frontend_dir, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Frontend index not found")