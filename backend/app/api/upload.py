import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api import deps
from app.models.user import User

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

    if os.path.exists(file_path):
        name, ext = os.path.splitext(original_filename)
        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(user_dir, new_filename)
            if not os.path.exists(file_path):
                original_filename = new_filename
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

        return {
            "message": "File uploaded successfully",
            "saved_as": original_filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=str(e))
