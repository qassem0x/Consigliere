from importlib.metadata import metadata
from fastapi import APIRouter, UploadFile, File, Depends
import shutil
from app.core.deps import get_current_user
from app.services.ingestion import process_file
from app.models.db_models import User, File as DBFile, Chat
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.agent import DataAgent

router = APIRouter()

@router.post("/upload")
def upload_file(file: UploadFile = File(...), 
                db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
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
    db.refresh(new_file) # To get the new file's ID and other info

    # create a chat
    chat = Chat(
        file_id=new_file.id,
        user_id=user.id,
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)

    dossier = None
    try:
        agent = DataAgent(file_path=f"data/{metadata['filename']}")
        dossier = agent.generate_dossier()
        print("Generated dossier:", dossier)
    except Exception as e:
        print(f"Error generating dossier: {e}")
        dossier = {
            "file_type": "Unprocessed Data",
            "briefing": "File uploaded successfully. AI analysis is pending.",
            "key_entities": [],
            "recommended_actions": []
        }

    return {"status": "success", "file_rows": new_file.row_count, "file_id": str(new_file.id), "metadata": metadata, "dossier": dossier, "chat_id": str(chat.id)}