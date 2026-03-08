from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import traceback
import json
from typing import Optional
from app.services.chart_engine import get_chart_engine
from app.api import deps
from app.models.user import User

router = APIRouter()

# Define the path where datasets are stored
UPLOAD_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets")
)

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
    Returns inferred types, statistics, and sample values for smart column filtering.
    """
    file_path = os.path.join(UPLOAD_FOLDER, request.filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Load the dataset
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.json'):
            df = pd.read_json(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Use new profiling system
        engine = get_chart_engine()
        columns = engine.get_column_profiles(df)
        
        # Sanitize column metadata to ensure JSON compliance
        columns = sanitize_for_json(columns)
        
        # Group by inferred type for convenience
        numeric_columns = [c['column_name'] for c in columns if c['inferred_type'] == 'numeric']
        categorical_columns = [c['column_name'] for c in columns if c['inferred_type'] == 'categorical']
        datetime_columns = [c['column_name'] for c in columns if c['inferred_type'] == 'datetime']
        high_cardinality = [c['column_name'] for c in columns if c['inferred_type'] == 'high_cardinality']
        
        # Clean preview data to handle NaN/Inf values
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
        
    except Exception as e:
        print(f"ERROR in /columns: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def create_visualization(
    request: VisualizationRequest,
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Generate a visualization using the new ChartEngine system.
    Includes automatic validation, profiling, and performance optimization.
    """
    print(f"Visualization request: {request.dict()}")
    print(f"DEBUG: x_column='{request.x_column}', y_column='{request.y_column}', chart_type='{request.chart_type}'")
    
    # BUG FIX 3: Validate input parameters BEFORE processing
    if not request.x_column or request.x_column.strip() == "":
        print("ERROR: X axis column is empty - validation failed")
        raise HTTPException(status_code=400, detail="X axis column must be selected before generating")
    
    # Validate Y column for chart types that require it
    charts_requiring_y = ["bar", "line", "scatter", "pie", "boxplot"]
    if request.chart_type in charts_requiring_y:
        if not request.y_column or request.y_column.strip() == "":
            print(f"ERROR: Y axis column is empty for chart type {request.chart_type}")
            raise HTTPException(status_code=400, detail=f"Y axis column must be selected for {request.chart_type} charts")
    
    file_path = os.path.join(UPLOAD_FOLDER, request.filename)
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Load the dataset
        print(f"Loading dataset from: {file_path}")
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.json'):
            df = pd.read_json(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        print(f"Dataset loaded. Shape: {df.shape}, Columns: {list(df.columns)}")
        
        # BUG FIX 3: Validate columns exist in dataset
        if request.x_column not in df.columns:
            print(f"ERROR: Column '{request.x_column}' not found in dataset")
            raise HTTPException(status_code=400, detail=f"Column '{request.x_column}' not found in dataset")
        
        if request.y_column and request.y_column not in df.columns:
            print(f"ERROR: Column '{request.y_column}' not found in dataset")
            raise HTTPException(status_code=400, detail=f"Column '{request.y_column}' not found in dataset")
        
        # Use new ChartEngine system
        engine = get_chart_engine()
        result = engine.generate_chart(
            df=df,
            chart_type=request.chart_type,
            x_column=request.x_column,
            y_column=request.y_column
        )
        
        print(f"Visualization result: success={result.get('success')}")
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            print(f"ERROR: Visualization failed: {error_msg} (code: {error_code})")
            raise HTTPException(status_code=400, detail=error_msg)
        
        print(f"Returning successful result with metadata: {result.get('metadata')}")
        
        # Return response in expected format
        return {
            "success": True,
            "image": result["image"],
            "metadata": result.get("metadata", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /generate: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
