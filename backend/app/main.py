import logging
import os
import asyncio
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from alembic.config import Config
from alembic import command

from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.api.EDA import router as eda_router
from app.api.visualization import router as visualization_router
from app.api.preprocess import router as preprocess_router
from app.api.ml import router as ml_router
from app.api.dashboard import router as dashboard_router
from app.api.payments import router as payments_router
from app.api.coupons import router as coupons_router
from app.api.admin import router as admin_router
from app.api.diagnostics import router as diagnostics_router
from app.core.config import settings
from app.core.database import engine, Base
from app.core.limiter import limiter
from app.core.security_headers import SecurityHeadersMiddleware

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app):
    # Run any pending Alembic migrations on startup
    loop = asyncio.get_event_loop()
    alembic_cfg = Config("alembic.ini")
    await loop.run_in_executor(
        None, partial(command.upgrade, alembic_cfg, "head")
    )
    yield

# ── Production detection ─────────────────────────────────────
IS_PRODUCTION = os.getenv("RENDER") is not None or os.getenv("ENVIRONMENT") == "production"

# ── Rate limiter ─────────────────────────────────────────────
app = FastAPI(
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/api/docs",
    redoc_url=None if IS_PRODUCTION else "/api/redoc",
    openapi_url=None if IS_PRODUCTION else "/api/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS — allow_credentials=True requires explicit origins, not "*" ──
cors_origins = settings.cors_origins_list
render_url = os.getenv("RENDER_EXTERNAL_URL")
if render_url and render_url not in cors_origins:
    cors_origins.append(render_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers — applied after CORS so CORS headers are preserved
app.add_middleware(SecurityHeadersMiddleware)


# Register API routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(eda_router, prefix="/api/eda", tags=["eda"])
app.include_router(visualization_router, prefix="/api/visualization", tags=["visualization"])
app.include_router(preprocess_router, prefix="/api/preprocess", tags=["preprocess"])
app.include_router(ml_router, prefix="/api/ml", tags=["ml"])
app.include_router(dashboard_router)
app.include_router(payments_router)
app.include_router(coupons_router)
app.include_router(admin_router)
app.include_router(diagnostics_router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# ── Frontend serving ─────────────────────────────────────────
# Priority: backend/static (production build) > frontend/dist > frontend (dev)
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
frontend_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

active_frontend_dir = None

if os.path.exists(static_dir) and os.path.isfile(os.path.join(static_dir, "index.html")):
    active_frontend_dir = static_dir
    logger.info("Frontend serving from: %s (production build)", static_dir)
elif os.path.exists(frontend_dist_dir) and os.path.isfile(os.path.join(frontend_dist_dir, "index.html")):
    active_frontend_dir = frontend_dist_dir
    logger.info("Frontend serving from: %s", frontend_dist_dir)
elif os.path.exists(frontend_dir) and os.path.isfile(os.path.join(frontend_dir, "index.html")):
    active_frontend_dir = frontend_dir
    logger.info("Frontend serving from: %s (dev)", frontend_dir)
else:
    logger.warning("Frontend not found. Run 'cd frontend && npm run build' to build.")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve built frontend assets and fallback to index.html for SPA routes.
    """
    if not active_frontend_dir:
        raise HTTPException(
            status_code=404,
            detail="Frontend not built. Run: cd frontend && npm run build"
        )

    # API routes should 404 if they reach here (not handled by routers)
    api_prefixes = ("api/", "auth/", "dashboard/", "payments/", "coupons/", "admin/", "health")
    if any(full_path.startswith(p) or full_path == p.rstrip('/') for p in api_prefixes):
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