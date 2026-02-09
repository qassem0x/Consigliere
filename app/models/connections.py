from pydantic import BaseModel, ConfigDict
from uuid import UUID


class ConnectionCreate(BaseModel):
    name: str
    drivername: str = "postgresql"
    host: str
    port: int = 5432
    database: str
    username: str
    password: str


class ConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connection_id: UUID
    name: str
    host: str
    database: str
    status: str = "connected"
