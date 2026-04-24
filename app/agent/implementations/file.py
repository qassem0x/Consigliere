import logging
import os
from typing import Optional, TYPE_CHECKING

import duckdb

from app.agent.implementations.base import BaseAgent
from app.agent.executors.file import FileExecutor
from app.agent.inference.file import FileInferenceEngine
from app.agent.interfaces import ISchemaProvider
from app.agent.llm.client import LLMClient
from app.agent.prompts import FILE_BRAIN_PROMPT
from app.models.db_models import ChatSettings

if TYPE_CHECKING:
    from app.agent.memory.chat_memory import ChatMemory

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {
    ".xlsx": "read_excel",
    ".xls": "read_excel",
    ".csv": "read_csv_auto",
    ".parquet": "read_parquet",
    ".json": "read_json_auto",
}


class _SchemaProviderAdapter(ISchemaProvider):
    def __init__(self, conn, inference_fn=None):
        self.conn = conn
        self.inference_fn = inference_fn

    def infer(self) -> str:
        if self.inference_fn:
            return self.inference_fn(self.conn)
        return FileInferenceEngine(self.conn).infer()


class ExcelAgent(BaseAgent):
    def __init__(
        self,
        source: str,
        llm_client: Optional[LLMClient] = None,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event=None,
        schema_inference: Optional[callable] = None,
        chat_memory: Optional["ChatMemory"] = None,
    ):
        if llm_client is None:
            from app.agent.llm.adapter import LiteLLMAdapter
            llm_client = LLMClient(LiteLLMAdapter(), cancel_event)

        if not os.path.exists(source):
            raise ValueError(f"File not found: {source}")

        ext = next((e for e in _SUPPORTED_EXTENSIONS if source.endswith(e)), None)
        if ext is None:
            raise ValueError(f"Unsupported file format: {source}")

        conn = duckdb.connect(database=":memory:")
        reader = _SUPPORTED_EXTENSIONS[ext]
        conn.execute(f"CREATE TABLE data AS SELECT * FROM {reader}('{source}')")
        row_count = conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]
        logger.info(f"Loaded {row_count} rows from {source}")

        executor = FileExecutor(
            conn=conn,
            source_key=source,
            max_row_limit=chat_settings.max_row_limit if chat_settings else 100,
        )

        schema_provider = _SchemaProviderAdapter(conn, schema_inference)

        super().__init__(
            llm_client=llm_client,
            executor=executor,
            schema_provider=schema_provider,
            brain_prompt=FILE_BRAIN_PROMPT,
            settings=chat_settings,
            chat_memory=chat_memory,
        )
        self.source = source