from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional, Tuple
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class StepResult:
    type: str
    data: Any
    step_number: int
    description: Optional[str] = None
    columns: Optional[list] = None
    total_rows: Optional[int] = None


class ILanguageModel(ABC):
    """Interface for LLM operations."""

    @abstractmethod
    def complete(
        self, messages: list[dict], temperature: float, timeout: int
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def complete_async(
        self, messages: list[dict], temperature: float, timeout: int
    ) -> LLMResponse:
        pass

    @abstractmethod
    def stream(
        self, messages: list[dict], temperature: float, timeout: int
    ) -> Generator[Tuple[str, Dict[str, int]], None, None]:
        """Stream response. Yields (token, usage_dict) tuples.
        
        Usage dict contains prompt_tokens, completion_tokens, total_tokens.
        Empty dict for regular tokens, populated on final usage token.
        """
        pass


class IDataLoader(ABC):
    """Interface for loading data."""

    @abstractmethod
    def load(self, source: str) -> Any:
        pass


class ISchemaInference(ABC):
    """Interface for schema inference."""

    @abstractmethod
    def infer(self, data: Any) -> dict:
        pass


class IExecutor(ABC):
    """Interface for code/SQL execution."""

    @abstractmethod
    async def execute(self, code: str, context: dict) -> dict:
        pass


class ICache(ABC):
    """Interface for caching."""

    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass
