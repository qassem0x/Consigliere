import os
import uuid
import logging
import pandas as pd
import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.db_models import User, File as DBFile, Dossier, Chat, ChatSettings
from app.models.chats import ChatSettingsUpdate
from app.agents import ExcelAgent
from app.services.ingestion import _transform_to_parquet

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@router.post("/files/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".csv", ".xlsx"]:
        raise HTTPException(
            status_code=400, detail="Unsupported file format. Use CSV or Excel."
        )

    temp_filename = f"temp_{uuid.uuid4()}{file_ext}"
    os.makedirs("data", exist_ok=True)
    temp_path = f"data/{temp_filename}"

    total_size = 0
    try:
        async with aiofiles.open(temp_path, "wb") as out_file:
            while content := await file.read(1024 * 1024):
                total_size += len(content)
                if total_size > MAX_FILE_SIZE:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB",
                    )
                await out_file.write(content)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"File upload stream failed: {e}")
        raise HTTPException(status_code=500, detail="File upload stream failed.")

    try:
        metadata = await run_in_threadpool(
            _transform_to_parquet, temp_path, file.filename
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

    new_file = DBFile(
        filename=file.filename,
        user_id=user.id,
        file_path=metadata["filename"],
        row_count=metadata["rows"],
        columns=metadata["columns"],
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    logger.info(f"User {user.id} uploaded file {new_file.id}")

    return {
        "status": "uploaded",
        "file_id": str(new_file.id),
        "filename": new_file.filename,
    }


@router.post("/files/{file_id}/analyze")
async def analyze_file(
    file_id: str,
    settings: ChatSettingsUpdate = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
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

        agent = ExcelAgent(file_path=full_path, chat_settings=None)
        dossier_data = await run_in_threadpool(agent.generate_dossier)
        schema = agent.schema

    except Exception as e:
        logger.error(f"AI Error: {e}")
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
        title=(
            settings.title
            if settings and settings.title
            else f"Analysis: {db_file.filename}"
        ),
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    if settings:
        chat_settings = ChatSettings(
            chat_id=new_chat.id,
            zero_leaks_mode=settings.zero_leaks_mode,
            max_row_limit=settings.max_row_limit,
        )
        db.add(chat_settings)
        db.commit()

    return {"status": "complete", "chat_id": str(new_chat.id), "dossier": dossier_data}
