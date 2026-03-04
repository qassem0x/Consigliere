import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, AsyncGenerator, TYPE_CHECKING

import json_repair
import pandas as pd
from sqlalchemy import create_engine, inspect, text

from app.agents.base import BaseAgent
from app.agents.executors.sql import SQLExecutor
from app.agents.interfaces import ILanguageModel
from app.agents.cache.manager import SQLCacheManager
from app.agents.inference import SemanticInferenceEngine
from app.agents.prompts import (
    SQL_GENERATOR_PROMPT,
    STRICT_SQL_RULES,
    SQL_FIX_PROMPT,
    EMPTY_RESULT_SQL_PROMPT,
    CHART_FIX_PROMPT,
    CHART_GENERATOR_PROMPT,
    SQL_BRAIN_PROMPT,
)
from app.models.db_models import ChatSettings

if TYPE_CHECKING:
    from app.agents.memory.chat_memory import ChatMemory

logger = logging.getLogger(__name__)


class SQLAgent(BaseAgent):
    """SQL database analysis agent with modular architecture."""

    def __init__(
        self,
        llm: Optional[ILanguageModel] = None,
        connection_string: Optional[str] = None,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event=None,
        executor: Optional[SQLExecutor] = None,
        schema_inference: Optional[callable] = None,
        chat_memory: Optional["ChatMemory"] = None,
    ):
        # Detect old vs new API: if first arg is a string, it's connection_string (old API)
        if isinstance(llm, str):
            connection_string = llm
            llm = None

        if connection_string is None:
            raise ValueError("connection_string is required")

        # Auto-create LLM if not provided
        if llm is None:
            from app.agents.llm import LiteLLMAdapter

            llm = LiteLLMAdapter()

        super().__init__(llm, chat_settings, cancel_event)

        self.connection_string = connection_string
        self._executor = executor
        self._schema_inference = schema_inference
        self._chat_memory = chat_memory
        self.target_db = connection_string.split(":")[0]
        self.max_retries = 3

        os.makedirs("static/plots", exist_ok=True)

    @property
    def executor(self) -> SQLExecutor:
        if self._executor is None:
            self._executor = SQLExecutor(
                connection_string=self.connection_string,
                max_row_limit=(
                    self.chat_settings.max_row_limit if self.chat_settings else 100
                ),
                plots_dir="static/plots",
                max_retries=self.max_retries,
            )
        return self._executor

    @property
    def chat_memory(self) -> Optional["ChatMemory"]:
        return self._chat_memory

    @property
    def cache(self) -> SQLCacheManager:
        """Use singleton SQLCacheManager for SQL caching."""
        return SQLCacheManager()

    @property
    def _sql_executor(self) -> SQLExecutor:
        """Get or create SQLExecutor with cached engine."""
        if self._executor is None:
            # Use cached engine from SQLCacheManager
            engine = self.cache.get_engine(self.connection_string)
            self._executor = SQLExecutor(
                engine=engine,  # Pass pre-created engine
                max_row_limit=(
                    self.chat_settings.max_row_limit if self.chat_settings else 100
                ),
                plots_dir="static/plots",
                max_retries=self.max_retries,
            )
        return self._executor

    def _infer_schema(self) -> str:
        """Infer database schema."""
        if self._schema_inference is not None:
            return self._schema_inference(self._sql_executor.engine)

        semantic_engine = SemanticInferenceEngine(self._sql_executor.engine)
        return semantic_engine.infer()

    @property
    def schema(self) -> str:
        """Get schema (cached or computed)."""
        # Use SQLCacheManager's get_schema method
        cached = self.cache.get_schema(self.connection_string)
        if cached:
            return cached

        schema = self._infer_schema()
        self.cache.set_schema(self.connection_string, schema)
        return schema

    @property
    def executor(self) -> SQLExecutor:
        """Get SQLExecutor (backward compatibility)."""
        return self._sql_executor

    def _generate_sql(self, user_query: str) -> str:
        """Generate SQL query from natural language."""
        system_content = (
            SQL_GENERATOR_PROMPT.format(
                schema=self.schema, query=user_query, target_db=self.target_db
            )
            + "\n"
            + STRICT_SQL_RULES
        )
        messages = [{"role": "system", "content": system_content}]
        response = self._call_llm_with_usage(messages, temperature=0.0)
        return self.executor._clean_sql(response)

    def _fix_sql(self, bad_query: str, error_msg: str) -> str:
        """Attempt to fix a failed SQL query."""
        messages = [
            {
                "role": "system",
                "content": SQL_FIX_PROMPT.format(
                    target_db=self.target_db,
                    error=error_msg,
                    query=bad_query,
                    schema=self.schema,
                ),
            }
        ]
        response = self._call_llm_with_usage(messages, temperature=0.2)
        return self.executor._clean_sql(response)

    def _widen_sql(self, original_query: str, user_request: str) -> str:
        """Broaden a SQL query that returned zero rows."""
        messages = [
            {
                "role": "system",
                "content": EMPTY_RESULT_SQL_PROMPT.format(
                    target_db=self.target_db,
                    query=original_query,
                    user_request=user_request,
                    schema=self.schema,
                ),
            }
        ]
        response = self._call_llm_with_usage(messages, temperature=0.3)
        return self.executor._clean_sql(response)

    def _fix_chart_code(self, bad_code: str, error_msg: str, df: pd.DataFrame) -> str:
        """Ask the LLM to correct broken chart code."""
        data_info = {
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "shape": df.shape,
            "sample": (
                []
                if self.chat_settings.zero_leaks_mode
                else df.head(3).to_dict(orient="records")
            ),
        }
        messages = [
            {
                "role": "system",
                "content": CHART_FIX_PROMPT.format(
                    error=error_msg,
                    code=bad_code,
                    data_info=json.dumps(data_info, indent=2, default=str),
                ),
            }
        ]
        response = self._call_llm_with_usage(messages, temperature=0.1)
        return re.sub(
            r"```(?:python|py)?\n?(.*?)\n?```", r"\1", response, flags=re.DOTALL
        ).strip()

    def _generate_chart_code(
        self, step: Dict[str, Any], df: pd.DataFrame, user_query: str
    ) -> str:
        """Generate Python code for creating a chart."""
        chart_type = step.get("chart_type", "bar")

        if self.chat_settings.zero_leaks_mode is True:
            data_sample = "REDACTED_FOR_PRIVACY"
        else:
            data_sample = df.head(5).to_dict(orient="records")

        data_info = {
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "shape": df.shape,
            "sample": data_sample,
        }

        messages = [
            {
                "role": "system",
                "content": CHART_GENERATOR_PROMPT.format(
                    step_description=step.get("title", step.get("description", "")),
                    chart_type=chart_type,
                    data_info=json.dumps(data_info, indent=2, default=str),
                    user_query=user_query,
                ),
            }
        ]

        try:
            return self._call_llm_with_usage(messages, temperature=0.0, timeout=30)
        except Exception as e:
            logger.error(f"Chart code generation failed: {e}")
            return None

    async def _consult_brain(
        self, user_query: str, history_str: str = ""
    ) -> Dict[str, Any]:
        """Consult the planning brain to generate analysis plan."""
        from app.agents.prompts.sql import SQL_BRAIN_PROMPT

        await self.check_cancelled_async()

        history_content = history_str if history_str else "No previous conversation."

        custom_prompt = ""
        if self.chat_settings and self.chat_settings.custom_prompt:
            custom_prompt = (
                f"\n\nAdditional Instructions:\n{self.chat_settings.custom_prompt}"
            )

        brain_content = (
            SQL_BRAIN_PROMPT.replace("{schema}", self.schema)
            .replace("{history}", history_content)
            .replace("{user_query}", user_query)
            .replace("{custom_prompt}", custom_prompt)
        )
        messages = [{"role": "system", "content": brain_content}]

        try:
            response = await self._call_llm_with_usage_async(
                messages, temperature=0.1, timeout=60
            )
            logger.info(f"RAW BRAIN RESPONSE:\n{response}")

            if "```" in response:
                response = response.replace("```json", "").replace("```", "").strip()

            brain_output = json_repair.loads(response)
            logger.info(f"PARSED BRAIN OUTPUT: {brain_output}")

            if isinstance(brain_output, list):
                found = None
                for item in brain_output:
                    if isinstance(item, dict) and "intent" in item:
                        found = item
                        break
                if found is None:
                    for item in brain_output:
                        if isinstance(item, dict):
                            found = item
                            break
                brain_output = found if found else {"intent": "DATA_ACTION", "plan": []}
            elif not isinstance(brain_output, dict):
                brain_output = {"intent": "DATA_ACTION", "plan": []}

            if (
                "enhanced_query" in brain_output
                and "enhanced_prompt" not in brain_output
            ):
                brain_output["enhanced_prompt"] = brain_output["enhanced_query"]

            if "intent" not in brain_output:
                brain_output["intent"] = "DATA_ACTION"
                brain_output["enhanced_prompt"] = user_query

            if brain_output.get("intent") in (
                "DATA_ACTION",
                "METADATA",
            ) and not brain_output.get("plan"):
                brain_output["plan"] = [
                    {
                        "step_number": 1,
                        "type": "table",
                        "title": "Direct Query",
                        "description": f"Execute SQL for: {user_query}",
                        "chart_type": "none",
                    }
                ]

            return brain_output

        except Exception as e:
            logger.error(f"Brain malfunction: {e}")
            return {
                "intent": "DATA_ACTION",
                "enhanced_prompt": f"Fallback: {user_query}",
                "plan": [
                    {
                        "step_number": 1,
                        "type": "table",
                        "title": "Direct Query",
                        "description": f"Execute SQL for: {user_query}",
                        "chart_type": "none",
                    }
                ],
            }

    async def _execute_sql_step(
        self, step: Dict[str, Any], all_sqls: List[str]
    ) -> Dict[str, Any]:
        """Execute a SQL-based step with error-driven self-correction."""
        current_query = step.get("title", step.get("description", ""))
        sql_query = self._generate_sql(current_query)
        df = None
        last_error = None
        current_sql_used = ""

        for attempt in range(self.max_retries):
            if not self.executor._sanitize_sql(sql_query):
                return {
                    "step_number": step["step_number"],
                    "step_description": step["title"],
                    "step_type": "error",
                    "type": "error",
                    "data": "Security Alert: Prohibited SQL commands detected.",
                }

            try:
                cached_df = self.cache.get_query_result(
                    self.connection_string, sql_query
                )
                if cached_df is not None:
                    df = cached_df
                    logger.info(
                        f"Step {step['step_number']}: Using cached query result"
                    )
                else:
                    result = await self.executor.execute(sql_query)
                    if result["type"] == "error":
                        raise Exception(result["data"])
                    df = (
                        pd.DataFrame(result["data"])
                        if result.get("data")
                        else pd.DataFrame()
                    )
                    if not df.empty:
                        self.cache.set_query_result(
                            self.connection_string, sql_query, df
                        )
                current_sql_used = sql_query
                logger.info(
                    f"Step {step['step_number']}: Query executed, {len(df)} rows"
                )
                break
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Step {step['step_number']}: SQL error: {last_error}")
                if attempt < self.max_retries - 1:
                    sql_query = self._fix_sql(sql_query, last_error)

        if df is not None and df.empty:
            wider_sql = self._widen_sql(current_sql_used, current_query)
            if self.executor._sanitize_sql(wider_sql):
                try:
                    wider_cached = self.cache.get_query_result(
                        self.connection_string, wider_sql
                    )
                    if wider_cached is not None:
                        df = wider_cached
                        logger.info(
                            f"Step {step['step_number']}: Using cached wider query result"
                        )
                    else:
                        wider_result = await self.executor.execute(wider_sql)
                        if wider_result.get("data"):
                            df = pd.DataFrame(wider_result["data"])
                            self.cache.set_query_result(
                                self.connection_string, wider_sql, df
                            )
                            current_sql_used = wider_sql
                except Exception:
                    pass

        if df is not None:
            if df.empty:
                exec_result = {
                    "step_number": step["step_number"],
                    "step_description": step["title"],
                    "step_type": step.get("type", "table"),
                    "type": "text",
                    "data": "Query returned no results.",
                    "query": current_sql_used,
                }
            else:
                df_clean = df.where(pd.notnull(df), None)
                data_dict = (
                    df_clean.head(self.chat_settings.max_row_limit)
                    .fillna("")
                    .astype(str)
                    .to_dict(orient="records")
                )
                exec_result = {
                    "step_number": step["step_number"],
                    "step_description": step["title"],
                    "step_type": step.get("type", "table"),
                    "type": "table",
                    "data": data_dict,
                    "columns": list(df.columns),
                    "total_rows": len(df),
                    "query": current_sql_used,
                }
        else:
            exec_result = {
                "step_number": step["step_number"],
                "step_description": step["title"],
                "step_type": "error",
                "type": "error",
                "data": f"Failed after {self.max_retries} attempts. Last error: {last_error}",
            }

        if current_sql_used:
            all_sqls.append(
                f"-- Step {step['step_number']}: {step.get('title', '')}\n{current_sql_used}"
            )

        return exec_result

    async def _execute_chart_step(
        self, step: Dict[str, Any], all_sqls: List[str], user_query: str
    ) -> Dict[str, Any]:
        """Execute a chart step."""
        current_query = step.get("title", step.get("description", ""))
        sql_query = self._generate_sql(current_query)
        df = None
        current_sql_used = ""

        for attempt in range(self.max_retries):
            if not self.executor._sanitize_sql(sql_query):
                return {
                    "step_number": step["step_number"],
                    "type": "error",
                    "data": "Security Alert",
                }

            try:
                cached_df = self.cache.get_query_result(
                    self.connection_string, sql_query
                )
                if cached_df is not None:
                    df = cached_df
                    logger.info(
                        f"Step {step['step_number']}: Using cached chart query result"
                    )
                else:
                    result = await self.executor.execute(sql_query)
                    if result["type"] == "error":
                        raise Exception(result["data"])
                    if result.get("data"):
                        df = pd.DataFrame(result["data"])
                        self.cache.set_query_result(
                            self.connection_string, sql_query, df
                        )
                        current_sql_used = sql_query
                break
            except Exception as e:
                if attempt < self.max_retries - 1:
                    sql_query = self._fix_sql(sql_query, str(e))

        if df is None or df.empty:
            return {
                "step_number": step["step_number"],
                "type": "error",
                "data": "No data for chart",
            }

        chart_code = self._generate_chart_code(step, df, user_query)
        if not chart_code:
            return {
                "step_number": step["step_number"],
                "type": "error",
                "data": "Chart code failed",
            }

        chart_result = await self.executor.generate_chart(chart_code, {"df": df})

        if current_sql_used:
            all_sqls.append(
                f"-- Step {step['step_number']}: {step.get('description', '')}\n{current_sql_used}\n# Chart Code:\n{chart_code}"
            )

        chart_result["step_number"] = step["step_number"]
        chart_result["step_description"] = step["title"]
        chart_result["step_type"] = "chart"
        chart_result["query"] = current_sql_used
        return chart_result

    def _execute_summary_step(
        self, step: Dict[str, Any], user_query: str, all_results: List[Dict[str, Any]]
    ) -> str:
        """Execute a summary step."""
        from app.agents.prompts.base import SUMMARY_SYNTHESIS_PROMPT

        context_str = ""
        for res in all_results:
            if res["type"] == "table":
                context_str += (
                    f"Step {res['step_number']} ({res['step_description']}):\n"
                )
                context_str += f"Query: {res.get('query','N/A')}\n"
                context_str += f"Total Rows: {res.get('total_rows', 0)}\n\n"
            elif res["type"] == "image":
                context_str += f"Step {res['step_number']}: Chart Created\n\n"

        messages = [
            {
                "role": "system",
                "content": SUMMARY_SYNTHESIS_PROMPT.format(
                    user_query=user_query,
                    context_str=context_str,
                    step_description=step.get("title", ""),
                    zero_leaks_mode=self.chat_settings.zero_leaks_mode,
                ),
            }
        ]

        try:
            return self._call_llm_with_usage(messages, temperature=0.5, timeout=30)
        except Exception:
            return "Summary generation failed."

    def _execute_metadata_step(
        self, step: Dict[str, Any], user_query: str
    ) -> Dict[str, Any]:
        """Execute a METADATA step."""
        user_query_lower = user_query.lower()

        try:
            schema_json = json.loads(self.schema)
        except:
            schema_json = {"tables": []}

        tables = schema_json.get("tables", [])
        all_results = []

        for table in tables:
            table_name = table.get("name", "")
            columns = table.get("columns", [])
            table_data = []

            if "column" in user_query_lower or "structure" in user_query_lower:
                for col in columns:
                    table_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Type": col.get("type", "unknown"),
                            "Nullable": col.get("nullable", "YES"),
                        }
                    )
            else:
                for col in columns:
                    table_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Type": col.get("type", "unknown"),
                        }
                    )

            if table_data:
                df_table = pd.DataFrame(table_data)
                all_results.append(
                    {
                        "type": "table",
                        "table_name": table_name,
                        "data": df_table.fillna("").to_dict(orient="records"),
                        "columns": list(df_table.columns),
                        "total_rows": len(df_table),
                    }
                )

        if all_results:
            return {
                "type": "metadata",
                "tables": all_results,
                "description": "Database schema",
            }
        return {"type": "text", "data": self.schema, "description": "Database schema"}

    async def answer(
        self, user_query: str, history_str: str = ""
    ) -> AsyncGenerator[str, None]:
        """Main method to answer user queries."""
        brain_output = await self._consult_brain(user_query, history_str)
        intent = brain_output.get("intent", "DATA_ACTION")
        enhanced_prompt = brain_output.get("enhanced_prompt", user_query)

        if intent == "GENERAL_CHAT":
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": "I'm Consigliere, your AI database assistant.",
                        "steps": [],
                        "code": None,
                    },
                }
            )
            return

        if intent == "OFFENSIVE":
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": "I'm here to help with data analysis.",
                        "steps": [],
                        "code": None,
                    },
                }
            )
            return

        plan = brain_output.get("plan", [])
        if not plan:
            plan = [
                {
                    "step_number": 1,
                    "type": "table",
                    "title": "Direct Query",
                    "description": enhanced_prompt,
                    "chart_type": "none",
                }
            ]

        yield json.dumps(
            {"type": "step_start", "step_number": 0, "description": "Planning..."}
        )

        all_results = []
        all_sqls = []
        final_summary_text = ""

        for step in plan:
            await self.check_cancelled_async()

            step_type = step.get("type", "table")
            step_number = step.get("step_number", 0)

            if step_type != "summary":
                yield json.dumps(
                    {
                        "type": "step_start",
                        "step_number": step_number,
                        "description": step.get(
                            "title", step.get("description", "...")
                        ),
                        "step_type": step_type,
                    }
                )

            if step_type in ["metric", "table"]:
                exec_result = await self._execute_sql_step(step, all_sqls)
                all_results.append(exec_result)
                yield json.dumps({"type": "step_result", "data": exec_result})

            elif step_type == "metadata":
                exec_result = self._execute_metadata_step(step, enhanced_prompt)
                all_results.append(exec_result)
                yield json.dumps({"type": "step_result", "data": exec_result})

            elif step_type == "chart":
                exec_result = await self._execute_chart_step(
                    step, all_sqls, enhanced_prompt
                )
                all_results.append(exec_result)
                yield json.dumps({"type": "step_result", "data": exec_result})

            elif step_type == "summary":
                final_summary_text = self._execute_summary_step(
                    step, enhanced_prompt, all_results
                )

        formatted_code = "\n\n".join(all_sqls) if all_sqls else "-- No SQL executed"

        accumulated_text = ""
        for token in self._stream_final_response(enhanced_prompt, all_results):
            accumulated_text += token
            yield json.dumps({"type": "token", "data": token, "is_final": False})

        token_usage = self.token_tracker.to_dict()
        yield json.dumps(
            {
                "type": "final_result",
                "data": {
                    "text": accumulated_text,
                    "steps": all_results,
                    "plan": plan,
                    "code": formatted_code,
                    "token_usage": token_usage,
                },
            }
        )

    async def generate_dossier(self) -> dict:
        """Generate database dossier."""
        from app.agents.prompts.base import DOSSIER_PROMPT

        messages = [
            {
                "role": "user",
                "content": DOSSIER_PROMPT.format(
                    schema=self.schema,
                    stats=self._generate_stats(),
                    preview=self._generate_preview(),
                    source_type="SQL database",
                ),
            }
        ]

        try:
            response = self._call_llm_with_usage(messages, temperature=0.4, timeout=60)
            clean_response = response.replace("```json", "").replace("```", "").strip()
            parsed = json_repair.loads(clean_response)

            if isinstance(parsed, dict):
                required_fields = [
                    "briefing",
                    "key_entities",
                    "data_alerts",
                    "recommended_actions",
                ]
                for field in required_fields:
                    if field not in parsed:
                        parsed[field] = [] if field != "briefing" else "No briefing"
                return parsed
            raise ValueError("Dossier output was not a dictionary")
        except Exception as e:
            logger.error(f"Dossier error: {e}")
            return {
                "briefing": "Database analysis completed.",
                "key_entities": [],
                "data_alerts": [],
                "recommended_actions": [],
            }

    def _generate_stats(self) -> str:
        """Generate database statistics."""
        try:
            inspector = inspect(self.executor.engine)
            tables = inspector.get_table_names()
            lines = [f"Total tables: {len(tables)}"]

            with self.executor.engine.connect() as conn:
                for table in tables[:10]:
                    try:
                        result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        row_count = result.scalar()
                    except:
                        row_count = "unknown"
                    lines.append(f"Table '{table}': {row_count} rows")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return "No stats available"

    def _generate_preview(self) -> str:
        """Generate sample rows from tables."""
        try:
            inspector = inspect(self.executor.engine)
            tables = inspector.get_table_names()[:3]
            preview_parts = []

            with self.executor.engine.connect() as conn:
                for table in tables:
                    try:
                        result = conn.execute(text(f'SELECT * FROM "{table}" LIMIT 3'))
                        rows = result.fetchall()
                        if rows:
                            preview_parts.append(
                                f"Table '{table}': {len(rows)} sample rows"
                            )
                    except:
                        pass

            return "\n\n".join(preview_parts) if preview_parts else "No preview"
        except Exception as e:
            return "No preview available"
