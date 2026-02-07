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
from litellm import completion
from tenacity import retry, stop_after_attempt, wait_exponential
import litellm

from app.core.prompts import ANALYSIS_FORMAT_PROMPT, ANALYSIS_SYSTEM_PROMPT, DOSSIER_PROMPT, ROUTER_PROMPT
from app.services.cache import DataCache

dotenv.load_dotenv()

# Configure LiteLLM
litellm.drop_params = True  # Ignore unsupported params instead of erroring
litellm.set_verbose = False  # Set to True for debugging

MODEL_NAME = os.getenv("MODEL_NAME", "ollama/llama3.2")  # Default to local
class DataAgent:
    def __init__(self, file_path: str):
        self.cache_manager = DataCache()
        self.df = self.cache_manager.get_data(file_path)
        
        self.schema = "\n".join([f"- {col}: {dtype}" for col, dtype in self.df.dtypes.items()])
        self.model_name = MODEL_NAME

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _call_llm(self, messages: list, temperature: float = 0.0, timeout: int = 60) -> str:
        """Unified LLM caller with retry logic and error handling"""
        try:
            response = completion(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                timeout=timeout
            )
            return response.choices[0].message.content.strip()
        except litellm.exceptions.RateLimitError as e:
            print(f"RATE LIMIT HIT: {e}")
            raise Exception("Rate limit exceeded. Please wait a moment and try again.")
        except litellm.exceptions.Timeout as e:
            print(f"TIMEOUT: {e}")
            raise Exception("LLM request timed out. Try a simpler query.")
        except Exception as e:
            print(f"LLM ERROR: {e}")
            raise Exception(f"LLM service error: {str(e)}")

    def _decide_intent(self, user_query: str, history_str: str = "") -> str:
        """Route query to appropriate handler"""
        messages = [
            {
                "role": "user", 
                "content": ROUTER_PROMPT.format(
                    query=user_query, 
                    history=history_str if history_str else "No previous conversation."
                )
            }
        ]
        
        try:
            text = self._call_llm(messages, temperature=0.0, timeout=30)
            
            # Clean markdown code blocks if present
            if "```" in text:
                text = text.replace("```json", "").replace("```", "").strip()
            
            parsed = json_repair.loads(text)
            intent = parsed.get("intent", "DATA_ACTION")
            print(f"DEBUG: Router decided intent = {intent}")
            return intent
            
        except Exception as e:
            print(f"ROUTER ERROR: {e}")
            return "DATA_ACTION"  # Fail-safe: assume data question

    def _generate_python_code(self, user_query: str, history_str: str = "") -> str:
        """Generate Python code using LLM"""
        messages = [
            {
                "role": "system",
                "content": ANALYSIS_SYSTEM_PROMPT.format(
                    schema=self.schema,
                    history=history_str if history_str else "No previous conversation.",
                    query=user_query
                )
            }
        ]
        
        print("DEBUG: Generating Python code...")
        
        try:
            code = self._call_llm(messages, temperature=0.0, timeout=60)
            return code
        except Exception as e:
            print(f"DEBUG: Code generation failed: {e}")
            return f"result = 'Code Generation Error: {str(e)}'"
        
    def _sanitize_code(self, code_string: str) -> str:
        """Extract and validate Python code, checking for security violations"""
        # Remove markdown code blocks if present
        match = re.search(r"```(?:python|py)?\n?(.*?)\n?```", code_string, re.DOTALL)
        clean_code = match.group(1).strip() if match else code_string.strip()

        # Security Check - banned patterns
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
                raise Exception(f"Security violation: {description} is not allowed in generated code.")
        
        # Additional check: ensure code assigns to 'result'
        if "result" not in clean_code:
            print("WARNING: Generated code doesn't assign to 'result'")
        
        return clean_code

    def _execute_code(self, clean_code: str):
        """Execute sanitized Python code with timeout and return structured result"""
        local_scope = {'df': self.df, 'pd': pd, 'plt': plt, 'result': None}
        stdout_capture = io.StringIO()

        try:
            # Clear any existing plots
            plt.clf()
            plt.close('all')

            # Execute code with stdout capture
            with contextlib.redirect_stdout(stdout_capture):
                exec(clean_code, {"__builtins__": __builtins__}, local_scope)
            
            result = local_scope.get('result')
            result_description = local_scope.get('description', '')
            print(f"DEBUG: Query Description: {result_description}")
            # Check if a plot was created
            if plt.gcf().get_axes():
                ax = plt.gca()
                title = ax.get_title() or "Plot"
                x_label = ax.get_xlabel() or "X-axis"
                y_label = ax.get_ylabel() or "Y-axis"
                description = f"Chart Title: {title}; X-Axis: {x_label}; Y-Axis: {y_label}"
                
                # Ensure plots directory exists
                os.makedirs("static/plots", exist_ok=True)
                
                file_name = f"plot_{uuid.uuid4()}.png"
                file_path = os.path.join("static", "plots", file_name)
                plt.savefig(file_path, bbox_inches='tight', dpi=100)
                plt.close('all')
                
                return {
                    "type": "image",
                    "data": f"/static/plots/{file_name}",
                    "mime": "image/png",
                    "description": description
                }

            # DataFrame result
            if isinstance(result, pd.DataFrame):
                if result.empty:
                    return {
                        "type": "text",
                        "data": "Query returned an empty result set."
                    }
                return {
                    "type": "table",
                    "data": result.head(50).fillna("").to_dict(orient="records"),
                    "columns": list(result.columns),
                    "total_rows": len(result),
                    "description": result_description
                }

            # Series result (convert to DataFrame)
            elif isinstance(result, pd.Series):
                if result.empty:
                    return {
                        "type": "text",
                        "data": "Query returned an empty result."
                    }
                
                df_temp = result.reset_index()
                df_temp.columns = ['index', 'value'] if len(df_temp.columns) == 2 else list(df_temp.columns)
                
                return {
                    "type": "table",
                    "data": df_temp.head(50).fillna("").to_dict(orient="records"),
                    "columns": list(df_temp.columns),
                    "total_rows": len(df_temp),
                    "description": result_description
                }
            
            # Direct result (string, number, dict, list, etc.)
            elif result is not None:
                return {
                    "type": "text",
                    "data": str(result)
                }

            # No result but stdout captured (print statements)
            else:
                output = stdout_capture.getvalue().strip()
                if output:
                    return {
                        "type": "text",
                        "data": output
                    }
                else:
                    return {
                        "type": "text",
                        "data": "Code executed successfully but produced no output. Try assigning your result to the 'result' variable."
                    }

        except Exception as e:
            # Clean up plots on error
            plt.close('all')
            return {
                "type": "error",
                "data": f"Execution Error: {str(e)}"
            }

    def _format_response(self, user_query: str, raw_result: any) -> str:
        """Convert technical result into natural language response"""
        # Handle different result types for summary
        if isinstance(raw_result, dict):
            if raw_result.get("type") == "error":
                return f"I encountered an error: {raw_result.get('data', 'Unknown error')}"
            elif raw_result.get("type") == "image":
                data_summary = f"Generated chart: {raw_result.get('description', 'Visualization')}"
            elif raw_result.get("type") == "table":
                row_count = raw_result.get("total_rows", len(raw_result.get("data", [])))
                data_summary = f"Query returned {row_count} rows with columns: {', '.join(raw_result.get('columns', []))}"
            else:
                data_summary = str(raw_result.get("data", ""))
        else:
            data_summary = str(raw_result)
        
        messages = [
            {
                "role": "system",
                "content": ANALYSIS_FORMAT_PROMPT.format(
                    query=user_query,
                    result=data_summary
                )
            }
        ]
        
        try:
            response = self._call_llm(messages, temperature=0.7, timeout=30)
            return response
        except Exception as e:
            print(f"FORMAT ERROR: {e}")
            # Fallback to simple response
            return f"Analysis complete. {data_summary}"

    def answer(self, user_query: str, history_str: str = "") -> dict:
        """Main method to process user query and return formatted response"""
        
        intent = self._decide_intent(user_query, history_str)
        
        if intent == "GENERAL_CHAT":
            return {
                "text": "I'm Consigliere, your AI data analyst. I can help you analyze your data by running queries, creating visualizations, and generating insights. What would you like to know about your dataset?",
                "result": {"type": "text", "data": "General conversation - no data analysis performed."}
            }
        
        if intent == "OFFENSIVE":
            return {
                "text": "I'm here to help with data analysis. Please keep our conversation professional and focused on your data needs.",
                "result": {"type": "text", "data": "Request rejected due to inappropriate content."}
            }
        
        raw_code = self._generate_python_code(user_query, history_str)

        try:
            clean_code = self._sanitize_code(raw_code)
        except Exception as e:
            return {
                "text": f"Security Error: {str(e)}",
                "result": {"type": "error", "data": str(e)}
            }
        
        # Debug output
        print("DEBUG: Generated Code:")
        print(clean_code)
        print("=" * 80)
        
        execution_result = self._execute_code(clean_code)

        print("=" * 80)
        print("DEBUG: Execution Result:")
        print(execution_result)
        print("=" * 80)
        
        if execution_result["type"] == "error":
            summary = f"I encountered an error while processing your request: {execution_result['data']}"
        elif execution_result["type"] == "table":
            # WARNING: Add Option later for user if he wants to send data to llm or not
            if True:
                summary = self._format_response(user_query, execution_result['data'][:5] + "... That's only data sample due to response length limits. The full result has " + str(execution_result.get("total_rows", "many")) + " rows. so don't make assumptions based on just the preview.")
            else:
                # just use first generated description if user doesn't want to send data to llm
                summary = execution_result['description'] 
        elif execution_result["type"] == "image":
            summary = self._format_response(user_query, f"I've created a visualization for you: {execution_result.get('description', '')}")
        else:
            summary = self._format_response(user_query, execution_result["data"])
        
        return {
            "text": summary,
            "result": execution_result,
            "python": clean_code
        }

    def _calculate_stats(self) -> str:
        """Run tactical scan of dataframe to extract key metrics"""
        stats = []
        
        stats.append(f"Total Records: {len(self.df):,}")
        stats.append(f"Total Columns: {len(self.df.columns)}")
        
        # Date ranges
        for col in self.df.select_dtypes(include=['datetime', 'datetimetz']).columns:
            try:
                start = self.df[col].min()
                end = self.df[col].max()
                stats.append(f"Timeframe ({col}): {start} to {end}")
            except:
                pass

        # Categorical columns - top values
        for col in self.df.select_dtypes(include=['object', 'category']).columns[:5]:
            try:
                unique_count = self.df[col].nunique()
                if unique_count < 50 and unique_count > 0:
                    top_3 = self.df[col].value_counts().head(3)
                    top_list = [f"{val} ({count})" for val, count in top_3.items()]
                    stats.append(f"Top values in '{col}': {', '.join(top_list)}")
            except:
                pass

        # Numerical columns - summary stats
        for col in self.df.select_dtypes(include=['number']).columns[:5]:
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
                    stats=stats_summary
                )
            }
        ]

        try:
            response_text = self._call_llm(messages, temperature=0.4, timeout=60)
            
            print("DEBUG: Dossier Response:")
            print(response_text[:500])  # Print first 500 chars
            
            # Clean markdown if present
            if "```" in response_text:
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            parsed_json = json_repair.loads(response_text)
            
            if isinstance(parsed_json, dict):
                # Validate required fields
                required_fields = ["file_type", "briefing", "key_entities", "recommended_actions"]
                for field in required_fields:
                    if field not in parsed_json:
                        print(f"WARNING: Missing field '{field}' in dossier")
                        parsed_json[field] = [] if field in ["key_entities", "recommended_actions"] else "Unknown"
                
                return parsed_json
            else:
                print(f"WARNING: Dossier was not a dict: {type(parsed_json)}")
                raise ValueError("Dossier output was not a dictionary")
                
        except Exception as e:
            print(f"Error generating dossier: {e}")
            return {
                "file_type": "Dataset",
                "briefing": f"I analyzed your data ({len(self.df):,} rows, {len(self.df.columns)} columns) but couldn't generate a full briefing. I'm ready to answer your questions!",
                "key_entities": list(self.df.columns[:5]),
                "recommended_actions": [
                    "Show me the first 10 rows",
                    "What columns are available?",
                    f"How many rows are in this dataset?"
                ]
            }