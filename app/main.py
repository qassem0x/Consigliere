from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import files, auth, chats, messages
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "")

app = FastAPI()

# CORS for frontend-backend integration (restrict origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(files.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
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