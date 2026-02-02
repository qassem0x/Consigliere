from fastapi import FastAPI
from app.api import upload

app = FastAPI()

app.include_router(upload.router)


@app.get("/")
def check_health():
    return {"status": "alive", "system": "Consigliere"}
