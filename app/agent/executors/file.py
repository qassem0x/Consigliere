import logging

import duckdb
import pandas as pd

from app.agent.domain import ExecutionResult
from app.agent.executors.base import BaseExecutor

logger = logging.getLogger(__name__)


class FileExecutor(BaseExecutor):
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        source_key: str = "",
        max_row_limit: int = 100,
        plots_dir: str = "static/plots",
    ):
        super().__init__(source_key=source_key, max_row_limit=max_row_limit, plots_dir=plots_dir)
        self.conn = conn

    def _execute_core(self, sql_query: str) -> ExecutionResult:
        if not self.sanitize(sql_query):
            return ExecutionResult(type="error", data="Security Alert: Prohibited SQL commands detected.")

        try:
            result = self.conn.execute(sql_query)
            columns = [desc[0] for desc in result.description] if result.description else []
            rows = result.fetchall()

            if not rows:
                return ExecutionResult(type="text", data="Query returned no results.", query=sql_query)

            df = pd.DataFrame(rows, columns=columns)
            return self._df_to_result(df, sql_query)
        except Exception as e:
            return ExecutionResult(type="error", data=f"File execution error: {str(e)}")