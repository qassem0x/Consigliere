import pandas as pd
import re
import os
import dotenv
import io
import contextlib
import google.generativeai as genai

dotenv.load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL_NAME = 'models/gemma-3n-e2b-it'
# MODEL_NAME = 'models/gemini-2.5-flash'  # Stronger Model

class DataAgent:
    def __init__(self, file_path: str):
        self.df = pd.read_parquet(file_path)
        self.schema = "\n".join([f"- {col}: {dtype}" for col, dtype in self.df.dtypes.items()])
        self.model = genai.GenerativeModel(MODEL_NAME)

    def _generate_python_code(self, user_query: str, history_str: str="") -> str:
        sys_prompt = (
            "You are a python coding assistant specialized in pandas.\n"
            "Generate a direct python code snippet.No data manipulation (don't change in data). No functions. No markdown. No explanations. No imports or system level operations.\n"
            "The dataframe is 'df'. Assign the final answer to the variable 'result'.\n"
            f"Schema:\n{self.schema}\n"
            f"History:\n{history_str}\n"
            f"User Query: {user_query}"
        )

        # DEBUG
        print("DEBUG: System Prompt for Code Generation:")
        print(sys_prompt)

        try:
            # Native Google call
            response = self.model.generate_content(
                sys_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0)
            )
            content = response.text
            return content.strip() if content else ""
        except Exception as e:
            # DEBUG
            print(f"DEBUG: API Call Failed: {e}")
            return f"result = 'API Error: {str(e)}'"
        
    def _sanitize_code(self, code_string: str) -> str:
        match = re.search(r"```(?:python|py)?\n?(.*?)\n?```", code_string, re.DOTALL)
        clean_code = match.group(1).strip() if match else code_string.strip()

        # Security Check
        banned = [r"\bos\b", r"\bsys\b", r"\bopen\(", r"\bimport\b", r"\bexec\b", r"\beval\b"]
        for pattern in banned:
            if re.search(pattern, clean_code):
                raise Exception(f"Security Risk: Banned keyword detected.")
        return clean_code

    def _execute_code(self, clean_code: str):
        # TODO: Hanlde Case when Result is a Plot (Future proofing, for now text)
        
        local_scope = {'df': self.df, 'pd': pd, 'result': None}
        stdout_capture = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_capture):
                exec(clean_code, {}, local_scope)
            
            result = local_scope.get('result')
            
            if isinstance(result, pd.DataFrame):
                return {
                    "type": "table",
                    "data": result.head(50).fillna("").to_dict(orient="records"), # fillna handles NaN for JSON
                    "columns": list(result.columns) # Frontend needs column names
                }

            elif isinstance(result, pd.Series):
                df_temp = result.reset_index() 
                df_temp.columns = ["Category", "Value"]
                return {
                    "type": "table",
                    "data": df_temp.head(50).fillna("").to_dict(orient="records"),
                    "columns": ["Category", "Value"]
                }

            elif result is not None:
                return {
                    "type": "text",
                    "data": str(result)
                }

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
        fmt_prompt = (
            "You are a helpful data analyst. "
            f"The user asked: '{user_query}'. "
            f"The analysis found: {raw_result}. "
            "Write a very short, natural response answering the user and make it clean and no technical details."
            "write the response in the style of consigliere, but keep it professional and concise."
        )
        try:
            response = self.model.generate_content(
                fmt_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )
            return response.text.strip()
        except:
            return f"The result is: {raw_result}"

    def answer(self, user_query: str, history_str: str="") -> dict:
        raw_code = self._generate_python_code(user_query, history_str)
        clean_code = self._sanitize_code(raw_code)
        execution_result = self._execute_code(clean_code)
        if execution_result["type"] == "table":
            summary = f"Returned a table with {len(execution_result['data'])} rows and columns: {', '.join(execution_result['columns'])}."
        else:
            summary = self._format_response(user_query, execution_result["data"])
        
        return {
            "text": summary,
            "result": execution_result
        }