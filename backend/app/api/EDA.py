from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.eda_engine import analyze_dataset
from app.api import deps
from app.api.file_utils import load_df
from app.models.user import User
from app.core.database import get_db
from app.api.tracking import record_session, generate_session_key

router = APIRouter()

class AnalysisRequest(BaseModel):
    filename: str

@router.post("/analyze")
async def analyze_data(
    request: AnalysisRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a specific dataset file.
    """
    try:
        df = load_df(request.filename, current_user.id)
        result = analyze_dataset(df)

        # Track this session (non-critical — wrapped in try/except)
        try:
            summary = {
                "filename": request.filename,
                "rows": result.get("shape", {}).get("rows"),
                "columns": result.get("shape", {}).get("columns"),
            }
            await record_session(
                db=db,
                user_id=current_user.id,
                session_key=generate_session_key("eda"),
                session_type="eda",
                filename=request.filename,
                result_summary=summary,
            )
        except Exception:
            pass

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
