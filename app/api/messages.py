import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.db_models import User, Chat, Message
from app.models.messages import MessageCreate, MessageOut
from app.services.agent import DataAgent
import json
import os

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
async def send_message(
    chat_id: UUID,
    msg_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    chat_history = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.desc()).limit(6).all()
    
    history_str = ""
    for msg in reversed(chat_history):
        content = msg.content
        if str(msg.role) == "assistant":
            try:
                content_dict = json.loads(str(msg.content))
                content = content_dict.get("text", msg.content)
            except:
                pass
        content = content[:300] + ("..." if len(content) > 300 else "")
        history_str += f"{msg.role.capitalize()}: {content}\n"


    user_msg = Message(
        chat_id=chat_id,
        role="user",
        content=msg_data.content
    )
        
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    path = "data/" + chat.file.file_path
    if os.path.exists(path) is False:
        raise HTTPException(status_code=404, detail="Data file not found on server.")

    agent = DataAgent(path)

    async def _event_generator():
        final_response = {
            "text": "",
            "steps": [],
            "code": None
        }

        try:
            for chunk in agent.answer(msg_data.content, history_str):
                yield chunk + "\n"

                try:
                    chunk_data = json.loads(chunk)
                    final_response['text'] = chunk_data['data'].get('text', "")
                    final_response['steps'] = chunk_data['data'].get('steps', [])
                    final_response['code'] = chunk_data['data'].get('code', None)

                except:
                    pass

                # Tiny sleep to ensure the loop yields control
                await asyncio.sleep(0.01)

            with SessionLocal() as db_session:
                assistant_msg = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=json.dumps({
                        "text": final_response['text'],
                        "steps": final_response['steps'],
                        "code": final_response['code']
                    }),
                    related_code={
                        "type": "python",
                        "code":final_response['code']
                    },
                    steps=final_response['steps']
                )
                db_session.add(assistant_msg)
                db_session.commit()
                db_session.refresh(assistant_msg)

                yield json.dumps({
                    "type": "final",
                    "message_id": assistant_msg.id
                })

        except Exception as e:
            yield json.dumps({
                "type": "error",
                "message": str(e)
            })
    
    return StreamingResponse(_event_generator(), media_type="application/x-ndjson")

    