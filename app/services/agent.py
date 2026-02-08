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
from typing import Dict, Any, List

from app.core.prompts import ANALYSIS_FORMAT_PROMPT, ANALYSIS_SYSTEM_PROMPT, DOSSIER_PROMPT, PLANNER_PROMPT, ROUTER_PROMPT, STEP_EXECUTOR_PROMPT
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
        
        # TODO: Make the schema smarter to have physical types and logical types, and sample values for categorical columns
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


    def _generate_plan(self, user_query: str, history_str: str = ""):
        messages = [
            {
                "role": "system",
                "content": PLANNER_PROMPT.format(
                    schema=self.schema,
                    history=history_str if history_str else "No previous conversation.",
                    query=user_query
                )
            }
        ]
        try:
            plan = self._call_llm(messages, temperature=0.0, timeout=60)
            print("DEBUG: Generated Plan:")
            print(plan)

            if '```' in plan:
                plan = plan.replace("```json", "").replace("```", "").strip()

            plan = json_repair.loads(plan)
            
            if "plan" not in plan or not isinstance(plan["plan"], list):
                raise ValueError("Invalid plan structure")
            

            for step in plan['plan']:
                if not all(k in step for k in ["step_number", "type", "description"]):
                    raise ValueError(f"Step missing required fields: {step}")
                if "depends_on" not in step:
                    step["depends_on"] = []

            return plan
        except Exception as e:
            print(f"DEBUG: Plan generation failed: {e}")
            return {
                "plan": [
                    {
                        "step_number": 1,
                        "type": "table",
                        "description": "Answer the user's query",
                        "depends_on": []
                    }
                ],
                "reasoning": "Fallback to simple single-step execution due to planning error."
            }
    

    def _generate_step_code(self, user_query, step: Dict[str, Any], prev_results: List[Dict[str, Any]]):
        prev_summary = []

        for i, res in enumerate(prev_results):
            if res["type"] == "table":
                prev_summary.append(f"Step {i}: Returned table with {res.get('total_rows', 0)} rows")
            elif res["type"] == "image":
                prev_summary.append(f"Step {i}: Created chart - {res.get('description', '')}")
            elif res["type"] == "text":
                prev_summary.append(f"Step {i}: {res['data'][:100]}")
        

        prev_context = "\n".join(prev_summary) if prev_summary else "this is the first step."

        messages = [
            {
                'role': 'system',
                 "content": STEP_EXECUTOR_PROMPT.format(
                    step_number=step["step_number"],
                    schema=self.schema,
                    query=user_query,
                    step_type=step["type"],
                    step_description=step["description"],
                    previous_results=prev_context
                )
            }
        ]

        try:
            code = self._call_llm(messages, temperature=0.0, timeout=60)
            return code
        except Exception as e:
            print(f"DEBUG: Step code generation failed for step {step['step_number']}: {e}")
            return f"result = 'Code generation failed for step {step['step_number']}: {str(e)}'"
     
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

    def _format_final_response(self, user_query: str, all_results: List[Dict[str, Any]]) -> str:
        """Convert technical result into natural language response"""


        summary_parts = []
        for i, result in enumerate(all_results, 1):
            if result["type"] == "table":
                summary_parts.append(f"Step {i}: Displayed {result.get('total_rows', 0)} rows of data")
            elif result["type"] == "image":
                summary_parts.append(f"Step {i}: Created visualization - {result.get('description', '')}")
            elif result["type"] == "text":
                summary_parts.append(f"Step {i}: {result['data'][:100]}")

        combined_summary = "\n".join(summary_parts)

        messages = [
            {
                "role": "system",
                "content": ANALYSIS_FORMAT_PROMPT.format(
                    user_query=user_query,
                    combined_summary=combined_summary,
                )
            }
        ]
        
        try:
            response = self._call_llm(messages, temperature=0.7, timeout=30)
            return response
        except Exception as e:
            print(f"FORMAT ERROR: {e}")
            # Fallback to simple response
            return f"Analysis complete. {combined_summary}"
    def answer(self, user_query: str, history_str: str = ""): # Removed -> dict type hint
        
        intent = self._decide_intent(user_query, history_str)

        if intent == "GENERAL_CHAT":
            yield json.dumps({
                "type": "final_result",
                "data": {
                    "text": "I'm Consigliere, your AI data analyst. I can help you analyze your data by running queries, creating visualizations, and generating insights. What would you like to know about your dataset?",
                    "steps": [],
                    "code": None
                }
            })
            return 
        
        if intent == "OFFENSIVE":
            yield json.dumps({
                "type": "final_result",
                "data": {
                    "text": "I'm here to help with data analysis. Please keep our conversation professional and focused on your data needs.",
                    "steps": [],
                    "code": None
                }
            })
            return 
        
        
        # NOTE: It's better to yield standard JSON strings if your endpoint expects ndjson
        yield json.dumps({"type": "step_start", "step_number": 0, "description": "Planning analysis steps..."})
        
        plan = self._generate_plan(user_query, history_str)

        if not plan or "plan" not in plan:
            yield json.dumps({
                "type": "final_result",
                "data": {
                    "text": "Sorry, I couldn't generate a valid plan. Please try rephrasing.",
                    "steps": [],
                    "code": None
                }
            })
            return

        all_results = []
        all_code = []

        for step in plan["plan"]:
            yield json.dumps({
                "type": "step_start", 
                "step_number": step['step_number'], 
                "description": step['description'],
                "step_type": step['type']
            })

            raw_code = self._generate_step_code(user_query, step, all_results)
            
            try:
                clean_code = self._sanitize_code(raw_code)
                all_code.append(clean_code)
            except Exception as e:
                # Handle Security Error
                yield json.dumps({
                    "type": "step_result",
                    "data": {
                        "step_number": step["step_number"],
                        "type": "error",
                        "data": f"Security Error: {str(e)}"
                    }
                })
                continue
            
            exec_result = self._execute_code(clean_code)
            
            exec_result['step_number'] = step["step_number"]
            exec_result['step_description'] = step["description"]
            exec_result['step_type'] = step['type']

            all_results.append(exec_result)

            yield json.dumps({
                "type": "step_result", 
                "data": exec_result
            })

        summary = self._format_final_response(user_query, all_results)

        yield json.dumps({
            "type": "final_result",
            "data": {
                "text": summary,
                "steps": all_results,
                "plan": plan,
                "code": f"\n\n#############\n\n".join(all_code)
            }
        })

    
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