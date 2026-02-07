import json
import uuid
import pandas as pd
import re
import os
import dotenv
import io
import contextlib
import google.generativeai as genai
from app.core.prompts import ANALYSIS_FORMAT_PROMPT, ANALYSIS_SYSTEM_PROMPT, DOSSIER_PROMPT, ROUTER_PROMPT
import matplotlib.pyplot as plt
import json_repair


dotenv.load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# MODEL_NAME = 'models/gemma-3-27b-it' 
# MODEL_NAME = 'models/gemini-3-flash-preview'  # Stronger Model

MODEL_NAME = os.getenv("MODEL_NAME")

class DataAgent:
    def __init__(self, file_path: str):
        self.df = pd.read_parquet(file_path)
        self.schema = "\n".join([f"- {col}: {dtype}" for col, dtype in self.df.dtypes.items()])
        self.model = genai.GenerativeModel(MODEL_NAME)

    def _decide_intent(self, user_query: str, history_str: str="") -> str:
        prompt = ROUTER_PROMPT.format(query=user_query, history=history_str if history_str else "No previous conversation.")
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0, 
                    # response_mime_type="application/json"
                )
            )
            text = response.text.strip()
            
            if "```" in text:
                text = text.replace("```json", "").replace("```", "").strip()
            
            return json_repair.loads(text).get("intent", "GENERAL_CHAT")
        except Exception as e:
            print(f"ROUTER ERROR: {e}")
            return "DATA_ACTION" # Fail-safe: Assume it's a data question

    def _generate_python_code(self, user_query: str, history_str: str="") -> str:
    
        formatted_prompt = ANALYSIS_SYSTEM_PROMPT.format(
            schema=self.schema,
            history=history_str if history_str else "No previous conversation.",
            query=user_query
        )
        
        print("DEBUG: System Prompt for Code Generation:")
        print(formatted_prompt)

        try:
            response = self.model.generate_content(
                formatted_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0)
            )
            content = response.text
            return content.strip() if content else ""
        except Exception as e:
            print(f"DEBUG: API Call Failed: {e}")
            return f"result = 'API Error: {str(e)}'"
        
    def _sanitize_code(self, code_string: str) -> str:
        """Extract and validate Python code, checking for security violations"""
        # Remove markdown code blocks if present
        match = re.search(r"```(?:python|py)?\n?(.*?)\n?```", code_string, re.DOTALL)
        clean_code = match.group(1).strip() if match else code_string.strip()

        # Security Check - banned keywords
        banned_patterns = [
            (r"\bos\b", "os module"),
            (r"\bsys\b", "sys module"),
            (r"\bsubprocess\b", "subprocess module"),
            (r"\bopen\s*\(", "file operations"),
            (r"\b__import__\s*\(", "dynamic imports"),
            (r"\bexec\s*\(", "exec function"),
            (r"\beval\s*\(", "eval function"),
            (r"\bcompile\s*\(", "compile function"),
        ]
        
        for pattern, description in banned_patterns:
            if re.search(pattern, clean_code, re.IGNORECASE):
                raise Exception(f"Security Risk: {description} is not allowed.")
        
        return clean_code

    def _execute_code(self, clean_code: str):
        """Execute sanitized Python code and return structured result"""
        local_scope = {'df': self.df, 'pd': pd, 'result': None}
        stdout_capture = io.StringIO()

        try:
            plt.clf()

            with contextlib.redirect_stdout(stdout_capture):
                exec(clean_code, {}, local_scope)
            
            result = local_scope.get('result')

            if plt.gcf().get_axes():
                ax = plt.gca()
                title = ax.get_title() or "Plot"
                x_label = ax.get_xlabel() or "X-axis"
                y_label = ax.get_ylabel() or "Y-axis"
                description = f"Chart Title: {title}; X-Axis: {x_label}; Y-Axis: {y_label}"
                
                file_name = f"plot_{uuid.uuid4()}.png"
                file_path = os.path.join("static", "plots", file_name)
                plt.savefig(file_path)
                return {
                    "type": "image",
                    "data": f"/static/plots/{file_name}",
                    "mime": "image/png",
                    "description": description
                }

            # DataFrame result
            if isinstance(result, pd.DataFrame):
                return {
                    "type": "table",
                    "data": result.head(50).fillna("").to_dict(orient="records"),
                    "columns": list(result.columns)
                }

            # Series result (convert to table format)
            elif isinstance(result, pd.Series):
                df_temp = result.to_frame().T
                
                return {
                    "type": "table",
                    "data": df_temp.fillna("").to_dict(orient="records"),
                    "columns": list(df_temp.columns)
                }
            # Direct result (string, number, etc.)
            elif result is not None:
                return {
                    "type": "text",
                    "data": str(result)
                }

            # No result but stdout captured
            else:
                output = stdout_capture.getvalue().strip()
                return {
                    "type": "text",
                    "data": output if output else "Analysis ran, but produced no output."
                }

        except Exception as e:
            return {
                "type": "error",
                "data": f"Execution Error: {str(e)}"
            }

    def _format_response(self, user_query: str, raw_result: any) -> str:
        """Convert technical result into natural language response"""
        if isinstance(raw_result, dict) and "description" in raw_result:
            data_summary = f"User asked for a plot. The system generated this chart: {raw_result['description']}"
        else:
            data_summary = str(raw_result)
        
        formatted_prompt = ANALYSIS_FORMAT_PROMPT.format(
            query=user_query,
            result=data_summary
        )
        
        try:
            response = self.model.generate_content(
                formatted_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )
            return response.text.strip()
        except:
            return f"The result is: {raw_result}"

    def answer(self, user_query: str, history_str: str="") -> dict:
        """Main method to process user query and return formatted response"""
        intent = self._decide_intent(user_query, history_str)
        if intent == "GENERAL_CHAT":
            return {
                "text": self._format_response(user_query, "I'm here to help with your data analysis needs!"),
                "result": {"type": "text", "data": "General chat response"}
            }
        
        if intent == "OFFENSIVE":
            return {
                "text": self._format_response(user_query, "Offensive intent detected"),
                "result": {"type": "text", "data": "Offensive intent detected."}
            }
        
        raw_code = self._generate_python_code(user_query, history_str)

        try:
            clean_code = self._sanitize_code(raw_code)
        except Exception as e:
            return {
                "text": str(e),
                "result": {"type": "error", "data": str(e)}
            }
        
        # Debug output
        print("DEBUG: Generated Code:")
        print(clean_code)
        
        execution_result = self._execute_code(clean_code)
        
        # Format response based on result type
        if execution_result["type"] == "table":
            summary = f"Here is the result of your query."
        else:
            summary = self._format_response(user_query, execution_result["data"])
        
        return {
            "text": summary,
            "result": execution_result,
            "python": clean_code
        }

    # ... inside DataAgent class ...

    def _calculate_stats(self) -> str:
        """Runs a tactical scan of the dataframe to extract key metrics."""
        stats = []
        
        stats.append(f"Total Records: {len(self.df)}")
        stats.append(f"Total Columns: {len(self.df.columns)}")
        
        for col in self.df.select_dtypes(include=['datetime', 'datetimetz']).columns:
            start = self.df[col].min()
            end = self.df[col].max()
            stats.append(f"Timeframe ({col}): {start} to {end}")

        # Categorical COls
        for col in self.df.select_dtypes(include=['object', 'category']).columns[:5]:
            try:
                if self.df[col].nunique() < 50: 
                    top_3 = self.df[col].value_counts().head(3).index.tolist()
                    stats.append(f"Top Entities in '{col}': {', '.join(map(str, top_3))}")
            except:
                pass

        # Numerical Col
        for col in self.df.select_dtypes(include=['number']).columns[:3]: 
            avg = self.df[col].mean()
            mx = self.df[col].max()
            stats.append(f"Metric '{col}': Max={mx:,.2f}, Avg={avg:,.2f}")

        return "\n".join(stats)

    def generate_dossier(self) -> dict:
        stats_summary = self._calculate_stats()
        
        preview = self.df.head(5).to_string()

        enhanced_prompt = DOSSIER_PROMPT.format(
            schema=self.schema,
            preview=preview,
            stats=stats_summary
        )

        try:
            response = self.model.generate_content(
                enhanced_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4, # Lower temp for more factual adherence
                ),
            )
            print("DEBUG: Dossier Response:")
            # print(response.text.strip())
            
            parsed_json = json_repair.loads(response.text.strip())
            
            if isinstance(parsed_json, dict):
                return parsed_json
            else:
                print(f"WARNING: Dossier was not a dict: {type(parsed_json)}")
                raise ValueError("Output was not a dictionary")
        except Exception as e:
            print(f"Error generating dossier: {e}")
            return {
                "file_type": "Unknown Dataset",
                "briefing": "I couldn't analyze the file automatically, but I'm ready for your questions.",
                "key_entities": list(self.df.columns[:3]),
                "recommended_actions": ["Show me the first 5 rows", "Count the rows"]
            }
