from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import pandas as pd
import os
import traceback
from typing import Optional
from app.services.visualization_engine import generate_visualization
from app.api import deps
from app.models.user import User

router = APIRouter()

# Define the path where datasets are stored
UPLOAD_FOLDER = r"D:\Dataset_analyser\datasets"

class VisualizationRequest(BaseModel):
    filename: str
    chart_type: str
    x_column: str
    y_column: Optional[str] = None

class ColumnRequest(BaseModel):
    filename: str

@router.post("/columns")
async def get_columns(
    request: ColumnRequest,
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get column metadata including names and data types (numeric vs categorical).
    Used for smart column filtering in visualization dropdowns.
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
        
        # Classify columns by type
        numeric_columns = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
        
        # Build column metadata
        columns = []
        for col in df.columns:
            col_type = 'numeric' if col in numeric_columns else 'categorical'
            columns.append({
                'name': col,
                'type': col_type,
                'dtype': str(df[col].dtype)
            })
        
        return {
            'columns': columns,
            'numeric_columns': numeric_columns,
            'categorical_columns': categorical_columns
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
    Generate a visualization for a specific dataset file.
    """
    print(f"Visualization request: {request.dict()}")
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
        
        # Generates visualization data
        print(f"Calling generate_visualization with: chart_type={request.chart_type}, x={request.x_column}, y={request.y_column}")
        result = generate_visualization(
            df, 
            request.chart_type, 
            request.x_column, 
            request.y_column
        )
        
        print(f"Visualization result: success={result.get('success')}, chart_type={result.get('chart_type')}")
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            print(f"ERROR: Visualization failed: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        print(f"Returning successful result")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /generate: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
