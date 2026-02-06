from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import UUID
from uuid import UUID


class ChatCreate(BaseModel):
    title: Optional[str] = None
    file_id: UUID

class ChatOut(BaseModel):
    id: UUID
    title: str | None
    file_id: UUID
    created_at: datetime
    type: str

    class Config:
        from_attributes = True