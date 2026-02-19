from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class FileMetadata(BaseModel):
    file_id: str
    filename: str
    rows: int
    columns: List[str]


class DossierData(BaseModel):
    briefing: str
    key_entities: List[str]
    recommended_actions: List[str]


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    rows: int
    columns: List[str]
    dossier: Optional[DossierData] = None


class FileResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    file_path: str
    file_type: str
    created_at: Any
