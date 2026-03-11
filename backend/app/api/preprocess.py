"""
Preprocessing API endpoints
POST /api/preprocess/health     -> Dataset health dashboard
POST /api/preprocess/recommend  -> Missing value recommendations
POST /api/preprocess/run        -> Run full pipeline
POST /api/preprocess/download   -> Download processed dataset
"""
import os
import io
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.file_utils import load_df, UPLOAD_FOLDER
from app.core.config import settings
from app.models.user import User
from app.core.database import get_db
from app.api.tracking import record_session, record_download, generate_session_key
from app.services.preprocessing_engine import (
    get_dataset_health,
    get_missing_recommendations,
    run_pipeline,
    store_processed_df,
    get_processed_df,
    export_dataframe,
    detect_outliers as _detect_outliers,
    step_train_test_split,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthRequest(BaseModel):
    filename: str


class PipelineRequest(BaseModel):
    filename: str
    config: Dict[str, Any] = {}


class DownloadRequest(BaseModel):
    session_key: str
    format: str = "csv"


class OutlierRequest(BaseModel):
    filename: str
    method: str = "iqr"
    threshold: float = 3.0


@router.post("/health")
async def dataset_health(
    request: HealthRequest,
    current_user: User = Depends(deps.require_pro),
):
    """Return health dashboard data for the uploaded dataset."""
    df = load_df(request.filename, current_user.id)
    try:
        health = get_dataset_health(df)
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend-imputation")
async def recommend_imputation(
    request: HealthRequest,
    current_user: User = Depends(deps.require_pro),
):
    """Return AI-recommended imputation strategies per column."""
    df = load_df(request.filename, current_user.id)
    try:
        return {"recommendations": get_missing_recommendations(df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-outliers")
async def detect_outliers_endpoint(
    request: OutlierRequest,
    current_user: User = Depends(deps.require_pro),
):
    """Detect outliers in the dataset."""
    df = load_df(request.filename, current_user.id)
    try:
        return {"outliers": _detect_outliers(df, method=request.method, threshold=request.threshold)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def run_preprocessing_pipeline(
    request: PipelineRequest,
    current_user: User = Depends(deps.require_pro),
    db: AsyncSession = Depends(get_db),
):
    """Run the full preprocessing pipeline on the uploaded dataset."""
    import hashlib, time, re

    df = load_df(request.filename, current_user.id)
    try:
        results, processed_df = run_pipeline(df, request.config)

        session_key = hashlib.md5(f"{request.filename}_{time.time()}".encode()).hexdigest()[:12]
        store_processed_df(session_key, processed_df)

        # Save processed CSV to the user's directory so ML feature can pick it up
        user_dir = os.path.join(UPLOAD_FOLDER, str(current_user.id))
        os.makedirs(user_dir, exist_ok=True)
        base = re.sub(r"\.[^.]+$", "", os.path.basename(request.filename))
        processed_filename = f"preprocessed_{base}.csv"
        processed_path = os.path.join(user_dir, processed_filename)
        processed_df.to_csv(processed_path, index=False)

        # Upload processed file to Cloudinary for persistence
        if settings.USE_CLOUDINARY and settings.CLOUDINARY_CLOUD_NAME:
            try:
                from app.core.cloudinary_config import upload_to_cloudinary

                processed_bytes = processed_df.to_csv(index=False).encode("utf-8")
                public_id = f"datalens/datasets/{current_user.id}/{processed_filename}"
                upload_to_cloudinary(processed_bytes, public_id)
                logger.info("Uploaded processed file %s to Cloudinary", processed_filename)
            except Exception as exc:
                logger.warning("Cloudinary upload of processed file failed: %s", exc)

        results["session_key"] = session_key
        results["processed_filename"] = processed_filename

        # Track this session (non-critical — wrapped in try/except)
        try:
            summary = {
                "filename": request.filename,
                "steps_applied": results.get("steps_applied", []),
                "rows_before": results.get("original_shape", {}).get("rows"),
                "rows_after": results.get("processed_shape", {}).get("rows"),
            }
            await record_session(
                db=db,
                user_id=current_user.id,
                session_key=generate_session_key("preprocess"),
                session_type="preprocessing",
                filename=request.filename,
                result_summary=summary,
            )
        except Exception:
            pass

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{session_key}")
async def download_processed(
    session_key: str,
    format: str = "csv",
    current_user: User = Depends(deps.require_pro),
    db: AsyncSession = Depends(get_db),
):
    """Download the processed dataset in the requested format."""
    df = get_processed_df(session_key)
    if df is None:
        raise HTTPException(status_code=404, detail="Processed dataset not found. Run the pipeline first.")
    try:
        data, media_type, ext = export_dataframe(df, format)
        filename = f"processed_dataset{ext}"

        # Track this download (non-critical — wrapped in try/except)
        try:
            await record_download(
                db=db,
                user_id=current_user.id,
                session_id=None,
                file_type="processed_csv",
                original_filename=filename,
                stored_path=f"processed_{session_key}{ext}",
            )
        except Exception:
            pass

        return StreamingResponse(
            io.BytesIO(data),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/columns")
async def get_columns(
    request: HealthRequest,
    current_user: User = Depends(deps.require_pro),
):
    """Return column list with dtypes for the dataset."""
    df = load_df(request.filename, current_user.id)
    cols = [{"name": c, "dtype": str(df[c].dtype), "missing_pct": round(float(df[c].isnull().mean() * 100), 2),
              "nunique": int(df[c].nunique())} for c in df.columns]
    return {"columns": cols}
