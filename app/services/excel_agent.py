import json
import uuid
import pandas as pd
import re
import os
import dotenv
import io
import contextlib
import matplotlib.pyplot as plt
import json_repair

from typing import Dict, Any, List

# UPDATED: We now only need BRAIN_PROMPT and the others
from app.core.prompts import (
    ANALYSIS_FORMAT_PROMPT,
    DOSSIER_PROMPT,
    EXCEL_BRAIN_PROMPT,
    STEP_EXECUTOR_PROMPT,
)
from app.services.base_agent import BaseAgent
from app.services.excel_agent_cache import DataCache
from app.services.llm import call_llm

dotenv.load_dotenv()


class ExcelDataAgent(BaseAgent):
    def __init__(self, file_path: str):
        self.cache_manager = DataCache()
        self.df = self.cache_manager.get_data(file_path)

        # Smart Schema Generation
        schema_parts = []
        for col in self.df.columns:
            dtype = self.df[col].dtype
            if pd.api.types.is_numeric_dtype(dtype):
                sample = f"Range: {self.df[col].min()} to {self.df[col].max()}"
            else:
                if self.df[col].nunique() < 20:
                    top_vals = self.df[col].unique()[:5].tolist()
                    sample = f"Sample: {top_vals}"
                else:
                    sample = f"Unique Values: {self.df[col].nunique()} from {len(self.df)} records"
            schema_parts.append(f"- {col} ({dtype}): {sample}")

        self.schema = "\n".join(schema_parts)
        print("SCHEMA: ", self.schema)

    def _consult_brain(self, user_query: str, history_str: str = ""):
        messages = [
            {
                "role": "system",
                "content": BRAIN_PROMPT.format(
                    schema=self.schema,
                    history=history_str if history_str else "No previous conversation.",
                    query=user_query,
                ),
            }
        ]

        try:
            response = call_llm(messages, temperature=0.1, timeout=60)

            if "```" in response:
                response = response.replace("```json", "").replace("```", "").strip()

            brain_output = json_repair.loads(response)

            if "intent" not in brain_output:
                raise ValueError("Brain output missing 'intent' field")

            return brain_output

        except Exception as e:
            print(f"DEBUG: Brain malfunction: {e}")
            return {
                "intent": "DATA_ACTION",
                "reasoning": "Fallback due to JSON parsing error.",
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
                prev_summary.append(
                    f"Step {i}: Returned table with {res.get('total_rows', 0)} rows"
                )
            elif res["type"] == "image":
                prev_summary.append(
                    f"Step {i}: Created chart - {res.get('description', '')}"
                )
            elif res["type"] == "text":
                prev_summary.append(f"Step {i}: {res['data'][:100]}")

        prev_context = (
            "\n".join(prev_summary) if prev_summary else "This is the first step."
        )

        # Pass specific chart type guidance if available
        step_desc = step["description"]
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
            code = call_llm(messages, temperature=0.0, timeout=60)
            return code
        except Exception as e:
            print(
                f"DEBUG: Step code generation failed for step {step['step_number']}: {e}"
            )
            return f"result = 'Code generation failed for step {step['step_number']}: {str(e)}'"

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
        local_scope = {"df": self.df, "pd": pd, "plt": plt, "result": None}
        stdout_capture = io.StringIO()

        try:
            plt.clf()
            plt.close("all")

            with contextlib.redirect_stdout(stdout_capture):
                exec(clean_code, {"__builtins__": __builtins__}, local_scope)

            result = local_scope.get("result")
            result_description = local_scope.get("description", "")
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
                    "data": result.head(50).fillna("").to_dict(orient="records"),
                    "columns": list(result.columns),
                    "total_rows": len(result),
                    "description": result_description,
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
                    "data": df_temp.head(50).fillna("").to_dict(orient="records"),
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

    def _format_final_response(
        self, user_query: str, all_results: List[Dict[str, Any]]
    ) -> str:
        """Convert technical result into natural language response"""
        # If the brain decided on general chat, this function might not be needed
        # but we keep it for data action summaries.

        summary_parts = []
        for i, result in enumerate(all_results, 1):
            if result["type"] == "table":
                summary_parts.append(
                    f"Step {i}: Displayed {result.get('total_rows', 0)} rows of data"
                )
            elif result["type"] == "image":
                summary_parts.append(
                    f"Step {i}: Created visualization - {result.get('description', '')}"
                )
            elif result["type"] == "text":
                summary_parts.append(f"Step {i}: {result['data'][:100]}")

        combined_summary = "\n".join(summary_parts)

        messages = [
            {
                "role": "system",
                "content": ANALYSIS_FORMAT_PROMPT.format(
                    user_query=user_query,
                    combined_summary=combined_summary,
                ),
            }
        ]

        try:
            response = call_llm(messages, temperature=0.7, timeout=30)
            return response
        except Exception as e:
            print(f"FORMAT ERROR: {e}")
            return f"Analysis complete. {combined_summary}"

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

        # 2. Handle Non-Data Intents
        if intent == "GENERAL_CHAT":
            reasoning = brain_output.get("reasoning", "I can help you with that.")
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": (
                            reasoning
                            if len(reasoning) > 10
                            else "I'm Consigliere, ready to analyze your data."
                        ),
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
            yield json.dumps(
                {
                    "type": "step_start",
                    "step_number": step["step_number"],
                    "description": step["title"],
                    "step_type": step["type"],
                }
            )

            # Generate Code
            raw_code = self._generate_step_code(user_query, step, all_results)

            try:
                clean_code = self._sanitize_code(raw_code)
                all_code.append(clean_code)
            except Exception as e:
                yield json.dumps(
                    {
                        "type": "step_result",
                        "data": {
                            "step_number": step["step_number"],
                            "type": "error",
                            "data": f"Security Error: {str(e)}",
                        },
                    }
                )
                continue

            # Execute Code
            exec_result = self._execute_code(clean_code)
            exec_result["step_number"] = step["step_number"]
            exec_result["step_description"] = step["title"]
            exec_result["step_type"] = step["type"]

            all_results.append(exec_result)

            yield json.dumps({"type": "step_result", "data": exec_result})

        # 4. Final Summary
        summary = self._format_final_response(user_query, all_results)

        # Construct full code log
        code_log = ""
        for i, step in enumerate(plan_steps):
            code_log += f"# Step {step['step_number']}: {step['description']}\n"
            if i < len(all_code):
                code_log += all_code[i] + "\n\n"
            code_log += "=" * 50 + "\n\n"

        yield json.dumps(
            {
                "type": "final_result",
                "data": {
                    "text": summary,
                    "steps": all_results,
                    "plan": brain_output,  # Return full brain output context
                    "code": code_log,
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
            response_text = call_llm(messages, temperature=0.4, timeout=60)

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
