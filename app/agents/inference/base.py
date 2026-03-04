from abc import ABC, abstractmethod
from typing import Any


class ISchemaInference(ABC):
    """Base interface for schema inference."""

    @abstractmethod
    def infer(self) -> str:
        """Infer schema from data source and return JSON string."""
        pass
