from fastapi.routing import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.models.db_models import User
from app.models.chats import ChatCreate, ChatOut, ChatSettingsUpdate, ChatSettingsOut
from app.models.db_models import Chat, File, ChatSettings
from app.core.database import get_db

router = APIRouter()


@router.post("/chats", response_model=ChatOut, status_code=201)
def create_chat(
    chat: ChatCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file = (
        db.query(File).filter(File.id == chat.file_id, File.user_id == user.id).first()
    )
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    try:

        new_chat = Chat(file_id=chat.file_id, user_id=user.id)
        db.add(new_chat)
        db.flush()

        new_settings = ChatSettings(
            chat_id=new_chat.id,
            zero_leaks_mode=chat.zero_leaks_mode,
            max_row_limit=chat.max_row_limit,
        )
        db.add(new_settings)

        db.commit()
        db.refresh(new_chat)
        return new_chat
    except Exception:
        raise HTTPException(500)


@router.get("/chats", response_model=list[ChatOut])
def get_my_chats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):

    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(Chat.updated_at.desc())
        .all()
    )

    result = []
    for chat in chats:
        settings = None
        if chat.settings:
            settings = ChatSettingsOut(
                zero_leaks_mode=chat.settings.zero_leaks_mode,
                max_row_limit=chat.settings.max_row_limit,
            )
        chat_data = {
            "id": chat.id,
            "title": chat.title
            or (chat.file.filename if chat.file else "Untitled Chat"),
            "file_id": chat.file_id,
            "connection_id": chat.connection_id,
            "created_at": chat.created_at,
            "type": "excel" if chat.file else "connection",
            "file": (
                {"file_path": chat.file.file_path, "filename": chat.file.filename}
                if chat.file
                else None
            ),
            "settings": settings,
        }
        result.append(chat_data)

    return result


@router.get("/chats/{chat_id}/dossier")
def get_chat_dossier(
    chat_id: str,
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

    dossier = chat.dossier
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found for this chat")

    return {
        "created_at": dossier.created_at,
        "briefing": dossier.briefing,
        "key_entities": dossier.key_entities,
        "recommended_actions": dossier.recommended_actions,
    }


@router.delete("/chats/{chat_id}", status_code=204)
def delete_chat(
    chat_id: str,
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

    target_connection = chat.connection
    target_file = chat.file

    db.delete(chat)
    db.commit()

    if target_file:
        file_path = "data/" + chat.file.file_path
        if file_path:
            from app.agents.cache import InMemoryCache

            cache = InMemoryCache()
            cache.invalidate(file_path)

            import os

            if os.path.exists(file_path):
                os.remove(file_path)

    if target_connection:
        encrypted_conn_str = target_connection.connection_string
        if encrypted_conn_str:
            try:
                from cryptography.fernet import Fernet
                from app.core.config import ENCRYPTION_KEY

                fernet = Fernet(ENCRYPTION_KEY.encode())

                if isinstance(encrypted_conn_str, str):
                    encrypted_conn_str = encrypted_conn_str.encode()

                decrypted_conn_str = fernet.decrypt(encrypted_conn_str).decode()

                from app.agents.cache import SQLCacheManager

                cache = SQLCacheManager()
                cache.invalidate_connection(connection_string=decrypted_conn_str)

            except Exception as e:
                print(f"Warning: Failed to invalidate cache for deleted chat: {e}")


@router.patch("/chats/{chat_id}/settings", status_code=200)
def update_chat_settings(
    chat_id: str,
    settings: ChatSettingsUpdate,
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

    if not chat.settings:
        new_settings = ChatSettings(
            chat_id=chat.id,
            zero_leaks_mode=settings.zero_leaks_mode,
            max_row_limit=settings.max_row_limit,
            custom_prompt=settings.custom_prompt,
        )
        db.add(new_settings)
    else:
        chat.settings.zero_leaks_mode = settings.zero_leaks_mode
        chat.settings.max_row_limit = settings.max_row_limit
        chat.settings.custom_prompt = settings.custom_prompt
        db.add(chat.settings)

    db.commit()
    db.refresh(chat)

    return {
        "zero_leaks_mode": chat.settings.zero_leaks_mode,
        "max_row_limit": chat.settings.max_row_limit,
        "custom_prompt": chat.settings.custom_prompt,
    }
