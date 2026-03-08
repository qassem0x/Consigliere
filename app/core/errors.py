from enum import Enum
from typing import Optional, Any, Dict
from dataclasses import dataclass, field


class ErrorCode(Enum):
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


class RecoverableError(Exception):
    """Base exception for recoverable errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        user_message: str = None,
        technical_details: Any = None,
        recoverable: bool = True,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.code = code
        self.user_message = user_message or message
        self.technical_details = technical_details
        self.recoverable = recoverable
        self.retry_after = retry_after


class RateLimitError(RecoverableError):
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 30):
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT,
            user_message="Too many requests. Please wait a moment.",
            recoverable=True,
            retry_after=retry_after,
        )


class LLMTimeoutError(RecoverableError):
    def __init__(
        self, message: str = "LLM request timed out", user_message: str = "Request took too long. Try a simpler query."
    ):
        super().__init__(
            message=message,
            code=ErrorCode.TIMEOUT,
            user_message=user_message,
            recoverable=True,
        )


class LLMError(RecoverableError):
    def __init__(self, message: str, technical_details: Any = None):
        super().__init__(
            message=message,
            code=ErrorCode.LLM_ERROR,
            user_message="AI service temporarily unavailable. Please try again.",
            technical_details=technical_details,
            recoverable=True,
        )


class AgentExecutionError(RecoverableError):
    def __init__(
        self,
        message: str,
        user_message: str = None,
        technical_details: Any = None,
        step_failed: Optional[int] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AGENT_ERROR,
            user_message=user_message
            or "Couldn't complete the analysis. Try simplifying your query.",
            technical_details=technical_details,
            recoverable=False,
        )
        self.step_failed = step_failed


class ValidationError(RecoverableError):
    def __init__(self, message: str, field: str = None):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            user_message=message,
            recoverable=False,
        )
        self.field = field


@dataclass
class ErrorResponse:
    code: str
    message: str
    details: Optional[Any] = None
    retry_after: Optional[int] = None
    step_failed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        if self.retry_after:
            result["retry_after"] = self.retry_after
        if self.step_failed:
            result["step_failed"] = self.step_failed
        return result

    @classmethod
    def from_exception(cls, exc: Exception) -> "ErrorResponse":
        if isinstance(exc, RecoverableError):
            return cls(
                code=exc.code.value,
                message=exc.user_message,
                details=exc.technical_details,
                retry_after=exc.retry_after,
                step_failed=getattr(exc, "step_failed", None),
            )
        return cls(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="An unexpected error occurred. Please try again.",
        )
