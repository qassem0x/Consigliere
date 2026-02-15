import os
import uuid
import pandas as pd
import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.db_models import User, File as DBFile, Dossier, Chat
from app.services.excel_agent import ExcelDataAgent
from app.services.ingestion import _transform_to_parquet

router = APIRouter()


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".csv", ".xlsx"]:
        raise HTTPException(
            status_code=400, detail="Unsupported file format. Use CSV or Excel."
        )

    temp_filename = f"temp_{uuid.uuid4()}{file_ext}"
    os.makedirs("data", exist_ok=True)
    temp_path = f"data/{temp_filename}"

    # 2. Async Stream Write (Non-Blocking I/O)
    try:
        async with aiofiles.open(temp_path, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # 1MB Chunks
                await out_file.write(content)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail="File upload stream failed.")

    try:
        metadata = await run_in_threadpool(
            _transform_to_parquet, temp_path, file.filename
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

    new_file = DBFile(
        filename=file.filename,  # Original User Filename
        user_id=user.id,
        file_path=metadata["filename"],  # Optimized Parquet Filename
        row_count=metadata["rows"],
        columns=metadata["columns"],
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    # Returns exactly what you asked for
    return {
        "status": "uploaded",
        "file_id": str(new_file.id),
        "filename": new_file.filename,
    }


@router.post("/files/{file_id}/analyze")
def analyze_file(
    file_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    db_file = (
        db.query(DBFile).filter(DBFile.id == file_id, DBFile.user_id == user.id).first()
    )
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        full_path = f"data/{db_file.file_path}"
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=404, detail="Physical file missing on server."
            )

        agent = ExcelDataAgent(file_path=full_path)
        dossier_data = agent.generate_dossier()
        schema = agent.schema

    except Exception as e:
        print(f"AI Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI Analysis failed: {str(e)}")

    new_dossier = Dossier(
        file_id=db_file.id,
        briefing=dossier_data.get("briefing", "No briefing generated."),
        key_entities=dossier_data.get("key_entities", []),
        recommended_actions=dossier_data.get("recommended_actions", []),
    )
    db.add(new_dossier)
    db.commit()
    db.refresh(new_dossier)

    new_chat = Chat(
        user_id=user.id,
        file_id=db_file.id,
        dossier_id=new_dossier.id,
        title=f"Analysis: {db_file.filename}",
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return {"status": "complete", "chat_id": str(new_chat.id), "dossier": dossier_data}
