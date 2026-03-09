from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.eda_engine import analyze_dataset
from app.api import deps
from app.api.file_utils import load_df
from app.models.user import User

router = APIRouter()

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
    try:
        df = load_df(request.filename, current_user.id)
        result = analyze_dataset(df)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
