from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import UUID
from uuid import UUID


class MessageCreate(BaseModel):
    content: str

class MessageOut(BaseModel):
    id: UUID
    role: str  # 'user' or 'ai'
    content: str
    created_at: datetime

    class Config:
        from_attributes = True