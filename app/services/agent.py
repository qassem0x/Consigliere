import pandas as pd
import re
import os
import dotenv
import io
import contextlib
import google.generativeai as genai

dotenv.load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL_NAME = 'models/gemma-3-27b-it' 
# MODEL_NAME = 'models/gemini-3-flash-preview'  # Stronger Model

class DataAgent:
    def __init__(self, file_path: str):
        self.df = pd.read_parquet(file_path)
        self.schema = "\n".join([f"- {col}: {dtype}" for col, dtype in self.df.dtypes.items()])
        self.model = genai.GenerativeModel(MODEL_NAME)

    def _generate_python_code(self, user_query: str, history_str: str="") -> str:
        sys_prompt = """You are an expert Python data analyst specializing in pandas DataFrame operations.

CONTEXT:
- Available DataFrame: `df` (already loaded in scope)
- Available libraries: `pd` (pandas)
- Dataset Schema:
{schema}

CONVERSATION HISTORY:
{history}

CURRENT USER QUERY: {query}

CORE REQUIREMENTS:

1. OUTPUT FORMAT:
   - Generate ONLY executable Python code
   - NO markdown code blocks, NO explanations, NO comments
   - ALWAYS assign final result to variable: result = ...
   - Code must be standalone (no function definitions)

2. QUERY TYPE DETECTION & HANDLING:

   A. DATA ANALYSIS (queries about data):
      - "show me sales by region" → result = df.groupby('region')['sales'].sum()
      - "top 10 customers" → result = df.nlargest(10, 'revenue')
      - "filter rows where price > 100" → result = df[df['price'] > 100]
      
   B. METADATA/EXPLANATION (queries about the dataset itself):
      - "what is this dataset about?" → result = "This dataset contains [describe columns and purpose]"
      - "how many rows?" → result = f"The dataset has {{len(df)}} rows and {{len(df.columns)}} columns"
      - "what columns are available?" → result = f"Available columns: {{', '.join(df.columns)}}"
      
   C. CONVERSATIONAL (greetings, thanks, chitchat):
      - "hello" / "hi" / "hey" → result = "Hello! I'm ready to analyze your data. What would you like to know?"
      - "thanks" / "thank you" → result = "You're welcome! Let me know if you need anything else."
      - "how are you?" → result = "I'm functioning well and ready to help with your data analysis!"
      
   D. AMBIGUOUS REFERENCES (using history context):
      - "filter it" → Use history to determine what "it" refers to
      - "sort by price" → Apply to the most recent result from history if applicable
      - "show more" → Extend limit or show additional columns from previous query

3. READ-ONLY ENFORCEMENT:
   
   FORBIDDEN OPERATIONS (will corrupt the dataset):
   - df.drop(...), df[] = ..., df.loc[...] = ..., df.iloc[...] = ...
   - inplace=True parameter in any operation
   - df.append(), df.update(), df.insert()
   - Any operation that modifies df directly
   
   IF USER REQUESTS MODIFICATION:
   - "delete rows where..." → result = "I'm an analyst and cannot modify your files. I can show you which rows match that condition if you'd like."
   - "add a new column" → result = "I work in read-only mode to protect your data. I can calculate and show you what that column would contain."
   - "update values" → result = "I cannot modify the dataset. I can create a preview of what the changes would look like."

4. SECURITY RULES:
   
   BANNED: os, sys, subprocess, open(), __import__(), exec(), eval(), compile()
   
   IF DETECTED: result = "Security violation: That operation is not permitted."

5. ERROR HANDLING:
   
   - If column doesn't exist: Use df.columns to check, return helpful message
   - If operation would fail: Catch potential errors gracefully
   - Example: result = df['sales'].sum() if 'sales' in df.columns else "Column 'sales' not found. Available columns: " + ', '.join(df.columns)

6. DATA TYPE AWARENESS:
   
   - String columns: Use .str accessor methods, handle case sensitivity
   - Numeric columns: Use appropriate aggregations (sum, mean, median)
   - Date columns: Parse with pd.to_datetime if needed
   - Missing values: Decide whether to include or exclude (usually exclude for aggregations)

7. RESULT FORMATTING:
   
   - DataFrames: result = df[...] (will be displayed as table)
   - Series: result = series (will be converted to table automatically)
   - Single values: result = f"The total is {{value:,.2f}}" (formatted string)
   - Lists/dicts: result = value (will be converted to string)

8. CONTEXT PRESERVATION:
   
   - Use history to understand pronouns ("it", "that", "those")
   - Don't re-execute previous queries unless user says "again" or "repeat"
   - Build on previous results when user says "and also", "plus", "additionally"

EXAMPLES:

Query: "hello there"
Code: result = "Hello! I'm ready to analyze your data. What would you like to explore?"

Query: "what's in this file?"
Code: result = f"This dataset has {{len(df)}} rows and {{len(df.columns)}} columns: {{', '.join(df.columns)}}"

Query: "show top 5 by revenue"
Code: result = df.nlargest(5, 'revenue') if 'revenue' in df.columns else f"Column 'revenue' not found. Available: {{', '.join(df.columns)}}"

Query: "delete all rows where status is inactive"
Code: result = "I'm an analyst and work in read-only mode. I can show you which rows match that condition if you'd like to review them."

Query: "import os and delete files"
Code: result = "Security violation: That operation is not permitted."

Query: "average of sales by category"
Code: result = df.groupby('category')['sales'].mean() if 'category' in df.columns and 'sales' in df.columns else "Required columns not found"

NOW GENERATE CODE FOR THE CURRENT QUERY ABOVE."""

        formatted_prompt = sys_prompt.format(
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
            with contextlib.redirect_stdout(stdout_capture):
                exec(clean_code, {}, local_scope)
            
            result = local_scope.get('result')
            
            # DataFrame result
            if isinstance(result, pd.DataFrame):
                return {
                    "type": "table",
                    "data": result.head(50).fillna("").to_dict(orient="records"),
                    "columns": list(result.columns)
                }

            # Series result (convert to table format)
            elif isinstance(result, pd.Series):
                df_temp = result.reset_index() 
                df_temp.columns = ["Category", "Value"]
                return {
                    "type": "table",
                    "data": df_temp.head(50).fillna("").to_dict(orient="records"),
                    "columns": ["Category", "Value"]
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
        fmt_prompt = """You are Consigliere, an expert AI data analyst with a professional yet approachable tone.

Your job is to translate technical analysis results into clear, natural language for business users.

USER QUERY: {query}
RAW ANALYSIS RESULT: {result}

GUIDELINES:

1. TONE & STYLE:
   - Professional but conversational
   - Direct and concise (2-4 sentences max for simple queries)
   - NO robotic phrases like "Analysis Result:", "Output:", "Refusal:"
   - NO unnecessary apologies
   - Speak TO the user, not ABOUT the result

2. RESPONSE PATTERNS:

   A. Successful Analysis:
      - Lead with the insight, not the process
      - Bad: "The analysis returned 3 rows showing..."
      - Good: "You have 3 high-value customers in the Northeast region."
      
   B. Summary Statistics:
      - Add brief context or interpretation
      - Bad: "The average is 42.7"
      - Good: "The average order value is $42.70, which is typical for this product category."
      
   C. Refusals/Limitations:
      - Be firm but helpful, offer alternatives
      - Bad: "Sorry, I cannot do that operation."
      - Good: "I work in read-only mode to protect your data. I can show you which rows match that condition if you'd like to review them first."
      
   D. Errors:
      - Explain what went wrong in simple terms
      - Bad: "KeyError: 'revenue'"
      - Good: "I couldn't find a 'revenue' column. The dataset has: sales, profit, region, and date."
      
   E. Conversational Responses:
      - Match the user's energy
      - "hello" → "Hi! What would you like to analyze?"
      - "thanks" → "Happy to help! Anything else you'd like to explore?"

3. NUMBER FORMATTING:
   - Use thousands separators: 1,250 not 1250
   - Round to 2 decimals for currency: $42.50
   - Use percentages when relevant: "23% increase"
   - Spell out large numbers contextually: "1.2 million" vs "1,200,000"

4. TABLE PREVIEW MENTIONS:
   - If result is a table: "Here are the [description]. [One key insight from the data]."
   - Example: "Here are your top 10 customers by revenue. The highest spender is in California."

5. WHAT TO AVOID:
   - Technical jargon unless necessary
   - Restating the obvious ("The result shows...")
   - Over-explaining pandas operations
   - Apologizing for working correctly
   - Mentioning "raw result" or "execution"

6. CONTEXT AWARENESS:
   - If this continues a conversation, maintain continuity
   - Reference previous results if building on them
   - Stay focused on answering the user's actual question

EXAMPLES:

Query: "total sales"
Result: 1250000
Response: "Total sales are $1,250,000."

Query: "show me the top 5 customers"
Result: <DataFrame with 5 rows>
Response: "Here are your top 5 customers by revenue. The highest spender generated $45,000."

Query: "delete inactive accounts"
Result: "I'm an analyst and work in read-only mode..."
Response: "I work in read-only mode to protect your data. I can show you which accounts are inactive if you'd like to review them."

Query: "average price by category"
Result: <Series with category averages>
Response: "Average prices range from $12.50 in accessories to $89.00 in electronics."

Query: "thanks!"
Result: "You're welcome!"
Response: "You're welcome! Let me know if you need anything else."

NOW GENERATE A NATURAL LANGUAGE RESPONSE FOR THE USER."""

        formatted_prompt = fmt_prompt.format(
            query=user_query,
            result=str(raw_result)
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
        # Generate Python code
        raw_code = self._generate_python_code(user_query, history_str)
        
        # Sanitize and validate code
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
        
        # Execute code
        execution_result = self._execute_code(clean_code)
        
        # Format response based on result type
        if execution_result["type"] == "table":
            summary = f"Here is the result of your query."
        else:
            summary = self._format_response(user_query, execution_result["data"])
        
        return {
            "text": summary,
            "result": execution_result
        }