import json
import os
import re
import uuid
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


class SQLExecutor:
    """Executor for SQL queries against databases."""

    def __init__(
        self,
        connection_string: str = None,
        max_row_limit: int = 100,
        plots_dir: str = "static/plots",
        max_retries: int = 3,
        engine: Engine = None,
    ):
        if connection_string is None and engine is None:
            raise ValueError("Either connection_string or engine must be provided")

        self.connection_string = connection_string
        self.max_row_limit = max_row_limit
        self.plots_dir = plots_dir
        self.max_retries = max_retries
        self.target_db = (
            connection_string.split(":")[0] if connection_string else "unknown"
        )

        os.makedirs(plots_dir, exist_ok=True)

        self._engine = engine

    @property
    def engine(self):
        if self._engine is None and self.connection_string:
            self._engine = create_engine(self.connection_string)
        return self._engine

    def _sanitize_sql(self, sql_query: str) -> bool:
        """Check if SQL query is safe (read-only)."""
        lowered = sql_query.lower()
        if "error:" in lowered:
            return False
        banned = [
            r"\binsert\b",
            r"\bupdate\b",
            r"\bdelete\b",
            r"\bdrop\b",
            r"\balter\b",
            r"\bgrant\b",
            r"\btruncate\b",
            r"\bcreate\b",
        ]
        for pattern in banned:
            if re.search(pattern, lowered):
                return False
        return True

    def _clean_sql(self, response: str) -> str:
        """Clean SQL response from LLM output."""
        cleaned = response.replace("```sql", "").replace("```", "").strip()
        if not cleaned.lower().startswith("select") and not cleaned.lower().startswith(
            "with"
        ):
            match = re.search(r"(SELECT|WITH)\s", cleaned, re.IGNORECASE)
            if match:
                cleaned = cleaned[match.start() :]
        return cleaned

    async def execute(self, sql_query: str, context: dict = None) -> Dict[str, Any]:
        """Execute SQL query and return results as DataFrame."""
        context = context or {}

        if not self._sanitize_sql(sql_query):
            return {
                "type": "error",
                "data": "Security Alert: Prohibited SQL commands detected.",
            }

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                if result.returns_rows:
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())

                    if df.empty:
                        return {
                            "type": "text",
                            "data": "Query returned no results.",
                            "query": sql_query,
                        }

                    df_clean = df.where(pd.notnull(df), None)
                    data_dict = (
                        df_clean.head(self.max_row_limit)
                        .fillna("")
                        .astype(str)
                        .to_dict(orient="records")
                    )
                    return {
                        "type": "table",
                        "data": data_dict,
                        "columns": list(df.columns),
                        "total_rows": len(df),
                        "query": sql_query,
                    }
                return pd.DataFrame()
        except Exception as e:
            return {
                "type": "error",
                "data": f"SQL execution error: {str(e)}",
            }

    async def execute_with_fix(
        self, sql_query: str, llm_fix_func, context: dict = None
    ) -> Dict[str, Any]:
        """Execute SQL with retry logic on error."""
        context = context or {}
        current_query = sql_query
        last_error = None

        for attempt in range(self.max_retries):
            if not self._sanitize_sql(current_query):
                return {
                    "type": "error",
                    "data": "Security Alert: Prohibited SQL commands detected.",
                }

            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(current_query))
                    if result.returns_rows:
                        df = pd.DataFrame(result.fetchall(), columns=result.keys())

                        if df.empty:
                            return {
                                "type": "text",
                                "data": "Query returned no results.",
                                "query": current_query,
                            }

                        df_clean = df.where(pd.notnull(df), None)
                        data_dict = (
                            df_clean.head(self.max_row_limit)
                            .fillna("")
                            .astype(str)
                            .to_dict(orient="records")
                        )
                        return {
                            "type": "table",
                            "data": data_dict,
                            "columns": list(df.columns),
                            "total_rows": len(df),
                            "query": current_query,
                        }
                    return pd.DataFrame()
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    current_query = await llm_fix_func(current_query, last_error)

        return {
            "type": "error",
            "data": f"SQL failed after {self.max_retries} attempts. Last error: {last_error}",
        }

    def _sanitize_chart_code(self, code_string: str) -> str:
        """Extract and validate Python chart code."""
        match = re.search(r"```(?:python|py)?\n?(.*?)\n?```", code_string, re.DOTALL)
        clean_code = match.group(1).strip() if match else code_string.strip()

        banned_patterns = [
            (r"\bos\.", "os module access"),
            (r"\bsys\.", "sys module access"),
            (r"\bsubprocess\.", "subprocess module"),
            (r"\bopen\s*\(", "file operations"),
            (r"\b__import__\s*\(", "dynamic imports"),
            (r"\bexec\s*\(", "exec function"),
            (r"\beval\s*\(", "eval function"),
        ]

        for pattern, description in banned_patterns:
            if re.search(pattern, clean_code, re.IGNORECASE):
                raise Exception(f"Security violation: {description} is not allowed.")

        return clean_code

    async def generate_chart(self, code: str, context: dict) -> Dict[str, Any]:
        """Generate chart from Python code."""
        df = context.get("df")
        if df is None:
            return {"type": "error", "data": "No DataFrame provided for chart"}

        try:
            clean_code = self._sanitize_chart_code(code)
        except Exception as e:
            return {"type": "error", "data": f"Security error: {e}"}

        local_scope = {"df": df, "pd": pd, "plt": plt}

        try:
            plt.clf()
            plt.close("all")
            plt.style.use("dark_background")

            exec(clean_code, {"__builtins__": __builtins__}, local_scope)

            if plt.gcf().get_axes():
                ax = plt.gca()
                title = ax.get_title() or "Chart"
                x_label = ax.get_xlabel() or "X-axis"
                y_label = ax.get_ylabel() or "Y-axis"
                description = (
                    f"Chart Title: {title}; X-Axis: {x_label}; Y-Axis: {y_label}"
                )

                file_name = f"plot_{uuid.uuid4()}.png"
                file_path = os.path.join(self.plots_dir, file_name)
                plt.savefig(file_path, bbox_inches="tight", dpi=100)
                plt.close("all")

                return {
                    "type": "image",
                    "data": f"/static/plots/{file_name}",
                    "mime": "image/png",
                    "description": description,
                }
            else:
                return {
                    "type": "error",
                    "data": "Chart code executed but no plot was created.",
                }

        except Exception as e:
            plt.close("all")
            return {"type": "error", "data": f"Chart generation failed: {str(e)}"}
