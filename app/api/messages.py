import asyncio
import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.core.config import ENCRYPTION_KEY, validate_env
from app.core.utils import sanitize_nan
from app.models.db_models import User, Chat, Message, ChatSettings
from app.models.messages import MessageCreate, MessageOut
from app.agents import ExcelAgent, SQLAgent
from app.agents.base import CancelledException
from cryptography.fernet import Fernet
import json
from datetime import datetime

logger = logging.getLogger(__name__)

validate_env()

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

    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    logger.info(f"Retrieved {len(messages)} messages for chat {chat_id}")
    if messages:
        last_msg = messages[-1]
        logger.info(
            f"Last message tokens: prompt={last_msg.prompt_tokens}, completion={last_msg.completion_tokens}, total={last_msg.total_tokens}"
        )

        # Debug: Check what MessageOut serializes
        msg_out = MessageOut.model_validate(last_msg)
        logger.info(
            f"MessageOut serialized: prompt_tokens={msg_out.prompt_tokens}, completion_tokens={msg_out.completion_tokens}, total_tokens={msg_out.total_tokens}"
        )

    return messages


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
                content = content_dict.get("text", msg.content)[:300]
            except Exception as parse_err:
                print(f"DEBUG: Failed to parse assistant message content: {parse_err}")
        content = content[:300] + ("..." if len(content) > 300 else "")
        history_str += f"{msg.role.capitalize()}: {content}\n"

    user_msg = Message(chat_id=chat_id, role="user", content=msg_data.content)

    chat.updated_at = datetime.now()

    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Create cancellation event for this request
    cancel_event = asyncio.Event()

    code_type = "python"

    if chat.file_id:
        path = "data/" + chat.file.file_path
        if os.path.exists(path) is False:
            raise HTTPException(
                status_code=404, detail="Data file not found on server."
            )
        chat_settings = (
            db.query(ChatSettings).where(ChatSettings.chat_id == chat_id).first()
        )
        agent = ExcelAgent(path, chat_settings=chat_settings, cancel_event=cancel_event)
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
            chat_settings = (
                db.query(ChatSettings).where(ChatSettings.chat_id == chat_id).first()
            )
            agent = SQLAgent(decrypted_conn_str, chat_settings=chat_settings, cancel_event=cancel_event)
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
        generation_completed = False

        try:
            # Get the async generator from the agent
            answer_generator = agent.answer(msg_data.content, history_str)
            # Iterate over the async generator
            async for chunk in answer_generator:
                try:
                    chunk_data = json.loads(chunk)
                    if chunk_data.get("type") == "final_result":
                        generation_completed = True
                        data = chunk_data.get("data", {})
                        final_response["text"] = data.get("text", "")
                        final_response["steps"] = data.get("steps", [])
                        final_response["code"] = data.get("code", None)

                except Exception as chunk_err:
                    print(f"DEBUG: Failed to parse chunk: {chunk_err}")

                yield chunk + "\n"

                # Tiny sleep to ensure the loop yields control
                await asyncio.sleep(0.01)

            if generation_completed:
                token_usage = agent.token_tracker.to_dict()
                with SessionLocal() as db_session:
                    clean_steps = sanitize_nan(final_response["steps"])
                    clean_code = sanitize_nan(final_response["code"])
                    assistant_msg = Message(
                        chat_id=chat_id,
                        role="assistant",
                        parent_id=user_msg.id,
                        content=json.dumps(
                            {
                                "text": final_response["text"],
                            }
                        ),
                        related_code={
                            "type": code_type,
                            "code": clean_code,
                        },
                        steps=clean_steps,
                        prompt_tokens=token_usage.get("prompt_tokens", 0),
                        completion_tokens=token_usage.get("completion_tokens", 0),
                        total_tokens=token_usage.get("total_tokens", 0),
                    )
                    db_session.add(assistant_msg)
                    db_session.commit()
                    db_session.refresh(assistant_msg)

                    yield json.dumps(
                        {
                            "type": "final",
                            "message_id": str(assistant_msg.id),
                            "parent_id": str(user_msg.id),
                            "token_usage": {
                                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                                "completion_tokens": token_usage.get(
                                    "completion_tokens", 0
                                ),
                                "total_tokens": token_usage.get("total_tokens", 0),
                            },
                        }
                    )

        except asyncio.CancelledError:
            print(f"DEBUG: Request cancelled by client for chat {chat_id}")
            # Signal cancellation to the agent
            cancel_event.set()
            yield json.dumps(
                {
                    "type": "error",
                    "error_type": "user_cancelled",
                    "message": "Request cancelled by user",
                }
            )
            # Re-raise to stop the generator
            raise
        except CancelledException as e:
            print(f"DEBUG: Agent operation cancelled for chat {chat_id}: {e}")
            cancel_event.set()
            yield json.dumps(
                {
                    "type": "error",
                    "error_type": "user_cancelled",
                    "message": "Request cancelled by user",
                }
            )
        except Exception as e:
            print(
                f"DEBUG: Exception in event generator for chat {chat_id}: {type(e).__name__}: {str(e)}"
            )
            import traceback

            traceback.print_exc()
            if not generation_completed:
                yield json.dumps(
                    {
                        "type": "error",
                        "error_type": "incomplete_generation",
                        "message": str(e),
                    }
                )

    return StreamingResponse(_event_generator(), media_type="application/x-ndjson")
