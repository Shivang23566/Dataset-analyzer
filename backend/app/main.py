from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.api.EDA import router as eda_router
from app.api.visualization import router as visualization_router
from app.core.database import engine, Base
import os
    
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Register API routers first
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(eda_router, prefix="/api/eda", tags=["eda"])
app.include_router(visualization_router, prefix="/api/visualization", tags=["visualization"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

# Frontend serving configuration
# Check for built React app first (dist folder), fallback to frontend root.
frontend_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

active_frontend_dir = None

if os.path.exists(frontend_dist_dir):
    active_frontend_dir = frontend_dist_dir
    print(f"[OK] Frontend active directory: {frontend_dist_dir}")
elif os.path.exists(frontend_dir):
    active_frontend_dir = frontend_dir
    print(f"[OK] Frontend active directory: {frontend_dir}")
else:
    print(f"[WARN] Frontend directory not found at {frontend_dir} or {frontend_dist_dir}")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve built frontend assets and fallback to index.html for SPA routes.
    """
    if not active_frontend_dir:
        raise HTTPException(status_code=404, detail="Frontend not available")

    # Avoid intercepting API endpoints if route ordering changes in future edits.
    if full_path.startswith("api/") or full_path.startswith("auth/"):
        raise HTTPException(status_code=404, detail="Not Found")

    requested = full_path.lstrip("/")
    if requested:
        candidate = os.path.abspath(os.path.join(active_frontend_dir, requested))

        # Block path traversal and serve actual files directly.
        if os.path.commonpath([active_frontend_dir, candidate]) == active_frontend_dir and os.path.isfile(candidate):
            return FileResponse(candidate)

    index_file = os.path.join(active_frontend_dir, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Frontend index not found")