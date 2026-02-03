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
    return db.query(Chat).filter(Chat.user_id == current_user.id).all()