from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class ChatCreate(BaseModel):
    title: Optional[str] = None
    file_id: UUID


class FileInfo(BaseModel):
    file_path: str
    filename: str


class ChatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: Optional[str] = None
    file_id: Optional[UUID] = None
    connection_id: Optional[UUID] = None
    created_at: datetime
    type: Optional[str] = None
    file: Optional[FileInfo] = None
