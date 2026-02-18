from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class ChatCreate(BaseModel):
    title: Optional[str] = None
    file_id: UUID
    zero_leaks_mode: Optional[bool] = False
    max_row_limit: Optional[int] = 100


class ChatSettingsUpdate(BaseModel):
    zero_leaks_mode: Optional[bool] = False
    max_row_limit: Optional[int] = 100


class FileInfo(BaseModel):
    file_path: str
    filename: str


class ChatSettingsOut(BaseModel):
    zero_leaks_mode: bool = False
    max_row_limit: int = 100


class ChatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: Optional[str] = None
    file_id: Optional[UUID] = None
    connection_id: Optional[UUID] = None
    created_at: datetime
    type: Optional[str] = None
    file: Optional[FileInfo] = None
    settings: Optional[ChatSettingsOut] = None
