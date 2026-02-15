import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.db_models import User, Chat, Message
from app.models.messages import MessageCreate, MessageOut
from app.services.excel_agent import ExcelDataAgent
from app.services.sql_agent import SQLAgent
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import json
import os

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY not found in environment variables")
fernet = Fernet(
    ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
)

router = APIRouter()


@router.get("/messages/{chat_id}", response_model=list[MessageOut])
def get_chat_history(
    chat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )


@router.post("/messages/{chat_id}", response_model=MessageOut)
async def send_message(
    chat_id: UUID,
    msg_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat_history = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(6)
        .all()
    )

    history_str = ""
    for msg in reversed(chat_history):
        content = msg.content
        if str(msg.role) == "assistant":
            try:
                content_dict = json.loads(str(msg.content))
                content = content_dict.get("text", msg.content)
            except Exception as parse_err:
                print(f"DEBUG: Failed to parse assistant message content: {parse_err}")
        content = content[:300] + ("..." if len(content) > 300 else "")
        history_str += f"{msg.role.capitalize()}: {content}\n"

    user_msg = Message(chat_id=chat_id, role="user", content=msg_data.content)

    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    code_type = "python"

    if chat.file_id:
        path = "data/" + chat.file.file_path
        if os.path.exists(path) is False:
            raise HTTPException(
                status_code=404, detail="Data file not found on server."
            )
        agent = ExcelDataAgent(path)
    elif chat.connection_id:
        code_type = "sql"
        if not chat.connection.connection_string:
            raise HTTPException(status_code=404, detail="Connection details not found.")
        try:
            encrypted_conn_str = chat.connection.connection_string
            # Handle both string and bytes
            if isinstance(encrypted_conn_str, str):
                encrypted_conn_str = encrypted_conn_str.encode()
            decrypted_conn_str = fernet.decrypt(encrypted_conn_str).decode()
            print(f"DEBUG: Successfully decrypted connection string for chat {chat_id}")
        except Exception as decrypt_err:
            print(
                f"DEBUG: Failed to decrypt connection for chat {chat_id}: {type(decrypt_err).__name__}: {str(decrypt_err)}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Failed to decrypt connection: {str(decrypt_err)}",
            )

        print("DEBUG: decrypted conn str: ", decrypted_conn_str)
        try:
            agent = SQLAgent(decrypted_conn_str)
            print(f"DEBUG: Successfully initialized SQLAgent for chat {chat_id}")
        except Exception as agent_err:
            print(
                f"DEBUG: Failed to initialize SQLAgent for chat {chat_id}: {type(agent_err).__name__}: {str(agent_err)}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to database: {str(agent_err)}",
            )
    else:
        raise HTTPException(
            status_code=400, detail="Chat has no associated file or connection."
        )

    async def _event_generator():
        final_response = {"text": "", "steps": [], "code": None}

        try:
            for chunk in agent.answer(msg_data.content, history_str):
                yield chunk + "\n"

                try:
                    chunk_data = json.loads(chunk)
                    if chunk_data.get("type") == "final_result":
                        data = chunk_data.get("data", {})
                        final_response["text"] = data.get("text", "")
                        final_response["steps"] = data.get("steps", [])
                        final_response["code"] = data.get("code", None)

                except Exception as chunk_err:
                    print(f"DEBUG: Failed to parse chunk: {chunk_err}")

                # Tiny sleep to ensure the loop yields control
                await asyncio.sleep(0.01)

            with SessionLocal() as db_session:
                assistant_msg = Message(
                    chat_id=chat_id,
                    role="assistant",
                    content=json.dumps(
                        {
                            "text": final_response["text"],
                            "steps": final_response["steps"],
                            "code": final_response["code"],
                        }
                    ),
                    related_code={"type": code_type, "code": final_response["code"]},
                    steps=final_response["steps"],
                )
                db_session.add(assistant_msg)
                db_session.commit()
                db_session.refresh(assistant_msg)

                yield json.dumps({"type": "final", "message_id": str(assistant_msg.id)})

        except Exception as e:
            print(
                f"DEBUG: Exception in event generator for chat {chat_id}: {type(e).__name__}: {str(e)}"
            )
            import traceback

            traceback.print_exc()
            yield json.dumps({"type": "error", "message": str(e)})

    return StreamingResponse(_event_generator(), media_type="application/x-ndjson")
