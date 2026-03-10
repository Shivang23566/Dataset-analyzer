import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.dataset import Dataset

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets")
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".json"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
    _: User = Depends(deps.check_dataset_limit),
    db: AsyncSession = Depends(get_db),
):
    original_filename = os.path.basename(file.filename or "upload")
    _, extension = os.path.splitext(original_filename)

    if extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{extension}' not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Build per-user directory to isolate files
    user_dir = os.path.join(UPLOAD_FOLDER, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, original_filename)
    saved_filename = original_filename

    if os.path.exists(file_path):
        name, ext = os.path.splitext(original_filename)
        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(user_dir, new_filename)
            if not os.path.exists(file_path):
                saved_filename = new_filename
                break
            counter += 1

    try:
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB.",
            )

        with open(file_path, "wb") as f:
            f.write(content)

        # After file is saved to disk, record it in database
        dataset_id = None
        try:
            dataset_record = Dataset(
                user_id=current_user.id,
                original_filename=file.filename or "upload",
                saved_filename=saved_filename,
                storage_path=str(file_path),
                file_size_bytes=len(content),
            )
            db.add(dataset_record)
            await db.commit()
            await db.refresh(dataset_record)
            dataset_id = dataset_record.id

            # Try to get row/column counts with pandas
            try:
                import pandas as pd
                if saved_filename.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif saved_filename.endswith('.json'):
                    df = pd.read_json(file_path)
                else:
                    df = None

                if df is not None:
                    dataset_record.row_count = len(df)
                    dataset_record.col_count = len(df.columns)
                    await db.commit()
            except Exception:
                pass  # metadata is optional, don't fail upload

        except Exception as db_error:
            logger.warning("Failed to record dataset in database: %s", db_error)
            # File is already saved, so don't fail the upload

        return {
            "message": "File uploaded successfully",
            "saved_as": saved_filename,
            "dataset_id": dataset_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=str(e))
