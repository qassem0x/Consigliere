import logging
from typing import Optional

import pandas as pd
from sqlalchemy import text

from app.agent.cache.sql import SQLCacheManager
from app.agent.domain import ExecutionResult
from app.agent.executors.base import BaseExecutor

logger = logging.getLogger(__name__)


class SQLExecutor(BaseExecutor):
    def __init__(
        self,
        connection_string: str = None,
        max_row_limit: int = 100,
        plots_dir: str = "static/plots",
        engine=None,
    ):
        if connection_string is None and engine is None:
            raise ValueError("Either connection_string or engine must be provided")

        source_key = connection_string or str(engine.url)
        super().__init__(source_key=source_key, max_row_limit=max_row_limit, plots_dir=plots_dir)
        self.connection_string = connection_string
        self._engine = engine
        self.target_db = connection_string.split(":")[0] if connection_string else "unknown"
        self._cache_manager = SQLCacheManager()

    @property
    def engine(self):
        if self._engine is None:
            self._engine = self._cache_manager.get_engine(self.connection_string)
        return self._engine

    def _execute_core(self, sql_query: str) -> ExecutionResult:
        if not self.sanitize(sql_query):
            return ExecutionResult(type="error", data="Security Alert: Prohibited SQL commands detected.")

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SET TRANSACTION READ ONLY"))
                result = conn.execute(text(sql_query))
                if not result.returns_rows:
                    return ExecutionResult(type="text", data="Query returned no results.", query=sql_query)

                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                if df.empty:
                    return ExecutionResult(type="text", data="Query returned no results.", query=sql_query)

                return self._df_to_result(df, sql_query)
        except Exception as e:
            return ExecutionResult(type="error", data=f"SQL execution error: {str(e)}")

    def get_schema(self) -> Optional[str]:
        if self.connection_string:
            cached = self._cache_manager.get_schema(self.connection_string)
            if cached:
                return cached
        return super().get_schema()

    def set_schema(self, schema: str):
        if self.connection_string:
            self._cache_manager.set_schema(self.connection_string, schema)
        super().set_schema(schema)