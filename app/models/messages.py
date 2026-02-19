from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Dict, Any


class MessageCreate(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
    related_code: Optional[Dict[str, Any]] = None
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    total_tokens: Optional[int] = 0

    class Config:
        from_attributes = True
