from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.db_models import User, File as DBFile, Dossier, Chat
from app.services.agent import DataAgent
from app.services.ingestion import process_file
import shutil

router = APIRouter()

@router.post("/files/upload")
def upload_file(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    path = f"data/{file.filename}"
    with open(path, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)

    metadata = process_file(file_path=path)

    new_file = DBFile(
        filename=file.filename,
        user_id=user.id,
        file_path=metadata['filename'],
        row_count=metadata['rows'],
        columns=metadata['columns']
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    return {
        "status": "uploaded", 
        "file_id": str(new_file.id), 
        "filename": new_file.filename,
    }

@router.post("/files/{file_id}/analyze")
def analyze_file(
    file_id: str, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    db_file = db.query(DBFile).filter(DBFile.id == file_id, DBFile.user_id == user.id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        agent = DataAgent(file_path=f"data/{db_file.file_path}")
        dossier_data = agent.generate_dossier()
    except Exception as e:
        print(f"AI Error: {e}")
        raise HTTPException(status_code=500, detail="AI Analysis failed")

    new_dossier = Dossier(
        file_id=db_file.id,
        file_type=dossier_data.get('file_type', 'Unknown'),
        briefing=dossier_data.get('briefing', ''),
        key_entities=dossier_data.get('key_entities', []),
        recommended_actions=dossier_data.get('recommended_actions', [])
    )
    db.add(new_dossier)
    db.commit()
    db.refresh(new_dossier)

    new_chat = Chat(
        user_id=user.id,
        file_id=db_file.id,
        dossier_id=new_dossier.id,
        title=f"Analysis: {db_file.filename}"
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return {
        "status": "complete",
        "chat_id": str(new_chat.id),
        "dossier": dossier_data
    }