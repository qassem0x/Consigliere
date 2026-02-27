import json
import uuid
import pandas as pd
import re
import os
import io
import contextlib
import matplotlib.pyplot as plt
import json_repair
import numpy as np

from typing import Dict, Any, List, Optional


def _make_json_safe(value: Any) -> Any:
    """Recursively convert value to JSON-serializable type"""
    if isinstance(value, pd.DataFrame):
        return _make_json_safe(value.to_dict(orient="records"))
    elif isinstance(value, pd.Series):
        return _make_json_safe(value.to_dict())
    elif isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.floating):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, dict):
        return {k: _make_json_safe(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    elif pd.isna(value):
        return None
    return value


from app.services.base_agent import BaseAgent
from app.services.excel.prompts import (
    CODE_FIX_PROMPT,
    EXCEL_BRAIN_PROMPT,
    STEP_EXECUTOR_PROMPT,
)
from app.core.prompts import (
    ANALYSIS_FORMAT_PROMPT,
    DOSSIER_PROMPT,
)
from app.services.excel.cache import DataCache
from app.services.excel.inference_engine import ExcelInferenceEngine
from app.core.llm import call_llm
from app.core.token_tracker import TokenTracker
from app.core.config import validate_env
from app.models.db_models import ChatSettings

validate_env()


class ExcelDataAgent(BaseAgent):
    def __init__(self, file_path: str, chat_settings: Optional[ChatSettings] = None):
        super().__init__(chat_settings)
        print(f"DEBUG: Initializing ExcelDataAgent for {file_path}")

        if chat_settings is not None:
            self.chat_settings = chat_settings
        else:
            self.chat_settings = ChatSettings(zero_leaks_mode=False, max_row_limit=100)
        print("DEBUG: chat_settings: ", self.chat_settings)
        self.cache_manager = DataCache()
        self.df = self.cache_manager.get_data(file_path)
        print(
            f"DEBUG: Loaded df with {len(self.df) if self.df is not None else 0} rows"
        )

        if self.df is None:
            raise ValueError(f"Failed to load data from {file_path}")

        inference_engine = ExcelInferenceEngine(self.df)
        self.schema = inference_engine.infer()
        print("SCHEMA: ", self.schema)

    def _consult_brain(self, user_query: str, history_str: str = ""):
        messages = [
            {
                "role": "system",
                "content": EXCEL_BRAIN_PROMPT.format(
                    schema=self.schema,
                    history=history_str if history_str else "No previous conversation.",
                    query=user_query,
                ),
            }
        ]

        try:
            response = self._call_llm_with_usage(messages, temperature=0.1, timeout=60)

            if "```" in response:
                response = response.replace("```json", "").replace("```", "").strip()

            brain_output = json_repair.loads(response)
            print("DEBUG: ", brain_output)

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
            print(f"DEBUG: Brain malfunction: {e}")
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

    def _generate_step_code(
        self, user_query, step: Dict[str, Any], prev_results: List[Dict[str, Any]]
    ):
        prev_summary = []

        for i, res in enumerate(prev_results):
            if res["type"] == "table":
                if self.chat_settings.zero_leaks_mode is True:
                    prev_summary.append(
                        f"Step {i}: Returned table with {res.get('total_rows', 0)} rows. Data REDACTED (Zero Leaks Mode)."
                    )
                else:
                    prev_summary.append(
                        f"Step {i}: Returned table with {res.get('total_rows', 0)} rows, Data Sample: {res.get('data', [])[:5]}"
                    )
            elif res["type"] == "image":
                prev_summary.append(
                    f"Step {i}: Created chart - {res.get('description', '')}"
                )
            elif res["type"] == "text":
                if self.chat_settings.zero_leaks_mode is True:
                    prev_summary.append(f"Step {i}: Text result REDACTED (Zero Leaks Mode).")
                else:
                    prev_summary.append(f"Step {i}: {res['data'][:100]}")

        prev_context = (
            "\n".join(prev_summary) if prev_summary else "This is the first step."
        )

        # Pass specific chart type guidance if available
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
            code = self._call_llm_with_usage(messages, temperature=0.0, timeout=60)
            return code
        except Exception as e:
            print(
                f"DEBUG: Step code generation failed for step {step['step_number']}: {e}"
            )
            return f"result = 'Code generation failed for step {step['step_number']}: {str(e)}'\ndescription = 'Code generation failed'"

    def _fix_step_code(
        self,
        bad_code: str,
        error_msg: str,
        step: Dict[str, Any],
    ) -> str:
        """Ask the LLM to self-correct failed step code using the runtime error."""
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
            fixed_code = self._call_llm_with_usage(messages, temperature=0.1, timeout=60)
            print(f"DEBUG: Step {step['step_number']} fix code received")
            return fixed_code
        except Exception as e:
            print(f"DEBUG: Fix code generation failed for step {step['step_number']}: {e}")
            return bad_code  # return original; sanitize will catch it again

    def _sanitize_code(self, code_string: str) -> str:
        """Extract and validate Python code, checking for security violations"""
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
            (r"\bcompile\s*\(", "compile function"),
            (r"\bimportlib\.", "importlib module"),
            (r"\bgetattr\s*\(\s*__builtins__", "builtins manipulation"),
            (r"\bglobals\s*\(", "globals access"),
            (r"\blocals\s*\(", "locals access"),
            (r"\bvars\s*\(", "vars access"),
            (r"\bdir\s*\(", "dir access"),
            (r"__\w+__", "dunder attribute access"),
        ]

        for pattern, description in banned_patterns:
            if re.search(pattern, clean_code, re.IGNORECASE):
                raise Exception(
                    f"Security violation: {description} is not allowed in generated code."
                )

        if "result" not in clean_code:
            print("WARNING: Generated code doesn't assign to 'result'")

        return clean_code

    def _execute_code(self, clean_code: str):
        """Execute sanitized Python code with timeout and return structured result"""
        print(f"DEBUG: _execute_code - self.df is None: {self.df is None}")
        print(f"DEBUG: _execute_code - self.df type: {type(self.df)}")

        if self.df is None:
            return {
                "type": "error",
                "data": "DataFrame not loaded. Please re-upload the file.",
            }

        local_scope = {
            "df": self.df,
            "pd": pd,
            "plt": plt,
            "result": None,
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "sorted": sorted,
            "any": any,
            "all": all,
        }
        stdout_capture = io.StringIO()

        try:
            plt.clf()
            plt.close("all")

            plt.style.use("dark_background")

            print(f"DEBUG: Executing code: {clean_code[:200]}...")

            with contextlib.redirect_stdout(stdout_capture):
                exec(clean_code, local_scope)

            result = local_scope.get("result")
            result_description = str(local_scope.get("description", ""))
            print(f"DEBUG: Query Description: {result_description}")

            # Check if a plot was created
            if plt.gcf().get_axes():
                ax = plt.gca()
                title = ax.get_title() or "Plot"
                x_label = ax.get_xlabel() or "X-axis"
                y_label = ax.get_ylabel() or "Y-axis"
                description = (
                    f"Chart Title: {title}; X-Axis: {x_label}; Y-Axis: {y_label}"
                )

                os.makedirs("static/plots", exist_ok=True)
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

            if isinstance(result, pd.DataFrame):
                if result.empty:
                    return {
                        "type": "text",
                        "data": "Query returned an empty result set.",
                    }
                return {
                    "type": "table",
                    "data": result.head(self.chat_settings.max_row_limit)
                    .fillna("")
                    .to_dict(orient="records"),
                    "columns": list(result.columns),
                    "total_rows": len(result),
                    "description": result_description,
                }

            elif isinstance(result, dict):
                # CASE 1: Column-Oriented Data (e.g. {'Name': ['A', 'B'], 'Age': [10, 20]})
                if result and all(isinstance(v, list) for v in result.values()):
                    try:
                        # Check if lists are of equal length (standard dataframe)
                        lengths = [len(v) for v in result.values()]
                        if len(set(lengths)) == 1:
                            df_temp = pd.DataFrame(result)
                            return {
                                "type": "table",
                                "data": df_temp.head(self.chat_settings.max_row_limit)
                                .fillna("")
                                .to_dict(orient="records"),
                                "columns": list(df_temp.columns),
                                "total_rows": len(df_temp),
                                "description": result_description or "Data Table",
                            }
                    except Exception:
                        pass  # Fall through to Summary View if DataFrame creation fails

                # CASE 2: Summary/Metric View
                try:
                    summary_rows = []

                    def process_value(key_prefix, value):
                        """Helper to flatten nested structures recursively"""
                        if isinstance(value, dict):
                            for k, v in value.items():
                                # Create composite key: "sex_distribution (male)"
                                new_key = f"{key_prefix} ({k})" if key_prefix else k
                                process_value(new_key, v)
                        elif isinstance(value, list):
                            # Cleanly format lists: "[A, B, C]" instead of "['A', 'B', 'C']"
                            # Truncate if too long to avoid UI bloat
                            if len(value) > 5:
                                clean_val = (
                                    ", ".join(map(str, value[:5]))
                                    + f", ... (+{len(value) - 5} more)"
                                )
                            else:
                                clean_val = ", ".join(map(str, value))
                            summary_rows.append(
                                {"Metric": key_prefix, "Value": clean_val}
                            )
                        else:
                            # Primitives (int, float, str)
                            summary_rows.append({"Metric": key_prefix, "Value": value})

                    # Iterate main dictionary
                    for k, v in result.items():
                        process_value(k, v)

                    df_temp = pd.DataFrame(summary_rows)

                    return {
                        "type": "table",
                        "data": df_temp.fillna("").to_dict(orient="records"),
                        "columns": ["Metric", "Value"],
                        "total_rows": len(df_temp),
                        "description": result_description or "Summary Statistics",
                    }
                except Exception as e:
                    print(f"DEBUG: Failed to create summary table: {e}")
                    # CASE 3: Absolute Fallback (Raw JSON)
                    return {
                        "type": "text",
                        "data": json.dumps(result, indent=2, default=str),
                    }

            elif isinstance(result, pd.Series):
                if result.empty:
                    return {"type": "text", "data": "Query returned an empty result."}

                df_temp = result.reset_index()
                df_temp.columns = (
                    ["index", "value"]
                    if len(df_temp.columns) == 2
                    else list(df_temp.columns)
                )

                return {
                    "type": "table",
                    "data": df_temp.head(self.chat_settings.max_row_limit)
                    .fillna("")
                    .to_dict(orient="records"),
                    "columns": list(df_temp.columns),
                    "total_rows": len(df_temp),
                    "description": result_description,
                }

            elif result is not None:
                return {"type": "text", "data": str(result)}

            else:
                output = stdout_capture.getvalue().strip()
                if output:
                    return {"type": "text", "data": output}
                else:
                    return {
                        "type": "text",
                        "data": "Code executed successfully but produced no output. Try assigning your result to the 'result' variable.",
                    }

        except Exception as e:
            plt.close("all")
            return {"type": "error", "data": f"Execution Error: {str(e)}"}

    def answer(self, user_query: str, history_str: str = ""):
        # 1. Consult the Brain (Unified Routing + Planning)
        yield json.dumps(
            {
                "type": "step_start",
                "step_number": 0,
                "description": "Analyzing request and planning...",
            }
        )

        brain_output = self._consult_brain(user_query, history_str)
        intent = brain_output.get("intent", "DATA_ACTION")
        enhanced_prompt = brain_output.get("enhanced_prompt", user_query)

        # 2. Handle Non-Data Intents
        if intent == "GENERAL_CHAT":
            chat_response = self._generate_chat_response(user_query, history_str)
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

        # METADATA and DATA_ACTION both use plan execution
        # 3. Handle DATA_ACTION (Execute the Plan)
        plan_steps = brain_output.get("plan", [])
        print("DEBUG: planning steps: ", plan_steps)

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
            step_start = {
                "type": "step_start",
                "step_number": step["step_number"],
                "description": step["title"],
                "step_type": step["type"],
            }
            if step.get("detailed_description") and step["type"] != "summary":
                step_start["detailed_description"] = step["detailed_description"]
            yield json.dumps(step_start)

            # Handle METADATA step type - return targeted schema info
            if step.get("type") == "metadata":
                metadata_result = self._execute_metadata_step(enhanced_prompt)
                metadata_result["step_number"] = step["step_number"]
                metadata_result["step_description"] = step["title"]
                metadata_result["step_type"] = "metadata"
                all_results.append(metadata_result)
                yield json.dumps({"type": "step_result", "data": metadata_result})
                continue

            # Generate Code
            raw_code = self._generate_step_code(enhanced_prompt, step, all_results)

            # Retry loop: generate → sanitize → execute → self-correct on error
            max_code_retries = 3
            exec_result = None
            last_error = None
            current_raw_code = raw_code

            for code_attempt in range(max_code_retries):
                try:
                    clean_code = self._sanitize_code(current_raw_code)
                    all_code.append(clean_code)
                except Exception as sec_err:
                    # Security violation — never retry, halt this step
                    print(f"DEBUG: Step {step['step_number']} security violation: {sec_err}")
                    exec_result = {
                        "step_number": step["step_number"],
                        "type": "error",
                        "data": f"Security Error: {str(sec_err)}",
                    }
                    break

                candidate = self._execute_code(clean_code)
                candidate = _make_json_safe(candidate)
                candidate["step_number"] = step["step_number"]
                candidate["step_description"] = step.get("title", step.get("description", ""))
                candidate["step_type"] = step["type"]
                if step.get("detailed_description") and step["type"] != "summary":
                    candidate["detailed_description"] = step["detailed_description"]

                if candidate["type"] != "error":
                    exec_result = candidate
                    break

                # Execution returned an error — collect error and try to self-correct
                last_error = candidate["data"]
                print(
                    f"DEBUG: Step {step['step_number']} execution error "
                    f"(attempt {code_attempt + 1}/{max_code_retries}): {last_error}"
                )

                if code_attempt < max_code_retries - 1:
                    print(
                        f"DEBUG: Step {step['step_number']}: requesting code fix from LLM…"
                    )
                    current_raw_code = self._fix_step_code(clean_code, last_error, step)

            # If every attempt failed, keep the last error result
            if exec_result is None:
                exec_result = {
                    "step_number": step["step_number"],
                    "step_description": step.get("title", step.get("description", "")),
                    "step_type": "error",
                    "type": "error",
                    "data": (
                        f"Step failed after {max_code_retries} attempts. "
                        f"Last error: {last_error}"
                    ),
                }

            all_results.append(exec_result)

            yield json.dumps({"type": "step_result", "data": exec_result})

        # 4. Final Summary - Stream token by token
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

        # Construct full code log
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

    def _calculate_stats(self) -> str:
        """Run tactical scan of dataframe to extract key metrics"""
        stats = []
        stats.append(f"Total Records: {len(self.df):,}")
        stats.append(f"Total Columns: {len(self.df.columns)}")

        for col in self.df.select_dtypes(include=["datetime", "datetimetz"]).columns:
            try:
                start = self.df[col].min()
                end = self.df[col].max()
                stats.append(f"Timeframe ({col}): {start} to {end}")
            except:
                pass

        for col in self.df.select_dtypes(include=["object", "category"]).columns[:5]:
            try:
                unique_count = self.df[col].nunique()
                if unique_count < 50 and unique_count > 0:
                    if self.chat_settings.zero_leaks_mode is True:
                        stats.append(f"Distinct values in '{col}': {unique_count} (values REDACTED - Zero Leaks Mode)")
                    else:
                        top_3 = self.df[col].value_counts().head(3)
                        top_list = [f"{val} ({count})" for val, count in top_3.items()]
                        stats.append(f"Top values in '{col}': {', '.join(top_list)}")
            except:
                pass

        for col in self.df.select_dtypes(include=["number"]).columns[:5]:
            try:
                avg = self.df[col].mean()
                mx = self.df[col].max()
                mn = self.df[col].min()
                stats.append(f"'{col}': Min={mn:,.2f}, Max={mx:,.2f}, Avg={avg:,.2f}")
            except:
                pass

        return "\n".join(stats)

    def generate_dossier(self) -> dict:
        """Generate initial briefing about the dataset"""
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
            response_text = self._call_llm_with_usage(
                messages, temperature=0.4, timeout=60
            )

            if "```" in response_text:
                response_text = (
                    response_text.replace("```json", "").replace("```", "").strip()
                )

            parsed_json = json_repair.loads(response_text)

            if isinstance(parsed_json, dict):
                required_fields = ["briefing", "key_entities", "recommended_actions"]
                for field in required_fields:
                    if field not in parsed_json:
                        parsed_json[field] = [] if field != "briefing" else "Unknown"
                return parsed_json
            else:
                raise ValueError("Dossier output was not a dictionary")

        except Exception as e:
            print(f"Error generating dossier: {e}")
            return {
                "briefing": f"I analyzed your data ({len(self.df):,} rows).",
                "key_entities": list(self.df.columns[:5]),
                "recommended_actions": ["Show me the data", "Count rows"],
            }

    def _generate_chat_response(self, user_query: str, history_str: str = "") -> str:
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
            response = self._call_llm_with_usage(messages, temperature=0.7, timeout=30)
            return response.strip()
        except Exception as e:
            print(f"DEBUG: Chat response error: {e}")
            return "Hi! I'm Consigliere, your data analysis assistant. Upload a file and ask me anything about your data!"

    def _execute_metadata_step(self, user_query: str) -> Dict[str, Any]:
        """Execute a METADATA step - return targeted schema info based on user question."""
        user_query_lower = user_query.lower()

        import json

        try:
            schema_json = json.loads(self.schema)
        except:
            schema_json = {"sheets": [{"columns": []}]}

        sheets = schema_json.get("sheets", [])

        all_results = []

        for sheet in sheets:
            sheet_name = sheet.get("name", "Sheet1")
            columns = sheet.get("columns", [])
            row_count = sheet.get("row_count", 0)

            sheet_data = []

            # Determine what to return based on user's question
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
                    distinct_count = profile.get("distinct_count", 0)
                    sheet_data.append(
                        {
                            "Column": col.get("name", ""),
                            "Distinct Values": distinct_count,
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
                # Default: return full schema overview
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
