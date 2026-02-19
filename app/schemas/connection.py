from typing import Optional, Any
from pydantic import BaseModel


class ConnectionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    db_type: str
    connection_string: Optional[str] = None
    created_at: Any
    updated_at: Any


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    database_version: Optional[str] = None
