from fastapi.routing import APIRouter
from fastapi import Depends
from app.core.llm import MODEL_NAME
from app.core.deps import get_current_user
from app.models.db_models import User

router = APIRouter()


@router.get("/model")
def get_model(current_user: User = Depends(get_current_user)):
    return {"model": MODEL_NAME}
