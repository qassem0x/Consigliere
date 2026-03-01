from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Dict, Any, List


class MessageCreate(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    parent_id: Optional[UUID] = None
    created_at: datetime
    related_code: Optional[Dict[str, Any]] = None
    steps: Optional[List[Dict[str, Any]]] = None
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    total_tokens: Optional[int] = 0

    class Config:
        from_attributes = True
