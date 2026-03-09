import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import pandas as pd
import numpy as np
from typing import Optional
from app.services.chart_engine import get_chart_engine
from app.api import deps
from app.api.file_utils import load_df
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class VisualizationRequest(BaseModel):
    filename: str
    chart_type: str
    x_column: str
    y_column: Optional[str] = None

class ColumnRequest(BaseModel):
    filename: str

def sanitize_for_json(obj):
    """Recursively sanitize data structure to be JSON-compliant"""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif pd.isna(obj):
        return None
    elif isinstance(obj, (pd.Timestamp, np.datetime64)):
        return str(obj)
    else:
        return obj

@router.post("/columns")
async def get_columns(
    request: ColumnRequest,
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get column metadata using comprehensive profiling system.
    """
    try:
        df = load_df(request.filename, current_user.id)

        engine = get_chart_engine()
        columns = engine.get_column_profiles(df)
        columns = sanitize_for_json(columns)

        numeric_columns = [c['column_name'] for c in columns if c['inferred_type'] == 'numeric']
        categorical_columns = [c['column_name'] for c in columns if c['inferred_type'] == 'categorical']
        datetime_columns = [c['column_name'] for c in columns if c['inferred_type'] == 'datetime']
        high_cardinality = [c['column_name'] for c in columns if c['inferred_type'] == 'high_cardinality']

        preview_data = df.head(100).replace([float('inf'), float('-inf')], None).fillna(None).to_dict('records')
        preview_data = sanitize_for_json(preview_data)

        return {
            'columns': columns,
            'numeric_columns': numeric_columns,
            'categorical_columns': categorical_columns,
            'datetime_columns': datetime_columns,
            'high_cardinality_columns': high_cardinality,
            'preview_data': preview_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /columns")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def create_visualization(
    request: VisualizationRequest,
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Generate a visualization using the ChartEngine system.
    """
    if not request.x_column or request.x_column.strip() == "":
        raise HTTPException(status_code=400, detail="X axis column must be selected before generating")

    charts_requiring_y = ["bar", "line", "scatter", "pie", "boxplot"]
    if request.chart_type in charts_requiring_y:
        if not request.y_column or request.y_column.strip() == "":
            raise HTTPException(status_code=400, detail=f"Y axis column must be selected for {request.chart_type} charts")

    try:
        df = load_df(request.filename, current_user.id)

        if request.x_column not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{request.x_column}' not found in dataset")

        if request.y_column and request.y_column not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{request.y_column}' not found in dataset")

        engine = get_chart_engine()
        result = engine.generate_chart(
            df=df,
            chart_type=request.chart_type,
            x_column=request.x_column,
            y_column=request.y_column
        )

        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(status_code=400, detail=error_msg)

        return {
            "success": True,
            "image": result["image"],
            "metadata": result.get("metadata", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /generate")
        raise HTTPException(status_code=500, detail=str(e))
