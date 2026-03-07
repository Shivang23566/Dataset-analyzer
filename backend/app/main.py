from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.openapi.docs import get_swagger_ui_html
from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.api.EDA import router as eda_router
from app.api.visualization import router as visualization_router
from app.core.database import engine, Base
import asyncio
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

# Mount frontend directory LAST
# Check for built React app first (dist folder), fallback to static frontend
frontend_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

if os.path.exists(frontend_dist_dir):
    app.mount("/", StaticFiles(directory=frontend_dist_dir, html=True), name="frontend")
    print(f"[OK] Frontend mounted from: {frontend_dist_dir}")
elif os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    print(f"[OK] Frontend mounted from: {frontend_dir}")
else:
    print(f"[WARN] Frontend directory not found at {frontend_dir} or {frontend_dist_dir}")