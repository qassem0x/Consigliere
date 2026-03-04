import json
import logging
import os
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable

import json_repair
import pandas as pd

from app.agents.base import BaseAgent
from app.agents.executors.python import PythonSandboxExecutor
from app.agents.interfaces import ILanguageModel
from app.agents.cache import InMemoryCache
from app.agents.inference import ExcelInferenceEngine
from app.agents.prompts import EXCEL_BRAIN_PROMPT, STEP_EXECUTOR_PROMPT, CODE_FIX_PROMPT
from app.models.db_models import ChatSettings

logger = logging.getLogger(__name__)


class ExcelAgent(BaseAgent):
    """Excel data analysis agent with modular architecture."""

    def __init__(
        self,
        llm: Optional[ILanguageModel] = None,
        file_path: Optional[str] = None,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event=None,
        executor: Optional[PythonSandboxExecutor] = None,
        schema_inference: Optional[Callable[..., str]] = None,
    ):
        # Detect old vs new API: if first arg is a string, it's file_path (old API)
        # If it's an ILanguageModel, it's llm (new API)
        if isinstance(llm, str):
            # Old API: first arg is file_path
            file_path = llm
            llm = None

        if file_path is None:
            raise ValueError("file_path is required")

        # Auto-create LLM if not provided (for backward compatibility)
        if llm is None:
            from app.agents.llm import LiteLLMAdapter

            llm = LiteLLMAdapter()

        super().__init__(llm, chat_settings, cancel_event)

        self.file_path = file_path
        self._executor = executor
        self._schema_inference = schema_inference

        self.df = self._load_data(file_path)
        if self.df is None:
            raise ValueError(f"Failed to load data from {file_path}")

        self.schema = self._infer_schema()

    @property
    def cache(self) -> InMemoryCache:
        # Use singleton InMemoryCache - shared across all agents
        return InMemoryCache()

    @property
    def executor(self) -> PythonSandboxExecutor:
        if self._executor is None:
            self._executor = PythonSandboxExecutor(
                max_row_limit=(
                    self.chat_settings.max_row_limit if self.chat_settings else 100
                ),
                plots_dir="static/plots",
            )
        return self._executor

    def _infer_schema(self) -> str:
        """Infer schema from dataframe."""
        schema_cache_key = f"{self.file_path}:schema"

        cached_schema = self.cache.get(schema_cache_key)
        if cached_schema is not None:
            logger.info(f"Using cached schema for {self.file_path}")
            return cached_schema

        if self._schema_inference is not None:
            schema = self._schema_inference(self.df)
        else:
            inference_engine = ExcelInferenceEngine(self.df)
            schema = inference_engine.infer()

        self.cache.set(schema_cache_key, schema)
        return schema

    def _load_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """Load data from file or cache."""
        cached = self.cache.get(file_path)
        if cached is not None:
            logger.info(f"Using cached data for {file_path}")
            return cached

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        try:
            if file_path.endswith(".parquet"):
                df = pd.read_parquet(file_path)
            elif file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            elif file_path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_path)
            else:
                df = pd.read_parquet(file_path)

            self.cache.set(file_path, df)
            logger.info(f"Loaded data with {len(df)} rows from {file_path}")
            return df
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return None

    async def _consult_brain(
        self, user_query: str, history_str: str = ""
    ) -> Dict[str, Any]:
        """Consult the planning brain to generate analysis plan."""
        custom_prompt = ""
        if self.chat_settings and self.chat_settings.custom_prompt:
            custom_prompt = f"\n\nAdditional Instructions:\n{self.chat_settings.custom_prompt}"
        
        messages = [
            {
                "role": "system",
                "content": EXCEL_BRAIN_PROMPT.format(
                    schema=self.schema,
                    history=history_str if history_str else "No previous conversation.",
                    query=user_query,
                    custom_prompt=custom_prompt,
                ),
            }
        ]

        try:
            response = await self._call_llm_with_usage_async(
                messages, temperature=0.1, timeout=60
            )

            if "```" in response:
                response_content = (
                    response.replace("```json", "").replace("```", "").strip()
                )
            else:
                response_content = response.strip()

            brain_output = json_repair.loads(response_content)

            if isinstance(brain_output, list):
                for item in brain_output:
                    if isinstance(item, dict) and "intent" in item:
                        brain_output = item
                        break
                else:
                    raise ValueError("Brain output missing 'intent' field")
            elif "intent" not in brain_output:
                raise ValueError("Brain output missing 'intent' field")

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
                        "description": "Answer the user's query using the dataframe.",
                        "chart_type": "none",
                    }
                ],
            }

    async def _generate_step_code(
        self, user_query: str, step: Dict[str, Any], prev_results: List[Dict[str, Any]]
    ) -> str:
        """Generate Python code for a step."""
        prev_summary = []

        for i, res in enumerate(prev_results):
            if res["type"] == "table":
                if self.chat_settings.zero_leaks_mode is True:
                    prev_summary.append(
                        f"Step {i}: Returned table with {res.get('total_rows', 0)} rows. Data REDACTED (Zero Leaks Mode)."
                    )
                else:
                    prev_summary.append(
                        f"Step {i}: Returned table with {res.get('total_rows', 0)} rows, Data Sample (first 5 rows): {res.get('data', [])[:5]}"
                    )
            elif res["type"] == "image":
                prev_summary.append(
                    f"Step {i}: Created chart - {res.get('description', '')}"
                )
            elif res["type"] == "text":
                if self.chat_settings.zero_leaks_mode is True:
                    prev_summary.append(
                        f"Step {i}: Text result REDACTED (Zero Leaks Mode)."
                    )
                else:
                    prev_summary.append(f"Step {i}: {res['data'][:100]}")

        prev_context = (
            "\n".join(prev_summary) if prev_summary else "This is the first step."
        )

        step_desc = step.get("title", step.get("description", ""))
        if step.get("chart_type") and step["chart_type"] != "none":
            step_desc += f" (Create a {step['chart_type']} visualization)"

        messages = [
            {
                "role": "system",
                "content": STEP_EXECUTOR_PROMPT.format(
                    step_number=step["step_number"],
                    schema=self.schema,
                    query=user_query,
                    step_type=step["type"],
                    step_description=step_desc,
                    previous_results=prev_context,
                ),
            }
        ]

        try:
            response = await self._call_llm_with_usage_async(
                messages, temperature=0.0, timeout=60
            )
            return response
        except Exception as e:
            logger.error(f"Step code generation failed: {e}")
            return f"result = 'Code generation failed for step {step['step_number']}: {str(e)}'\ndescription = 'Code generation failed'"

    async def _fix_step_code(
        self, bad_code: str, error_msg: str, step: Dict[str, Any]
    ) -> str:
        """Ask the LLM to self-correct failed step code."""
        step_desc = step.get("title", step.get("description", ""))
        if step.get("chart_type") and step["chart_type"] != "none":
            step_desc += f" (Create a {step['chart_type']} visualization)"

        messages = [
            {
                "role": "system",
                "content": CODE_FIX_PROMPT.format(
                    error=error_msg,
                    code=bad_code,
                    schema=self.schema,
                    step_type=step.get("type", "table"),
                    step_description=step_desc,
                ),
            }
        ]
        try:
            response = await self._call_llm_with_usage_async(
                messages, temperature=0.1, timeout=60
            )
            return response
        except Exception as e:
            logger.error(f"Fix code generation failed: {e}")
            return bad_code

    async def _generate_chat_response(
        self, user_query: str, history_str: str = ""
    ) -> str:
        """Generate a conversational response for general chat queries."""
        messages = [
            {
                "role": "system",
                "content": """You are Consigliere, a friendly data analysis assistant. 
Keep your response brief (1-2 sentences), conversational, and helpful.
If the user is greeting you, respond warmly.
If they're asking about your capabilities, explain briefly what you can do.
Do NOT mention schema, columns, or technical details.""",
            }
        ]

        if history_str:
            messages.append({"role": "user", "content": history_str})

        messages.append({"role": "user", "content": user_query})

        try:
            response = await self._call_llm_with_usage_async(
                messages, temperature=0.7, timeout=30
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Chat response error: {e}")
            return "Hi! I'm Consigliere, your data analysis assistant. Upload a file and ask me anything about your data!"

    def _execute_metadata_step(self, user_query: str) -> Dict[str, Any]:
        """Execute a METADATA step - return targeted schema info."""
        user_query_lower = user_query.lower()

        try:
            schema_json = json.loads(self.schema)
        except Exception:
            schema_json = {"sheets": [{"columns": []}]}

        sheets = schema_json.get("sheets", [])
        all_results = []

        for sheet in sheets:
            sheet_name = sheet.get("name", "Sheet1")
            columns = sheet.get("columns", [])
            row_count = sheet.get("row_count", 0)
            sheet_data = []

            if (
                "column" in user_query_lower
                or "structure" in user_query_lower
                or "schema" in user_query_lower
            ):
                for col in columns:
                    sheet_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Type": col.get("type", "unknown"),
                            "Role": col.get("role", "unknown"),
                        }
                    )
            elif "null" in user_query_lower:
                for col in columns:
                    profile = col.get("profile", {})
                    null_ratio = profile.get("null_ratio", 0)
                    sheet_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Null Count": (
                                int(row_count * null_ratio) if null_ratio > 0 else 0
                            ),
                            "Null Ratio": f"{null_ratio * 100:.1f}%",
                        }
                    )
            elif "distinct" in user_query_lower or "unique" in user_query_lower:
                for col in columns:
                    profile = col.get("profile", {})
                    sheet_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Distinct Values": profile.get("distinct_count", 0),
                        }
                    )
            elif (
                "row" in user_query_lower
                or "count" in user_query_lower
                or "size" in user_query_lower
            ):
                sheet_data.append(
                    {"Row Count": row_count, "Column Count": len(columns)}
                )
            elif (
                "numeric" in user_query_lower
                or "number" in user_query_lower
                or "measure" in user_query_lower
            ):
                for col in columns:
                    col_type = col.get("type", "")
                    if "int" in col_type or "float" in col_type:
                        profile = col.get("profile", {})
                        sheet_data.append(
                            {
                                "Column": col.get("name", ""),
                                "Type": col_type,
                                "Min": profile.get("min", "N/A"),
                                "Max": profile.get("max", "N/A"),
                                "Mean": (
                                    f"{profile.get('mean', 0):.2f}"
                                    if profile.get("mean")
                                    else "N/A"
                                ),
                            }
                        )
            elif (
                "string" in user_query_lower
                or "text" in user_query_lower
                or "category" in user_query_lower
            ):
                for col in columns:
                    col_type = col.get("type", "")
                    if "str" in col_type or "object" in col_type:
                        profile = col.get("profile", {})
                        sheet_data.append(
                            {
                                "Column": col.get("name", ""),
                                "Type": col_type,
                                "Distinct": profile.get("distinct_count", 0),
                            }
                        )
            else:
                for col in columns:
                    profile = col.get("profile", {})
                    sheet_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Type": col.get("type", "unknown"),
                            "Null %": f"{profile.get('null_ratio', 0) * 100:.1f}%",
                            "Distinct": profile.get("distinct_count", "N/A"),
                        }
                    )

            if sheet_data:
                df_sheet = pd.DataFrame(sheet_data)
                all_results.append(
                    {
                        "type": "table",
                        "table_name": sheet_name,
                        "data": df_sheet.fillna("").to_dict(orient="records"),
                        "columns": list(df_sheet.columns),
                        "total_rows": len(df_sheet),
                        "description": f"Schema for {sheet_name}",
                    }
                )

        if all_results:
            return {
                "type": "metadata",
                "tables": all_results,
                "description": "Data schema information",
            }
        else:
            return {
                "type": "text",
                "data": self.schema,
                "description": "Data schema information",
            }

    def _calculate_stats(self) -> str:
        """Run tactical scan of dataframe to extract key metrics."""
        stats = []
        stats.append(f"Total Records: {len(self.df):,}")
        stats.append(f"Total Columns: {len(self.df.columns)}")

        try:
            dup_count = self.df.duplicated().sum()
            if dup_count > 0:
                stats.append(
                    f"Duplicate Rows: {dup_count:,} ({dup_count / len(self.df) * 100:.1f}%)"
                )
        except Exception:
            pass

        try:
            null_counts = self.df.isnull().sum()
            null_cols = (
                null_counts[null_counts > 0].sort_values(ascending=False).head(5)
            )
            for col, count in null_cols.items():
                ratio = count / len(self.df) * 100
                stats.append(f"Nulls in '{col}': {count:,} ({ratio:.1f}%)")
        except Exception:
            pass

        for col in self.df.select_dtypes(include=["datetime", "datetimetz"]).columns:
            try:
                start = self.df[col].min()
                end = self.df[col].max()
                stats.append(f"Timeframe ({col}): {start} to {end}")
            except Exception:
                pass

        for col in self.df.select_dtypes(include=["object", "category"]).columns[:5]:
            try:
                unique_count = self.df[col].nunique()
                if unique_count < 50 and unique_count > 0:
                    if self.chat_settings.zero_leaks_mode is True:
                        stats.append(
                            f"Distinct values in '{col}': {unique_count} (values REDACTED - Zero Leaks Mode)"
                        )
                    else:
                        top_3 = self.df[col].value_counts().head(3)
                        top_list = [f"{val} ({count})" for val, count in top_3.items()]
                        stats.append(f"Top values in '{col}': {', '.join(top_list)}")
            except Exception:
                pass

        for col in self.df.select_dtypes(include=["number"]).columns[:5]:
            try:
                avg = self.df[col].mean()
                mx = self.df[col].max()
                mn = self.df[col].min()
                stats.append(f"'{col}': Min={mn:,.2f}, Max={mx:,.2f}, Avg={avg:,.2f}")
            except Exception:
                pass

        return "\n".join(stats)

    async def generate_dossier(self) -> dict:
        """Generate initial briefing about the dataset."""
        from app.core.prompts import DOSSIER_PROMPT

        stats_summary = self._calculate_stats()

        if self.chat_settings.zero_leaks_mode is True:
            preview = "REDACTED_FOR_PRIVACY (Zero Leaks Mode Active). Use schema and stats only."
        else:
            preview = self.df.head(5).to_string()

        messages = [
            {
                "role": "user",
                "content": DOSSIER_PROMPT.format(
                    schema=self.schema,
                    preview=preview,
                    stats=stats_summary,
                    source_type="Excel spreadsheet",
                ),
            }
        ]

        try:
            response = await self._call_llm_with_usage_async(
                messages, temperature=0.4, timeout=60
            )
            response_text = response

            if "```" in response_text:
                response_text = (
                    response_text.replace("```json", "").replace("```", "").strip()
                )

            parsed_json = json_repair.loads(response_text)

            if isinstance(parsed_json, dict):
                required_fields = [
                    "briefing",
                    "key_entities",
                    "data_alerts",
                    "recommended_actions",
                ]
                for field in required_fields:
                    if field not in parsed_json:
                        parsed_json[field] = [] if field != "briefing" else "Unknown"
                return parsed_json
            else:
                raise ValueError("Dossier output was not a dictionary")

        except Exception as e:
            logger.error(f"Error generating dossier: {e}")
            return {
                "briefing": f"I analyzed your data ({len(self.df):,} rows).",
                "key_entities": list(self.df.columns[:5]),
                "data_alerts": [],
                "recommended_actions": ["Show me the data", "Count rows"],
            }

    async def answer(
        self, user_query: str, history_str: str = ""
    ) -> AsyncGenerator[str, None]:
        """Main method to answer user queries."""
        yield json.dumps(
            {
                "type": "step_start",
                "step_number": 0,
                "description": "Analyzing request and planning...",
            }
        )

        brain_output = await self._consult_brain(user_query, history_str)
        intent = brain_output.get("intent", "DATA_ACTION")
        enhanced_prompt = brain_output.get("enhanced_prompt", user_query)

        if intent == "GENERAL_CHAT":
            chat_response = await self._generate_chat_response(user_query, history_str)
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": chat_response,
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
                        "text": "I'm here to help with professional data analysis. Let's keep it focused on the data.",
                        "steps": [],
                        "code": None,
                    },
                }
            )
            return

        plan_steps = brain_output.get("plan", [])

        if not plan_steps:
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": "I understood your request but couldn't generate a valid execution plan. Could you try asking in a different way?",
                        "steps": [],
                        "code": None,
                    },
                }
            )
            return

        all_results = []
        all_code = []

        for step in plan_steps:
            self.check_cancelled()

            step_start = {
                "type": "step_start",
                "step_number": step["step_number"],
                "description": step["title"],
                "step_type": step["type"],
            }
            if step.get("detailed_description") and step["type"] != "summary":
                step_start["detailed_description"] = step["detailed_description"]
            yield json.dumps(step_start)

            if step.get("type") == "metadata":
                metadata_result = self._execute_metadata_step(enhanced_prompt)
                metadata_result["step_number"] = step["step_number"]
                metadata_result["step_description"] = step["title"]
                metadata_result["step_type"] = "metadata"
                all_results.append(metadata_result)
                yield json.dumps({"type": "step_result", "data": metadata_result})
                continue

            raw_code = await self._generate_step_code(
                enhanced_prompt, step, all_results
            )

            max_code_retries = 3
            exec_result = None
            last_error = None
            current_raw_code = raw_code

            for code_attempt in range(max_code_retries):
                try:
                    clean_code = self.executor.sanitize(current_raw_code)
                    all_code.append(clean_code)
                except Exception as sec_err:
                    sec_error_msg = str(sec_err)
                    logger.error(
                        f"Step {step['step_number']} security violation: {sec_error_msg}"
                    )
                    last_error = f"Security Error: {sec_error_msg}"

                    if code_attempt < max_code_retries - 1:
                        current_raw_code = await self._fix_step_code(
                            current_raw_code, last_error, step
                        )
                        continue
                    else:
                        exec_result = {
                            "step_number": step["step_number"],
                            "type": "error",
                            "data": f"Security Error: {sec_error_msg}",
                        }
                        break

                if exec_result is None:
                    from app.core.utils import make_json_safe

                    candidate = await self.executor.execute(clean_code, {"df": self.df})
                    candidate = make_json_safe(candidate)
                    candidate["step_number"] = step["step_number"]
                    candidate["step_description"] = step.get(
                        "title", step.get("description", "")
                    )
                    candidate["step_type"] = step["type"]
                    if step.get("detailed_description") and step["type"] != "summary":
                        candidate["detailed_description"] = step["detailed_description"]

                    if candidate["type"] != "error":
                        exec_result = candidate
                        break

                    last_error = candidate["data"]
                    logger.warning(
                        f"Step {step['step_number']} execution error: {last_error}"
                    )

                    if code_attempt < max_code_retries - 1:
                        current_raw_code = await self._fix_step_code(
                            clean_code, last_error, step
                        )

            if exec_result is None:
                exec_result = {
                    "step_number": step["step_number"],
                    "step_description": step.get("title", step.get("description", "")),
                    "step_type": "error",
                    "type": "error",
                    "data": f"Step failed after {max_code_retries} attempts. Last error: {last_error}",
                }

            all_results.append(exec_result)
            yield json.dumps({"type": "step_result", "data": exec_result})

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

        code_log = ""
        for i, step in enumerate(plan_steps):
            code_log += f"# Step {step['step_number']}: {step.get('title', step.get('description', ''))}\n"
            if i < len(all_code):
                code_log += all_code[i] + "\n\n"
            code_log += "=" * 50 + "\n\n"

        token_usage = self.token_tracker.to_dict()
        yield json.dumps(
            {
                "type": "final_result",
                "data": {
                    "text": accumulated_text,
                    "steps": all_results,
                    "plan": brain_output,
                    "code": code_log,
                    "token_usage": {
                        "prompt_tokens": token_usage.get("prompt_tokens", 0),
                        "completion_tokens": token_usage.get("completion_tokens", 0),
                        "total_tokens": token_usage.get("total_tokens", 0),
                    },
                },
            }
        )
