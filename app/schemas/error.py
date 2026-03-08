from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel


class ErrorCodeEnum(str, Enum):
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    AGENT_ERROR = "AGENT_ERROR"
    LLM_ERROR = "LLM_ERROR"
    CANCELLED = "CANCELLED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"


class ErrorResponse(BaseModel):
    code: ErrorCodeEnum
    message: str
    details: Optional[Any] = None
    retry_after: Optional[int] = None
    step_failed: Optional[int] = None
