from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import Session
from app.core.deps import get_current_user
from app.models.db_models import Chat, Dossier, User
from app.models.connections import ConnectionCreate, ConnectionOut
from app.models.db_models import Connection
from app.core.database import get_db
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

from app.services.sql_agent import SQLAgent

load_dotenv()

router = APIRouter()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY not found in environment variables")
fernet = Fernet(
    ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
)


@router.post("/connections", response_model=ConnectionOut, status_code=201)
def create_connection(
    connection: ConnectionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    print("DEBUG: Received connection details:", connection)
    url = URL.create(
        drivername=connection.drivername,
        username=connection.username,
        password=connection.password,
        host=connection.host,
        port=connection.port,
        database=connection.database,
    )

    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as conn_err:
        print(
            f"DEBUG: Failed to connect to database: {type(conn_err).__name__}: {str(conn_err)}"
        )
        raise HTTPException(status_code=400, detail="Invalid connection details")
    finally:
        if "engine" in locals():
            engine.dispose()

    ## DO ANALYSIS AND CREATE DOSSIER
    try:
        agent = SQLAgent(url.render_as_string(hide_password=False))
        print(
            f"DEBUG: Successfully initialized SQLAgent for connection: {connection.name}"
        )
    except Exception as agent_init_err:
        print(
            f"DEBUG: Failed to initialize SQLAgent: {type(agent_init_err).__name__}: {str(agent_init_err)}"
        )
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to database: {str(agent_init_err)}",
        )

    dossier = {}
    try:
        dossier = agent.generate_dossier()
        print(
            f"DEBUG: Successfully generated dossier for connection: {connection.name}"
        )
    except Exception as dossier_err:
        print(
            f"DEBUG: Failed to generate dossier: {type(dossier_err).__name__}: {str(dossier_err)}"
        )
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=400, detail="Failed to retrieve tables from the database"
        )

    encrypted_url = fernet.encrypt(
        url.render_as_string(hide_password=False).encode()
    ).decode()

    new_connection = Connection(
        user_id=user.id,
        name=connection.name,
        engine=connection.drivername,
        connection_string=encrypted_url,
    )

    try:
        with db.begin_nested():  # start a transaction
            db.add(new_connection)
            db.flush()

            new_dossier = Dossier(
                connection_id=new_connection.id,
                briefing=dossier.get("briefing", "No briefing generated."),
                key_entities=dossier.get("key_entities", []),
                recommended_actions=dossier.get("recommended_actions", []),
            )
            db.add(new_dossier)
            db.flush()

            new_chat = Chat(
                user_id=user.id,
                connection_id=new_connection.id,
                dossier_id=new_dossier.id,
                title=f"Analysis: {connection.name}",
            )
            db.add(new_chat)
        db.commit()
        db.refresh(new_connection)
        return {
            "connection_id": new_connection.id,
            "name": new_connection.name,
            "host": connection.host,
            "database": connection.database,
            "status": "connected",
        }

    except Exception as save_err:
        print(
            f"DEBUG: Failed to save connection data: {type(save_err).__name__}: {str(save_err)}"
        )
        import traceback

        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save connection data")
