from fastapi.routing import APIRouter
from app.core.llm import MODEL_NAME

router = APIRouter()


@router.get("/model")
def get_model():
    return {"model": MODEL_NAME}
