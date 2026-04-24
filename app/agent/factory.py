from typing import Optional, TYPE_CHECKING

from app.agent.llm.adapter import LiteLLMAdapter
from app.agent.llm.client import LLMClient
from app.models.db_models import ChatSettings

if TYPE_CHECKING:
    from app.agent.implementations.file import ExcelAgent
    from app.agent.implementations.db import SQLAgent


class AgentFactory:
    _llm: Optional[LiteLLMAdapter] = None

    @classmethod
    def _get_llm(cls) -> LiteLLMAdapter:
        if cls._llm is None:
            cls._llm = LiteLLMAdapter()
        return cls._llm

    @classmethod
    def _client(cls, cancel_event=None) -> LLMClient:
        return LLMClient(cls._get_llm(), cancel_event)

    @classmethod
    def create_excel_agent(
        cls,
        source: str,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event=None,
        schema_inference: Optional[callable] = None,
        chat_memory=None,
    ) -> "ExcelAgent":
        from app.agent.implementations.file import ExcelAgent
        return ExcelAgent(
            source=source,
            llm_client=cls._client(cancel_event),
            chat_settings=chat_settings,
            schema_inference=schema_inference,
            chat_memory=chat_memory,
        )

    @classmethod
    def create_sql_agent(
        cls,
        connection_string: str,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event=None,
        executor=None,
        cache=None,
        schema_inference: Optional[callable] = None,
    ) -> "SQLAgent":
        from app.agent.implementations.db import SQLAgent
        return SQLAgent(
            connection_string=connection_string,
            llm_client=cls._client(cancel_event),
            chat_settings=chat_settings,
            executor=executor,
            schema_inference=schema_inference,
        )