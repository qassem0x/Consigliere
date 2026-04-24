import logging
from typing import Optional, TYPE_CHECKING

from app.agent.implementations.base import BaseAgent
from app.agent.executors.sql import SQLExecutor
from app.agent.inference.db import SemanticInferenceEngine
from app.agent.interfaces import ISchemaProvider
from app.agent.llm.client import LLMClient
from app.agent.prompts import SQL_BRAIN_PROMPT
from app.models.db_models import ChatSettings

if TYPE_CHECKING:
    from app.agent.memory.chat_memory import ChatMemory

logger = logging.getLogger(__name__)


class _SchemaProviderAdapter(ISchemaProvider):
    def __init__(self, engine, inference_fn=None):
        self.engine = engine
        self.inference_fn = inference_fn

    def infer(self) -> str:
        if self.inference_fn:
            return self.inference_fn(self.engine)
        return SemanticInferenceEngine(self.engine).infer()


class SQLAgent(BaseAgent):
    def __init__(
        self,
        connection_string: str,
        llm_client: Optional[LLMClient] = None,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event=None,
        executor: Optional[SQLExecutor] = None,
        schema_inference: Optional[callable] = None,
        chat_memory: Optional["ChatMemory"] = None,
    ):
        if llm_client is None:
            from app.agent.llm.adapter import LiteLLMAdapter
            llm_client = LLMClient(LiteLLMAdapter(), cancel_event)

        actual_executor = executor or SQLExecutor(
            connection_string=connection_string,
            max_row_limit=chat_settings.max_row_limit if chat_settings else 100,
        )

        schema_provider = _SchemaProviderAdapter(actual_executor.engine, schema_inference)

        super().__init__(
            llm_client=llm_client,
            executor=actual_executor,
            schema_provider=schema_provider,
            brain_prompt=SQL_BRAIN_PROMPT,
            settings=chat_settings,
            chat_memory=chat_memory,
        )
        self.connection_string = connection_string
        self.target_db = connection_string.split(":")[0]