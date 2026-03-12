"""
ML Builder API endpoints
POST /api/ml/columns        -> Get columns for target selection
POST /api/ml/detect-task    -> Auto-detect task type
POST /api/ml/recommend      -> AI model recommendation
POST /api/ml/cards          -> Get model cards for the task
POST /api/ml/train          -> Train selected model
GET  /api/ml/download/{key} -> Download trained model
GET  /api/ml/inference-code/{key} -> Get inference code snippet
GET  /api/ml/model-card/{key}     -> Get model card markdown
"""
import io
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.file_utils import load_df
from app.models.user import User
from app.core.database import get_db
from app.api.tracking import record_session, record_download
from app.services.ml_engine import (
    detect_task_type,
    recommend_model,
    get_model_cards,
    train_model as _train_model,
    export_model_pickle,
    generate_inference_code,
    generate_model_card_md,
    cleanup_model_artifacts,
    get_model_owner,
)

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.ml")
router = APIRouter()


class FileRequest(BaseModel):
    filename: str


class TaskDetectRequest(BaseModel):
    filename: str
    target_col: str


class RecommendRequest(BaseModel):
    filename: str
    target_col: Optional[str] = None


class CardsRequest(BaseModel):
    task: str


class TrainRequest(BaseModel):
    filename: str
    model_id: str
    target_col: Optional[str] = None
    task: str
    hyperparams: Dict[str, Any] = {}
    auto_tune: bool = False
    cv_folds: int = 5
    test_size: float = 0.2
    random_state: int = 42


@router.post("/columns")
async def get_columns(
    request: FileRequest,
    current_user: User = Depends(deps.require_pro),
):
    """Return column metadata for target selection."""
    df = load_df(request.filename, current_user.id)
    cols = []
    for c in df.columns:
        dtype = str(df[c].dtype)
        is_numeric = pd.api.types.is_numeric_dtype(df[c])
        n_unique = int(df[c].nunique())
        cols.append({"name": c, "dtype": dtype, "is_numeric": is_numeric, "n_unique": n_unique})
    return {"columns": cols}


@router.post("/detect-task")
async def detect_task(
    request: TaskDetectRequest,
    current_user: User = Depends(deps.require_pro),
):
    """Auto-detect ML task type from the target column."""
    df = load_df(request.filename, current_user.id)
    try:
        return detect_task_type(df, request.target_col)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend")
async def recommend(
    request: RecommendRequest,
    current_user: User = Depends(deps.require_pro),
):
    """Get AI model recommendation for the dataset."""
    df = load_df(request.filename, current_user.id)
    try:
        task_info = {}
        if request.target_col:
            task_info = detect_task_type(df, request.target_col)
        else:
            task_info = {"task": "clustering"}
        rec = recommend_model(df, request.target_col, task_info)
        return {**rec, "task_info": task_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cards")
async def model_cards(
    request: CardsRequest,
    current_user: User = Depends(deps.require_pro),
):
    """Return model cards for the given task type."""
    try:
        cards = get_model_cards(request.task)
        return {"cards": cards}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train")
async def train(
    request: TrainRequest,
    current_user: User = Depends(deps.require_pro),
    db: AsyncSession = Depends(get_db),
):
    """Train the selected model and return evaluation metrics (runs in thread pool)."""
    df = load_df(request.filename, current_user.id)
    config = {
        "model_id": request.model_id,
        "target_col": request.target_col,
        "task": request.task,
        "hyperparams": request.hyperparams,
        "auto_tune": request.auto_tune,
        "cv_folds": request.cv_folds,
        "test_size": request.test_size,
        "random_state": request.random_state,
        "user_id": current_user.id,
    }
    try:
        # Run CPU-bound training in a thread pool to avoid blocking the event loop
        result = await asyncio.to_thread(_train_model, df, config)
        if not result.get("success"):
            raise HTTPException(status_code=422, detail=result.get("error", "Training failed"))

        # Track this session (non-critical — wrapped in try/except)
        try:
            summary = {
                "filename": request.filename,
                "model_name": result.get("model_name"),
                "task_type": result.get("task_type"),
                "accuracy": result.get("metrics", {}).get("accuracy")
                    or result.get("metrics", {}).get("r2_score"),
                "session_key": result.get("session_key"),
            }
            await record_session(
                db=db,
                user_id=current_user.id,
                session_key=result.get("session_key", ""),
                session_type="ml",
                filename=request.filename,
                result_summary=summary,
            )
        except Exception:
            pass

        return result
    except HTTPException:
        raise
    except Exception as e:
        # Clean up partial model artifacts on training failure
        session_key = None
        try:
            # If training partially succeeded and stored artifacts, clean them up
            if 'result' in locals() and isinstance(result, dict):
                session_key = result.get("session_key")
            if session_key:
                cleanup_model_artifacts(session_key)
                logger.warning("Cleaned up artifacts for failed session: %s", session_key)
        except Exception as cleanup_err:
            logger.warning("Artifact cleanup failed: %s", cleanup_err)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{session_key}")
async def download_model(
    session_key: str,
    current_user: User = Depends(deps.require_pro),
    db: AsyncSession = Depends(get_db),
):
    """Download trained model as a joblib file."""
    # Ownership check
    owner_id = get_model_owner(session_key)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Model not found. Train a model first.")
    if owner_id != current_user.id:
        security_logger.warning(
            "MODEL_ACCESS_DENIED | user=%s | owner=%s | session_key=%s",
            current_user.id, owner_id, session_key,
        )
        raise HTTPException(status_code=403, detail="Access denied")

    pkl_bytes = export_model_pickle(session_key)
    if pkl_bytes is None:
        raise HTTPException(status_code=404, detail="Model not found. Train a model first.")

    # Track this download (non-critical — wrapped in try/except)
    try:
        await record_download(
            db=db,
            user_id=current_user.id,
            session_id=None,
            file_type="model",
            original_filename=f"model_{session_key}.joblib",
            stored_path=f"store/model_{session_key}.joblib",
        )
    except Exception:
        pass

    return StreamingResponse(
        io.BytesIO(pkl_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=model_{session_key}.joblib"},
    )


@router.get("/inference-code/{session_key}", response_class=PlainTextResponse)
async def inference_code(
    session_key: str,
    current_user: User = Depends(deps.require_pro),
):
    """Return Python inference code snippet for the trained model."""
    owner_id = get_model_owner(session_key)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Model session not found")
    if owner_id != current_user.id:
        security_logger.warning(
            "MODEL_ACCESS_DENIED | user=%s | owner=%s | session_key=%s",
            current_user.id, owner_id, session_key,
        )
        raise HTTPException(status_code=403, detail="Access denied")
    code = generate_inference_code(session_key)
    if not code:
        raise HTTPException(status_code=404, detail="Model session not found")
    return code


@router.get("/model-card/{session_key}", response_class=PlainTextResponse)
async def model_card(
    session_key: str,
    current_user: User = Depends(deps.require_pro),
):
    """Return model card markdown for the trained model."""
    owner_id = get_model_owner(session_key)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Model session not found")
    if owner_id != current_user.id:
        security_logger.warning(
            "MODEL_ACCESS_DENIED | user=%s | owner=%s | session_key=%s",
            current_user.id, owner_id, session_key,
        )
        raise HTTPException(status_code=403, detail="Access denied")
    md = generate_model_card_md(session_key)
    if md == "Model not found":
        raise HTTPException(status_code=404, detail="Model session not found")
    return md
