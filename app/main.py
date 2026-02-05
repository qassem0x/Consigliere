from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import upload, auth, chats, messages
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "")

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(upload.router)
app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(messages.router)
    
@app.get("/")
def check_health():
    return {"status": "alive", "system": "Consigliere"}

@app.get("/db-health")
def test_db_connection():
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            
        return {"status": "connected", "database_version": version}
        
    except Exception as e:
        return {"status": "error", "details": str(e)}