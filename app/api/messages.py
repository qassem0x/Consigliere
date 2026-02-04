from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.db_models import User, Chat, Message
from app.models.messages import MessageCreate, MessageOut
from app.services.agent import DataAgent
import json

router = APIRouter()

@router.get("/messages/{chat_id}", response_model=list[MessageOut])
def get_chat_history(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()


@router.post("/messages/{chat_id}", response_model=MessageOut)
def send_message(
    chat_id: UUID,
    msg_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_msg = Message(
        chat_id=chat_id,
        role="user",
        content=msg_data.content
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    path = "data/" + chat.file.file_path
    agent = DataAgent(path)
    
    answer = agent.answer(msg_data.content)
    
    assistant_msg = Message(
        chat_id=chat_id,
        role="assistant",
        content=json.dumps(answer)
    )

    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg