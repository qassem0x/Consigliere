import contextlib
import io
import os
import re
import uuid
from typing import Any, Dict

import matplotlib.pyplot as plt
import pandas as pd


class PythonSandboxExecutor:
    """Executor for Python code in a sandboxed environment."""

    def __init__(self, max_row_limit: int = 100, plots_dir: str = "static/plots"):
        self.max_row_limit = max_row_limit
        self.plots_dir = plots_dir
        os.makedirs(plots_dir, exist_ok=True)

    def sanitize(self, code_string: str) -> str:
        """Extract and validate Python code, checking for security violations."""
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
            import logging

            logging.getLogger(__name__).warning(
                "Generated code doesn't assign to 'result'"
            )

        return clean_code

    async def execute(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code with the given context."""
        return self._execute_sync(code, context)

    def _execute_sync(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        df = context.get("df")

        if df is None:
            return {
                "type": "error",
                "data": "DataFrame not loaded. Please re-upload the file.",
            }

        local_scope = {
            "df": df,
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

            with contextlib.redirect_stdout(stdout_capture):
                exec(code, local_scope)

            result = local_scope.get("result")
            result_description = str(local_scope.get("description", ""))

            if plt.gcf().get_axes():
                ax = plt.gca()
                title = ax.get_title() or "Plot"
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

            if isinstance(result, pd.DataFrame):
                if result.empty:
                    return {
                        "type": "text",
                        "data": "Query returned an empty result set.",
                    }
                return {
                    "type": "table",
                    "data": result.head(self.max_row_limit)
                    .fillna("")
                    .to_dict(orient="records"),
                    "columns": list(result.columns),
                    "total_rows": len(result),
                    "description": result_description,
                }

            elif isinstance(result, dict):
                if result and all(isinstance(v, list) for v in result.values()):
                    lengths = [len(v) for v in result.values()]
                    if len(set(lengths)) == 1:
                        df_temp = pd.DataFrame(result)
                        return {
                            "type": "table",
                            "data": df_temp.head(self.max_row_limit)
                            .fillna("")
                            .to_dict(orient="records"),
                            "columns": list(df_temp.columns),
                            "total_rows": len(df_temp),
                            "description": result_description or "Data Table",
                        }

                try:
                    summary_rows = []

                    def process_value(key_prefix, value):
                        if isinstance(value, dict):
                            for k, v in value.items():
                                new_key = f"{key_prefix} ({k})" if key_prefix else k
                                process_value(new_key, v)
                        elif isinstance(value, list):
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
                            summary_rows.append({"Metric": key_prefix, "Value": value})

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
                except Exception:
                    return {"type": "text", "data": str(result)}

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
                    "data": df_temp.head(self.max_row_limit)
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


import contextlib
