from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional, Tuple

from app.agent.domain import ExecutionResult, LLMResponse, TokenUsage


class ILanguageModel(ABC):
    @abstractmethod
    def complete(self, messages: list[dict], temperature: float, timeout: int) -> LLMResponse:
        pass

    @abstractmethod
    async def complete_async(self, messages: list[dict], temperature: float, timeout: int) -> LLMResponse:
        pass

    @abstractmethod
    def stream(self, messages: list[dict], temperature: float, timeout: int) -> Generator[Tuple[str, TokenUsage], None, None]:
        pass


class IQueryExecutor(ABC):
    @abstractmethod
    def execute(self, sql: str) -> ExecutionResult:
        pass

    @abstractmethod
    def get_schema(self) -> Optional[str]:
        pass

    @abstractmethod
    def set_schema(self, schema: str):
        pass


class ISchemaProvider(ABC):
    @abstractmethod
    def infer(self) -> str:
        pass


class ICache(ABC):
    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass


class IDataLoader(ABC):
    @abstractmethod
    def load(self, source: str) -> Any:
        pass


class ISchemaInference(ABC):
    @abstractmethod
    def infer(self, data: Any) -> dict:
        pass


class IExecutor(ABC):
    @abstractmethod
    async def execute(self, code: str, context: dict) -> dict:
        pass