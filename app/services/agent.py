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

    def _generate_python_code(self, user_query: str) -> str:
        sys_prompt = (
            "You are a python coding assistant specialized in pandas.\n"
            "Generate a direct python code snippet.No data manipulation (don't change in data). No functions. No markdown. No explanations. No imports or system level operations.\n"
            "The dataframe is 'df'. Assign the final answer to the variable 'result'.\n"
            f"Schema:\n{self.schema}\n"
            f"User Query: {user_query}"
        )

        try:
            # Native Google call
            response = self.model.generate_content(
                sys_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0)
            )
            content = response.text
            return content.strip() if content else ""
        except Exception as e:
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
        local_scope = {'df': self.df, 'pd': pd, 'result': None}

        stdout_capture = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_capture):
                exec(clean_code, {}, local_scope)
            result = local_scope.get('result')
            if result is not None:
                return result
            else:
                return stdout_capture.getvalue().strip() or "No result produced."
        except Exception as e:
            return f"Execution Error: {str(e)}"

    def _format_response(self, user_query: str, raw_result: any) -> str:
        fmt_prompt = (
            "You are a helpful data analyst. "
            f"The user asked: '{user_query}'. "
            f"The analysis found: {raw_result}. "
            "Write a very short, natural response answering the user and make it clean and no technical details."
        )
        try:
            response = self.model.generate_content(
                fmt_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )
            return response.text.strip()
        except:
            return f"The result is: {raw_result}"

    def answer(self, user_query: str) -> str:
        raw_code = self._generate_python_code(user_query)
        print("Generated Code:", raw_code)
        clean_code = self._sanitize_code(raw_code)
        execution_result = self._execute_code(clean_code)
        
        return self._format_response(user_query, execution_result)