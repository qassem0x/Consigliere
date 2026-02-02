from fastapi import APIRouter, UploadFile, File
import shutil
from app.services.ingestion import process_file

router = APIRouter()

@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    path = f"data/{file.filename}"
    with open(path, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)

    metadata = process_file(file_path=path)
    return {"message": "File Uploaded Sucessfully", "data": metadata}
