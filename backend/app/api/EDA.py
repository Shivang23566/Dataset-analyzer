from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import pandas as pd
import os
from app.services.eda_engine import analyze_dataset
from app.api import deps
from app.models.user import User

router = APIRouter()

# Define the path where datasets are stored (should match upload.py)
UPLOAD_FOLDER = r"D:\Dataset_analyser\datasets"

class AnalysisRequest(BaseModel):
    filename: str

@router.post("/analyze")
async def analyze_data(
    request: AnalysisRequest,
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Analyze a specific dataset file.
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
            
        # Perform analysis using the service
        result = analyze_dataset(df)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
