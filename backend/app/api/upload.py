from fastapi import APIRouter, UploadFile, File, HTTPException
import os

router = APIRouter()

UPLOAD_FOLDER = r"D:\Dataset_analyser\datasets"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):

    original_filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, original_filename)

    if os.path.exists(file_path):
        name, extension = os.path.splitext(original_filename)
        counter = 1

        while True:
            new_filename = f"{name}_{counter}{extension}"
            file_path = os.path.join(UPLOAD_FOLDER, new_filename)

            if not os.path.exists(file_path):
                original_filename = new_filename
                break

            counter += 1

    try:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        with open(file_path, "wb") as f:
            f.write(content)

        return {
            "message": "File uploaded successfully",
            "saved_as": original_filename
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
