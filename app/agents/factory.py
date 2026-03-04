from typing import Optional, TYPE_CHECKING
from app.agents.implementations.excel import ExcelAgent
from app.agents.implementations.sql import SQLAgent
from app.agents.llm import LiteLLMAdapter
from app.agents.executors import PythonSandboxExecutor, SQLExecutor
from app.agents.cache.memory import InMemoryCache
from app.models.db_models import ChatSettings

if TYPE_CHECKING:
    from app.agents.implementations.excel import ExcelAgent
    from app.agents.implementations.sql import SQLAgent


class AgentFactory:
    """Factory for creating agents with injected dependencies."""

    _llm_instance = None

    @classmethod
    def get_llm(cls) -> LiteLLMAdapter:
        """Get or create singleton LLM instance."""
        if cls._llm_instance is None:
            cls._llm_instance = LiteLLMAdapter()
        return cls._llm_instance

    @classmethod
    def create_excel_agent(
        cls,
        file_path: str,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event=None,
        executor: Optional[PythonSandboxExecutor] = None,
        cache: Optional[InMemoryCache] = None,
        schema_inference: Optional[callable] = None,
    ) -> ExcelAgent:
        """Create an ExcelAgent with default or custom dependencies."""
        llm = cls.get_llm()
        return ExcelAgent(
            llm=llm,
            file_path=file_path,
            chat_settings=chat_settings,
            cancel_event=cancel_event,
            executor=executor,
            cache=cache,
            schema_inference=schema_inference,
        )

    @classmethod
    def create_sql_agent(
        cls,
        connection_string: str,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event=None,
        executor: Optional[SQLExecutor] = None,
        cache: Optional[InMemoryCache] = None,
        schema_inference: Optional[callable] = None,
    ) -> "SQLAgent":
        """Create a SQLAgent with default or custom dependencies."""
        llm = cls.get_llm()
        return SQLAgent(
            llm=llm,
            connection_string=connection_string,
            chat_settings=chat_settings,
            cancel_event=cancel_event,
            executor=executor,
            cache=cache,
            schema_inference=schema_inference,
        )
