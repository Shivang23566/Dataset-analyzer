import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.database import get_db
from app.core.path_security import (
    sanitize_filename,
    get_user_directory,
    InvalidFilenameError,
    PathTraversalError,
)
from app.models.user import User
from app.models.dataset import Dataset

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security.upload")
router = APIRouter()

UPLOAD_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "datasets")
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".json"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
CHUNK_SIZE = 1024 * 1024           # 1 MB streaming chunks


@router.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
    _: User = Depends(deps.check_dataset_limit),
    db: AsyncSession = Depends(get_db),
):
    try:
        original_filename = sanitize_filename(file.filename or "upload")
    except (InvalidFilenameError, PathTraversalError) as exc:
        security_logger.warning(
            "UPLOAD_FILENAME_REJECTED | user=%s | filename='%s' | reason=%s",
            current_user.id, file.filename, exc,
        )
        raise HTTPException(status_code=400, detail="Invalid filename")

    _, extension = os.path.splitext(original_filename)

    if extension.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{extension}' not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Build per-user directory to isolate files
    user_dir = str(get_user_directory(UPLOAD_FOLDER, current_user.id))

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
        # Stream file to disk in chunks to avoid loading entire file into memory
        total_size = 0
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    f.close()
                    os.unlink(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB.",
                    )
                f.write(chunk)

        if total_size == 0:
            os.unlink(file_path)
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Upload to Cloudinary for persistent cloud storage
        cloudinary_public_id = None
        if settings.USE_CLOUDINARY and settings.CLOUDINARY_CLOUD_NAME:
            try:
                from app.core.cloudinary_config import upload_to_cloudinary

                public_id = f"datalens/datasets/{current_user.id}/{saved_filename}"
                # Read back from disk for Cloudinary (avoids keeping in memory)
                with open(file_path, "rb") as cf:
                    content = cf.read()
                upload_result = upload_to_cloudinary(content, public_id)
                cloudinary_public_id = upload_result["public_id"]
                logger.info("Uploaded %s to Cloudinary", saved_filename)
            except Exception as exc:
                logger.warning("Cloudinary upload failed (local copy kept): %s", exc)

        # After file is saved to disk, record it in database
        dataset_id = None
        try:
            dataset_record = Dataset(
                user_id=current_user.id,
                original_filename=file.filename or "upload",
                saved_filename=saved_filename,
                storage_path=cloudinary_public_id or str(file_path),
                file_size_bytes=total_size,
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
