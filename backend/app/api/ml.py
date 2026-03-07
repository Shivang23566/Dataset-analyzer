"""
ML Builder API endpoints
POST /api/ml/columns        → Get columns for target selection
POST /api/ml/detect-task    → Auto-detect task type
POST /api/ml/recommend      → AI model recommendation
POST /api/ml/cards          → Get model cards for the task
POST /api/ml/train          → Train selected model
GET  /api/ml/download/{key} → Download trained model pickle
GET  /api/ml/inference-code/{key} → Get inference code snippet
GET  /api/ml/model-card/{key}     → Get model card markdown
"""
import os
import io
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
import pandas as pd

from app.api import deps
from app.models.user import User
from app.services.ml_engine import (
    detect_task_type,
    recommend_model,
    get_model_cards,
    train_model as _train_model,
    export_model_pickle,
    generate_inference_code,
    generate_model_card_md,
)

router = APIRouter()

UPLOAD_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets")
)


def _load_df(filename: str) -> pd.DataFrame:
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    if filename.endswith(".csv"):
        return pd.read_csv(path)
    elif filename.endswith(".json"):
        return pd.read_json(path)
    raise HTTPException(status_code=400, detail="Unsupported file format")


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
    current_user: User = Depends(deps.get_current_active_user),
):
    """Return column metadata for target selection."""
    df = _load_df(request.filename)
    import numpy as np
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
    current_user: User = Depends(deps.get_current_active_user),
):
    """Auto-detect ML task type from the target column."""
    df = _load_df(request.filename)
    try:
        return detect_task_type(df, request.target_col)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend")
async def recommend(
    request: RecommendRequest,
    current_user: User = Depends(deps.get_current_active_user),
):
    """Get AI model recommendation for the dataset."""
    df = _load_df(request.filename)
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
    current_user: User = Depends(deps.get_current_active_user),
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
    current_user: User = Depends(deps.get_current_active_user),
):
    """Train the selected model and return evaluation metrics."""
    df = _load_df(request.filename)
    config = {
        "model_id": request.model_id,
        "target_col": request.target_col,
        "task": request.task,
        "hyperparams": request.hyperparams,
        "auto_tune": request.auto_tune,
        "cv_folds": request.cv_folds,
        "test_size": request.test_size,
        "random_state": request.random_state,
    }
    try:
        result = _train_model(df, config)
        if not result.get("success"):
            raise HTTPException(status_code=422, detail=result.get("error", "Training failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{session_key}")
async def download_model(
    session_key: str,
    current_user: User = Depends(deps.get_current_active_user),
):
    """Download trained model as a pickle file."""
    pkl_bytes = export_model_pickle(session_key)
    if pkl_bytes is None:
        raise HTTPException(status_code=404, detail="Model not found. Train a model first.")
    return StreamingResponse(
        io.BytesIO(pkl_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=model_{session_key}.pkl"},
    )


@router.get("/inference-code/{session_key}", response_class=PlainTextResponse)
async def inference_code(
    session_key: str,
    current_user: User = Depends(deps.get_current_active_user),
):
    """Return Python inference code snippet for the trained model."""
    code = generate_inference_code(session_key)
    if not code:
        raise HTTPException(status_code=404, detail="Model session not found")
    return code


@router.get("/model-card/{session_key}", response_class=PlainTextResponse)
async def model_card(
    session_key: str,
    current_user: User = Depends(deps.get_current_active_user),
):
    """Return model card markdown for the trained model."""
    md = generate_model_card_md(session_key)
    if md == "Model not found":
        raise HTTPException(status_code=404, detail="Model session not found")
    return md
