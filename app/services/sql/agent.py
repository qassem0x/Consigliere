import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List

import json_repair
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, inspect, text

from app.core.prompts import (
    ANALYSIS_FORMAT_PROMPT,
    DOSSIER_PROMPT,
    SUMMARY_SYNTHESIS_PROMPT,
)
from app.core.token_tracker import TokenTracker
from app.core.utils import make_json_safe
from app.models.db_models import ChatSettings
from app.services.base_agent import BaseAgent
from app.services.sql.cache import SQLAgentCache
from app.services.sql.inference_engine import SemanticInferenceEngine
from app.services.sql.prompts import (
    CHART_FIX_PROMPT,
    CHART_GENERATOR_PROMPT,
    EMPTY_RESULT_SQL_PROMPT,
    SQL_BRAIN_PROMPT,
    SQL_FIX_PROMPT,
    SQL_GENERATOR_PROMPT,
    STRICT_SQL_RULES,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLAgent(BaseAgent):
    def __init__(self, connection_string: str, chat_settings: ChatSettings, cancel_event=None):
        super().__init__(chat_settings, cancel_event)
        self.connection_string = connection_string
        if chat_settings is not None:
            self.chat_settings = chat_settings
        else:
            self.chat_settings = ChatSettings(zero_leaks_mode=False, max_row_limit=100)

        self.cache_manager = SQLAgentCache()

        # Get engine from cache or create new one
        self.engine = self.cache_manager.get_engine(connection_string)
        self.target_db = connection_string.split(":")[0]
        self.max_retries = 3

        # Ensure plots directory exists
        os.makedirs("static/plots", exist_ok=True)

        # Try to get schema from cache
        cached_schema = self.cache_manager.get_schema(connection_string)
        if cached_schema:
            self.schema = cached_schema
            logger.info(
                f"SQLAgent initialized with cached schema: {len(self.schema)} chars"
            )
        else:
            # Generate schema and cache it
            self.semantic_engine = SemanticInferenceEngine(self.engine)
            self.schema = self.semantic_engine.infer()
            self.cache_manager.set_schema(connection_string, self.schema)
            logger.info(
                f"SQLAgent initialized with new schema: {len(self.schema)} chars"
            )

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
        return self._clean_sql(response)

    def _fix_sql(self, bad_query: str, error_msg: str) -> str:
        """Attempt to fix a failed SQL query using the runtime error."""
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
        return self._clean_sql(response)

    def _widen_sql(self, original_query: str, user_request: str) -> str:
        """Broaden a SQL query that returned zero rows by relaxing filters."""
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
        return self._clean_sql(response)

    def _fix_chart_code(self, bad_code: str, error_msg: str, df: pd.DataFrame) -> str:
        """Ask the LLM to correct broken chart code using the runtime error."""
        data_info = {
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "shape": df.shape,
            "sample": [] if self.chat_settings.zero_leaks_mode else df.head(3).to_dict(orient="records"),
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
        # Strip any markdown fences the LLM might still add
        return re.sub(r"```(?:python|py)?\n?(.*?)\n?```", r"\1", response, flags=re.DOTALL).strip()

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

    def _execute_code(self, sql_query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame with caching."""
        # Try to get from cache first
        cached_df = self.cache_manager.get_query_result(
            self.connection_string, sql_query
        )
        if cached_df is not None:
            return cached_df

        # Execute query if not cached
        with self.engine.connect() as conn:
            result = conn.execute(text(sql_query))
            if result.returns_rows:
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                # Cache the result
                self.cache_manager.set_query_result(
                    self.connection_string, sql_query, df
                )
                return df
            return pd.DataFrame()

    def _generate_chart_code(
        self, step: Dict[str, Any], df: pd.DataFrame, user_query: str
    ) -> str:
        """Generate Python code for creating a chart from the data."""
        chart_type = step.get("chart_type", "bar")

        if self.chat_settings.zero_leaks_mode is True:
            data_sample = "REDACTED_FOR_PRIVACY (Zero Leaks Mode Active). Use columns and dtypes only"
        else:
            data_sample = df.head(5).to_dict(orient="records")
        # Prepare data preview for the LLM
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
            code = self._call_llm_with_usage(messages, temperature=0.0, timeout=30)
            return code
        except Exception as e:
            logger.error(f"Chart code generation failed: {e}")
            return None

    def _sanitize_chart_code(self, code_string: str) -> str:
        """Extract and validate Python chart code."""
        match = re.search(r"```(?:python|py)?\n?(.*?)\n?```", code_string, re.DOTALL)
        clean_code = match.group(1).strip() if match else code_string.strip()

        # Security checks
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
                raise Exception(
                    f"Security violation: {description} is not allowed in generated code."
                )

        return clean_code

    def _execute_chart_code(self, clean_code: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Execute chart generation code and return image path."""
        local_scope = {"df": df, "pd": pd, "plt": plt}

        try:
            # Clear any existing plots
            plt.clf()
            plt.close("all")

            # Apply dark theme
            plt.style.use("dark_background")

            # Execute the chart code
            exec(clean_code, {"__builtins__": __builtins__}, local_scope)

            # Check if a plot was created
            if plt.gcf().get_axes():
                ax = plt.gca()
                title = ax.get_title() or "Chart"
                x_label = ax.get_xlabel() or "X-axis"
                y_label = ax.get_ylabel() or "Y-axis"
                description = (
                    f"Chart Title: {title}; X-Axis: {x_label}; Y-Axis: {y_label}"
                )

                # Save the chart
                file_name = f"plot_{uuid.uuid4()}.png"
                file_path = os.path.join("static", "plots", file_name)
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
            logger.error(f"Chart execution error: {e}")
            return {
                "type": "error",
                "data": f"Chart generation failed: {str(e)}",
            }

    async def _consult_brain(self, user_query: str, history_str: str = "") -> Dict[str, Any]:
        """Consult the planning brain to generate analysis plan."""
        # Check for cancellation before starting plan generation
        await self.check_cancelled_async()
        
        history_content = history_str if history_str else "No previous conversation."
        brain_content = (
            SQL_BRAIN_PROMPT
            .replace("{schema}", self.schema)
            .replace("{history}", history_content)
            .replace("{user_query}", user_query)
        )
        messages = [
            {
                "role": "system",
                "content": brain_content,
            }
        ]

        try:
            # This also checks for cancellation before the LLM call
            response = await self._call_llm_with_usage_async(messages, temperature=0.1, timeout=60)
            logger.info(f"RAW BRAIN RESPONSE:\n{response}")
            if "```" in response:
                response = response.replace("```json", "").replace("```", "").strip()

            brain_output = json_repair.loads(response)
            logger.info(f"PARSED BRAIN OUTPUT type={type(brain_output).__name__}: {brain_output}")

            if isinstance(brain_output, list):
                # Try to find the dict that has 'intent'; fall back to first dict item
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

            # Normalize key: prompt uses 'enhanced_query' but code reads 'enhanced_prompt'
            if "enhanced_query" in brain_output and "enhanced_prompt" not in brain_output:
                brain_output["enhanced_prompt"] = brain_output["enhanced_query"]

            if "intent" not in brain_output:
                logger.warning(
                    f"Brain output missing 'intent', defaulting to DATA_ACTION"
                )
                brain_output["intent"] = "DATA_ACTION"
                brain_output["enhanced_prompt"] = user_query

            # Validate plan structure
            if brain_output.get("intent") in ("DATA_ACTION", "METADATA") and not brain_output.get(
                "plan"
            ):
                logger.warning(f"Brain returned empty plan for intent={brain_output.get('intent')}, using fallback")
                brain_output["plan"] = [
                    {
                        "step_number": 1,
                        "type": "table",
                        "title": "Direct Query",
                        "description": f"Execute SQL for: {user_query}",
                        "chart_type": "none",
                    }
                ]

            logger.info(f"FINAL BRAIN PLAN ({len(brain_output.get('plan', []))} steps): {brain_output.get('plan')}")
            return brain_output

        except Exception as e:
            logger.error(f"Brain malfunction: {e}")
            return {
                "intent": "DATA_ACTION",
                "enhanced_prompt": f"Fallback due to JSON parsing error. User query: {user_query}",
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

    def _execute_sql_step(
        self, step: Dict[str, Any], all_sqls: List[str]
    ) -> Dict[str, Any]:
        """Execute a SQL-based step with error-driven self-correction.

        Retry strategy:
          Attempts 1..max_retries  → fix syntax/runtime errors via _fix_sql.
          If all attempts succeed but return 0 rows → one final _widen_sql pass.
        """
        current_query = step.get("title", step.get("description", ""))
        sql_query = self._generate_sql(current_query)
        df = None
        last_error = None
        current_sql_used = ""

        # ── Phase 1: Fix execution errors ───────────────────────────────────
        for attempt in range(self.max_retries):
            if not self._sanitize_sql(sql_query):
                return {
                    "step_number": step["step_number"],
                    "step_description": step["title"],
                    "step_type": "error",
                    "type": "error",
                    "data": "Security Alert: Prohibited SQL commands detected.",
                }

            try:
                df = self._execute_code(sql_query)
                current_sql_used = sql_query
                logger.info(
                    f"Step {step['step_number']}: Query executed successfully, {len(df)} rows"
                )
                break
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Step {step['step_number']}: SQL error on attempt "
                    f"{attempt + 1}/{self.max_retries}: {last_error}"
                )
                if attempt < self.max_retries - 1:
                    logger.info(f"Step {step['step_number']}: Requesting SQL fix from LLM…")
                    sql_query = self._fix_sql(sql_query, last_error)

        # ── Phase 2: If 0 rows returned, try widening the query ─────────────
        if df is not None and df.empty:
            logger.warning(
                f"Step {step['step_number']}: Query returned 0 rows. Attempting wider query…"
            )
            wider_sql = self._widen_sql(current_sql_used, current_query)
            if self._sanitize_sql(wider_sql):
                try:
                    wider_df = self._execute_code(wider_sql)
                    if wider_df is not None and not wider_df.empty:
                        df = wider_df
                        current_sql_used = wider_sql
                        logger.info(
                            f"Step {step['step_number']}: Wider query succeeded, "
                            f"{len(df)} rows returned."
                        )
                    else:
                        logger.info(
                            f"Step {step['step_number']}: Wider query also returned 0 rows."
                        )
                except Exception as e:
                    logger.warning(
                        f"Step {step['step_number']}: Wider query failed: {e}"
                    )

        # ── Build result ─────────────────────────────────────────────────────
        if df is not None:
            if df.empty:
                exec_result = {
                    "step_number": step["step_number"],
                    "step_description": step["title"],
                    "step_type": step.get("type", "table"),
                    "type": "text",
                    "data": "Query returned no results. The data may not match the specified filters.",
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
                    "description": f"Retrieved {len(df)} records",
                    "query": current_sql_used,
                }
            if step.get("detailed_description") and step.get("type") != "summary":
                exec_result["detailed_description"] = step["detailed_description"]
        else:
            exec_result = {
                "step_number": step["step_number"],
                "step_description": step["title"],
                "step_type": "error",
                "type": "error",
                "data": (
                    f"Failed to execute query after {self.max_retries} attempts. "
                    f"Last error: {last_error}"
                ),
            }
            if step.get("detailed_description") and step.get("type") != "summary":
                exec_result["detailed_description"] = step["detailed_description"]

        if current_sql_used:
            all_sqls.append(
                f"-- Step {step['step_number']}: {step.get('title', step.get('description', ''))}\n{current_sql_used}"
            )

        return exec_result

    def _execute_chart_step(
        self, step: Dict[str, Any], all_sqls: List[str], user_query: str
    ) -> Dict[str, Any]:
        """Execute a chart step with full self-correction on both SQL and chart code.

        Retry strategy:
          SQL phase:   up to max_retries attempts with _fix_sql on error.
                       If 0 rows → one _widen_sql attempt.
          Chart phase: up to max_retries attempts; on error feed error back
                       via _fix_chart_code so the LLM can self-correct.
        """
        current_query = step.get("title", step.get("description", ""))
        sql_query = self._generate_sql(current_query)
        df = None
        last_error = None
        current_sql_used = ""

        # ── Phase 1: SQL execution with error-driven retry ───────────────────
        for attempt in range(self.max_retries):
            if not self._sanitize_sql(sql_query):
                return {
                    "step_number": step["step_number"],
                    "step_description": step["title"],
                    "step_type": "error",
                    "type": "error",
                    "data": "Security Alert: Prohibited SQL commands detected.",
                }

            try:
                df = self._execute_code(sql_query)
                current_sql_used = sql_query
                logger.info(
                    f"Step {step['step_number']}: Data for chart retrieved, {len(df)} rows"
                )
                break
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Step {step['step_number']}: Chart SQL error on attempt "
                    f"{attempt + 1}/{self.max_retries}: {last_error}"
                )
                if attempt < self.max_retries - 1:
                    sql_query = self._fix_sql(sql_query, last_error)

        # ── Widen if 0 rows ───────────────────────────────────────────────────
        if df is not None and df.empty:
            logger.warning(
                f"Step {step['step_number']}: Chart SQL returned 0 rows. Attempting wider query…"
            )
            wider_sql = self._widen_sql(current_sql_used, current_query)
            if self._sanitize_sql(wider_sql):
                try:
                    wider_df = self._execute_code(wider_sql)
                    if wider_df is not None and not wider_df.empty:
                        df = wider_df
                        current_sql_used = wider_sql
                        logger.info(
                            f"Step {step['step_number']}: Wider chart SQL succeeded, "
                            f"{len(df)} rows."
                        )
                except Exception as e:
                    logger.warning(
                        f"Step {step['step_number']}: Wider chart SQL failed: {e}"
                    )

        if df is None or df.empty:
            return {
                "step_number": step["step_number"],
                "step_description": step["title"],
                "step_type": "error",
                "type": "error",
                "data": "Could not retrieve data for chart after all retries.",
            }

        # ── Phase 2: Chart code generation + self-correcting execution ───────
        chart_code = self._generate_chart_code(step, df, user_query)
        if not chart_code:
            return {
                "step_number": step["step_number"],
                "step_description": step["title"],
                "step_type": "error",
                "type": "error",
                "data": "Failed to generate chart code (LLM call failed).",
            }

        chart_result = None
        chart_last_error = None
        current_chart_code = chart_code

        for chart_attempt in range(self.max_retries):
            try:
                clean_code = self._sanitize_chart_code(current_chart_code)
            except Exception as sec_err:
                # Security violation in chart code — do not retry
                logger.error(
                    f"Step {step['step_number']}: Chart code security violation: {sec_err}"
                )
                return {
                    "step_number": step["step_number"],
                    "step_description": step["title"],
                    "step_type": "error",
                    "type": "error",
                    "data": f"Security error in chart code: {sec_err}",
                }

            result = self._execute_chart_code(clean_code, df)

            if result["type"] != "error":
                chart_result = result
                # Annotate and append SQL log entry on first success
                if current_sql_used:
                    all_sqls.append(
                        f"-- Step {step['step_number']}: "
                        f"{step.get('description', step.get('title', ''))}\n"
                        f"{current_sql_used}\n\n# Chart Code:\n{clean_code}"
                    )
                break
            else:
                chart_last_error = result["data"]
                logger.warning(
                    f"Step {step['step_number']}: Chart execution error on attempt "
                    f"{chart_attempt + 1}/{self.max_retries}: {chart_last_error}"
                )
                if chart_attempt < self.max_retries - 1:
                    logger.info(
                        f"Step {step['step_number']}: Requesting chart code fix from LLM…"
                    )
                    current_chart_code = self._fix_chart_code(
                        clean_code, chart_last_error, df
                    )

        if chart_result is None:
            logger.error(
                f"Step {step['step_number']}: Chart failed after "
                f"{self.max_retries} attempts. Last error: {chart_last_error}"
            )
            result = {
                "step_number": step["step_number"],
                "step_description": step["title"],
                "step_type": "error",
                "type": "error",
                "data": (
                    f"Chart generation failed after {self.max_retries} attempts. "
                    f"Last error: {chart_last_error}"
                ),
            }
            if step.get("detailed_description") and step.get("type") != "summary":
                result["detailed_description"] = step["detailed_description"]
            return result

        chart_result["step_number"] = step["step_number"]
        chart_result["step_description"] = step["title"]
        chart_result["step_type"] = "chart"
        chart_result["query"] = current_sql_used
        if step.get("detailed_description") and step.get("type") != "summary":
            chart_result["detailed_description"] = step["detailed_description"]

        return chart_result

    def _execute_summary_step(
        self, step: Dict[str, Any], user_query: str, all_results: List[Dict[str, Any]]
    ) -> str:
        """Execute a summary step by synthesizing previous results."""
        context_str = ""
        for res in all_results:
            if res["type"] == "table":
                context_str += (
                    f"Step {res['step_number']} ({res['step_description']}):\n"
                )
                if self.chat_settings.zero_leaks_mode is True:
                    context_str += f"Query: REDACTED (Zero Leaks Mode)\n"
                    context_str += f"Total Rows: {res.get('total_rows', 0)}\n"
                    context_str += "Data: REDACTED_FOR_PRIVACY (Zero Leaks Mode Active).\n\n"
                else:
                    context_str += f"Query: {res.get('query','N/A')}\n"
                    context_str += f"Total Rows: {res.get('total_rows', 0)}\n"
                    context_str += (
                        f"Data Sample (Top 5 rows): {str(res.get('data', [])[:5])}\n\n"
                    )
            elif res["type"] == "image":
                context_str += (
                    f"Step {res['step_number']} ({res['step_description']}):\n"
                )
                context_str += f"Chart Created: {res.get('description', '')}\n\n"
            elif res["type"] == "text":
                context_str += (
                    f"Step {res['step_number']} ({res['step_description']}):\n"
                )
                if self.chat_settings.zero_leaks_mode is True:
                    context_str += "Result: REDACTED_FOR_PRIVACY (Zero Leaks Mode Active).\n\n"
                else:
                    context_str += f"Result: {res.get('data', '')}\n\n"
            elif res["type"] == "error":
                context_str += f"Step {res['step_number']} Error: {res.get('data')}\n\n"

        messages = [
            {
                "role": "system",
                "content": SUMMARY_SYNTHESIS_PROMPT.format(
                    user_query=user_query,
                    context_str=context_str,
                    step_description=step.get("title", step.get("description", "")),
                    zero_leaks_mode=self.chat_settings.zero_leaks_mode,
                ),
            }
        ]
        for attempt in range(self.max_retries):
            try:
                summary_text = self._call_llm_with_usage(
                    messages, temperature=0.5, timeout=30
                )
                logger.info(f"Step {step['step_number']}: Summary generated successfully")
                return summary_text
            except Exception as e:
                logger.warning(
                    f"Step {step['step_number']}: Summary attempt "
                    f"{attempt + 1}/{self.max_retries} failed: {e}"
                )

        logger.error(
            f"Step {step['step_number']}: Summary failed after {self.max_retries} attempts"
        )
        return "Summary generation failed. See individual step results above for details."

    async def answer(self, user_query: str, history_str: str = ""):
        """Main method to answer user queries."""
        brain_output = await self._consult_brain(user_query, history_str)
        intent = brain_output.get("intent", "DATA_ACTION")
        enhanced_prompt = brain_output.get("enhanced_prompt", user_query)

        print("DEBUG:", brain_output)

        # Handle non-data intents
        if intent == "GENERAL_CHAT":
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": "I'm Consigliere, your AI database assistant. I can query your SQL database to find insights. What would you like to know?",
                        "steps": [],
                        "code": None,
                        "plan": None,
                    },
                }
            )
            return

        if intent == "OFFENSIVE":
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": "I'm here to help with data analysis. Please keep our conversation professional.",
                        "steps": [],
                        "code": None,
                        "plan": None,
                    },
                }
            )
            return

        # METADATA and DATA_ACTION both use plan execution
        plan = brain_output.get("plan", [])
        print("DEBUG: ", plan)

        # Validate plan
        if not plan:
            logger.warning("Empty plan received, creating fallback")
            plan = [
                {
                    "step_number": 1,
                    "type": "table",
                    "title": "Direct Query",
                    "description": enhanced_prompt,
                    "chart_type": "none",
                }
            ]

        # Yield initial planning step
        yield json.dumps(
            {
                "type": "step_start",
                "step_number": 0,
                "description": "Planning analysis steps...",
            }
        )

        all_results = []
        all_sqls = []
        final_summary_text = ""

        logger.info(f"Executing plan with {len(plan)} steps")

        # Execute each step in the plan
        for step in plan:
            # Check for cancellation before starting each step
            await self.check_cancelled_async()
            
            if isinstance(step, str):
                step = json_repair.loads(step)
            step_type = step.get("type", "table")
            step_number = step.get("step_number", 0)

            # Yield step_start for all types except summary
            if step_type != "summary":
                yield json.dumps(
                    {
                        "type": "step_start",
                        "step_number": step_number,
                        "description": step.get(
                            "title", step.get("description", "Processing...")
                        ),
                        "step_type": step_type,
                        "detailed_description": step.get("detailed_description"),
                    }
                )

            if step_type in ["metric", "table"]:
                exec_result = self._execute_sql_step(step, all_sqls)
                all_results.append(exec_result)
                yield json.dumps({"type": "step_result", "data": exec_result})

            elif step_type == "metadata":
                exec_result = self._execute_metadata_step(step, enhanced_prompt)
                all_results.append(exec_result)
                yield json.dumps({"type": "step_result", "data": exec_result})

            elif step_type == "chart":
                exec_result = self._execute_chart_step(step, all_sqls, enhanced_prompt)
                all_results.append(exec_result)
                yield json.dumps({"type": "step_result", "data": exec_result})

            elif step_type == "summary":
                final_summary_text = self._execute_summary_step(
                    step, enhanced_prompt, all_results
                )

            else:
                logger.warning(
                    f"Unknown step type '{step_type}', skipping step {step_number}"
                )
                exec_result = {
                    "step_number": step_number,
                    "step_description": step.get("title", "Unknown"),
                    "step_type": step_type,
                    "type": "error",
                    "data": f"Unknown step type: {step_type}",
                }
                if step.get("detailed_description") and step_type != "summary":
                    exec_result["detailed_description"] = step.get(
                        "detailed_description"
                    )
                all_results.append(exec_result)
                yield json.dumps({"type": "step_result", "data": exec_result})

        # Generate final summary with streaming if not already created by summary step
        formatted_code = "\n\n".join(all_sqls) if all_sqls else "-- No SQL executed"

        logger.info("Analysis complete, streaming final result")

        # Stream the final response token by token
        accumulated_text = ""
        for token in self._stream_final_response(enhanced_prompt, all_results):
            accumulated_text += token
            yield json.dumps(
                {
                    "type": "token",
                    "data": token,
                    "is_final": False,
                }
            )

        token_usage = self.token_tracker.to_dict()
        yield json.dumps(
            {
                "type": "final_result",
                "data": {
                    "text": accumulated_text,
                    "steps": all_results,
                    "plan": plan,
                    "code": formatted_code,
                    "token_usage": {
                        "prompt_tokens": token_usage.get("prompt_tokens", 0),
                        "completion_tokens": token_usage.get("completion_tokens", 0),
                        "total_tokens": token_usage.get("total_tokens", 0),
                    },
                },
            }
        )

    def _generate_stats(self) -> str:
        """Generate enriched database statistics: per-table row counts and column overview."""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            lines = [f"Total tables: {len(tables)}"]
            with self.engine.connect() as conn:
                for table in tables[:10]:  # cap at 10 tables to avoid timeout
                    try:
                        result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        row_count = result.scalar()
                    except Exception:
                        row_count = "unknown"
                    cols = inspector.get_columns(table)
                    col_names = [c["name"] for c in cols[:8]]  # first 8 columns
                    col_types = [str(c["type"]) for c in cols[:8]]
                    col_summary = ", ".join(
                        f"{n} ({t})" for n, t in zip(col_names, col_types)
                    )
                    lines.append(
                        f"Table '{table}': {row_count} rows | Columns: {col_summary}"
                    )
                    # FK relationships
                    fks = inspector.get_foreign_keys(table)
                    for fk in fks:
                        ref_table = fk.get("referred_table", "?")
                        local_cols = ", ".join(fk.get("constrained_columns", []))
                        lines.append(
                            f"  → '{table}'.{local_cols} references '{ref_table}'"
                        )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Stats generation error: {e}")
            return "No stats available"

    def _generate_preview(self) -> str:
        """Generate sample rows from up to 3 tables."""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()[:3]
            preview_parts = []
            with self.engine.connect() as conn:
                for table in tables:
                    try:
                        result = conn.execute(text(f'SELECT * FROM "{table}" LIMIT 3'))
                        rows = result.fetchall()
                        col_names = list(result.keys())
                        if rows:
                            rows_str = "\n".join(
                                str(dict(zip(col_names, row))) for row in rows
                            )
                            preview_parts.append(
                                f"Table '{table}' sample rows:\n{rows_str}"
                            )
                        else:
                            preview_parts.append(f"Table '{table}': empty")
                    except Exception as e:
                        preview_parts.append(f"Table '{table}': preview unavailable ({e})")
            return "\n\n".join(preview_parts) if preview_parts else "No preview available"
        except Exception as e:
            logger.error(f"Preview generation error: {e}")
            return "No preview available"

    def generate_dossier(self):
        """Generate database dossier (intelligence report)."""
        logger.info("Generating dossier")
        try:
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
            response = self._call_llm_with_usage(messages, temperature=0.4, timeout=60)
            clean_response = response.replace("```json", "").replace("```", "").strip()
            parsed = json_repair.loads(clean_response)
            if isinstance(parsed, dict):
                required_fields = ["briefing", "key_entities", "data_alerts", "recommended_actions"]
                for field in required_fields:
                    if field not in parsed:
                        parsed[field] = [] if field != "briefing" else "No briefing generated."
                return parsed
            raise ValueError("Dossier output was not a dictionary")
        except Exception as e:
            logger.error(f"Dossier generation error: {str(e)}")
            raise Exception(f"Dossier generation failed: {str(e)}")

    def invalidate_cache(self):
        """Invalidate all cached data for this connection."""
        self.cache_manager.invalidate_connection(self.connection_string)
        logger.info("Cache invalidated for current connection")

    def invalidate_query_cache(self):
        """Invalidate only cached queries (useful after data modifications)."""
        self.cache_manager.invalidate_all_queries(self.connection_string)
        logger.info("Query cache invalidated for current connection")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self.cache_manager.get_cache_stats()

    def _execute_metadata_step(
        self, step: Dict[str, Any], user_query: str
    ) -> Dict[str, Any]:
        """Execute a METADATA step - return targeted database schema info based on user question."""
        user_query_lower = user_query.lower()

        import json

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

            if (
                "column" in user_query_lower
                or "structure" in user_query_lower
                or "schema" in user_query_lower
            ):
                for col in columns:
                    table_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Type": col.get("type", "unknown"),
                            "Nullable": col.get("nullable", "YES"),
                        }
                    )

            elif "primary" in user_query_lower or "key" in user_query_lower:
                for col in columns:
                    if col.get("is_primary_key", False):
                        table_data.append(
                            {
                                "Column": col.get("name", ""),
                                "Type": col.get("type", "unknown"),
                            }
                        )

            elif "foreign" in user_query_lower:
                for col in columns:
                    if col.get("is_foreign_key", False):
                        table_data.append(
                            {
                                "Column": col.get("name", ""),
                                "References": col.get("foreign_key_ref", ""),
                                "Type": col.get("type", "unknown"),
                            }
                        )
            else:
                for col in columns:
                    table_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Type": col.get("type", "unknown"),
                            "Nullable": col.get("nullable", "YES"),
                        }
                    )

            if table_data:
                df_table = pd.DataFrame(table_data)
                all_results.append(
                    {
                        "type": "table",
                        "table_name": table_name,
                        "data": make_json_safe(df_table.fillna("").to_dict(orient="records")),
                        "columns": list(df_table.columns),
                        "total_rows": len(df_table),
                        "description": f"Schema for {table_name}",
                    }
                )

        if all_results:
            return {
                "type": "metadata",
                "tables": all_results,
                "description": "Database schema information",
            }
        else:
            return {
                "type": "text",
                "data": self.schema,
                "description": "Database schema information",
            }
