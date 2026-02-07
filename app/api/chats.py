from fastapi.routing import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.models.db_models import User
from app.models.chats import ChatCreate, ChatOut
from app.models.db_models import Chat, File
from app.core.database import get_db

router = APIRouter()


@router.post("/chats", response_model=ChatOut, status_code=201)
def create_chat(
    chat: ChatCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file = db.query(File).filter(File.id == chat.file_id, File.user_id == user.id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # NOTE: Title left as None, for default naming i'll do it in the frontend side
    
    new_chat = Chat(file_id=chat.file_id, user_id=user.id)

    try:
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        return new_chat
    except Exception:
        raise HTTPException(500)


@router.get("/chats", response_model=list[ChatOut])
def get_my_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.created_at.desc()).all()
    
    for chat in chats:
        chat.type = "excel"
        chat.title = chat.file.filename
    return chats 


@router.get("/chats/{chat_id}/dossier")
def get_chat_dossier(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    dossier = chat.dossier
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found for this chat")
    
    return {
        "file_type": dossier.file_type,
        "created_at": dossier.created_at,
        "briefing": dossier.briefing,
        "key_entities": dossier.key_entities,
        "recommended_actions": dossier.recommended_actions
    }

@router.delete("/chats/{chat_id}", status_code=204)
def delete_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    db.delete(chat)
    db.commit()

    # get file path to invalidate cache & delete from disk
    file_path = "data/" + chat.file.file_path
    if file_path:
        from app.services.cache import DataCache
        cache = DataCache()
        cache.invalidate(file_path)

        import os
        if os.path.exists(file_path):
            os.remove(file_path)