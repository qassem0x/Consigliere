import json
import json_repair
import pandas as pd
import re
from sqlalchemy import create_engine, inspect, text
from typing import List, Dict, Any

from app.services.base_agent import BaseAgent
from app.services.llm import call_llm
from app.core.prompts import (
    SQL_GENERATOR_PROMPT,
    DOSSIER_PROMPT,
    ANALYSIS_FORMAT_PROMPT,
)

STRICT_SQL_RULES = """
CRITICAL SYNTAX RULES:
1. If using UNION or UNION ALL with LIMIT/ORDER BY, you MUST wrap each subquery in parentheses:
   CORRECT: (SELECT * FROM a LIMIT 5) UNION ALL (SELECT * FROM b LIMIT 5)
   INCORRECT: SELECT * FROM a LIMIT 5 UNION ALL SELECT * FROM b LIMIT 5
2. Prefer using Common Table Expressions (WITH clause) over complex nested subqueries.
3. Ensure all table and column names match the schema exactly.
"""

SQL_FIX_PROMPT = """
You are a PostgreSQL expert. A previous SQL query failed to execute.
Your task is to FIX the query based on the database error message.

Target Database: {target_db}

Error Message:
{error}

Failed Query:
{query}

Database Schema:
{schema}

Instructions:
1. Analyze the syntax error carefully.
2. If the error is about "UNION", you likely forgot parentheses around subqueries with LIMIT/ORDER BY.
3. Rewrite the query to be syntactically correct for PostgreSQL.
4. DO NOT output the same query again.
5. Return ONLY the raw SQL query. No Markdown, no explanations.
"""


class SQLAgent(BaseAgent):
    def __init__(self, connection_string: str):
        super().__init__()
        self.engine = create_engine(connection_string)
        self.target_db = connection_string.split(":")[0]
        self.schema = self._get_schema_string()
        self.max_retries = 3

    def _get_schema_string(self) -> str:
        try:
            inspector = inspect(self.engine)
            schema_lines = []
            for table in inspector.get_table_names():
                columns = inspector.get_columns(table)
                col_str = ", ".join(
                    [f"{col['name']} ({str(col['type'])})" for col in columns]
                )
                schema_lines.append(f"Table {table} ({col_str})")
            return "\n".join(schema_lines)
        except Exception as e:
            return f"Error reading schema: {str(e)}"

    def _generate_sql(self, user_query: str) -> str:
        system_content = (
            SQL_GENERATOR_PROMPT.format(
                schema=self.schema, query=user_query, target_db=self.target_db
            )
            + "\n"
            + STRICT_SQL_RULES
        )
        messages = [{"role": "system", "content": system_content}]
        response = call_llm(messages, temperature=0.0)
        return self._clean_sql(response)

    def _fix_sql(self, bad_query: str, error_msg: str) -> str:
        messages = [
            {
                "role": "system",
                "content": SQL_FIX_PROMPT.format(
                    target_db=self.target_db,
                    error=error_msg,
                    query=bad_query,
                    schema=self.schema,
                ),
            }
        ]
        response = call_llm(messages, temperature=0.2)
        return self._clean_sql(response)

    def _clean_sql(self, response: str) -> str:
        cleaned = response.replace("```sql", "").replace("```", "").strip()
        if not cleaned.lower().startswith("select") and not cleaned.lower().startswith(
            "with"
        ):
            match = re.search(r"(SELECT|WITH)\s", cleaned, re.IGNORECASE)
            if match:
                cleaned = cleaned[match.start() :]
        return cleaned

    def _sanitize_sql(self, sql_query: str) -> bool:
        lowered = sql_query.lower()
        if "error:" in lowered:
            return False
        banned = [
            r"\binsert\b",
            r"\bupdate\b",
            r"\bdelete\b",
            r"\bdrop\b",
            r"\balter\b",
            r"\bgrant\b",
            r"\btruncate\b",
        ]
        for pattern in banned:
            if re.search(pattern, lowered):
                return False
        return True

    def _execute_code(self, sql_query: str) -> pd.DataFrame:
        with self.engine.connect() as conn:
            result = conn.execute(text(sql_query))
            if result.returns_rows:
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                return df
            return pd.DataFrame()

    def _format_final_response(
        self, user_query: str, all_results: List[Dict[str, Any]]
    ) -> str:
        summary_parts = []
        for i, result in enumerate(all_results, 1):
            if result["type"] == "table":
                summary_parts.append(
                    f"Step {i}: Query {all_results[i-1].get('query', 'Unknown')} returned {result.get('total_rows', 0)} rows. Columns: {', '.join(result.get('columns', []))}"
                )
            elif result["type"] == "error":
                summary_parts.append(f"Step {i}: Error - {result.get('data', '')}")

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
        intent = self._decide_intent(user_query, history_str)

        if intent == "GENERAL_CHAT":
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": "I'm Consigliere, your AI database assistant. I can query your SQL database to find insights. What would you like to know?",
                        "steps": [],
                        "code": None,
                        "plan": None,
                    },
                }
            )
            return

        if intent == "OFFENSIVE":
            yield json.dumps(
                {
                    "type": "final_result",
                    "data": {
                        "text": "I'm here to help with data analysis. Please keep our conversation professional.",
                        "steps": [],
                        "code": None,
                        "plan": None,
                    },
                }
            )
            return

        plan = {
            "plan": [
                {
                    "step_number": 1,
                    "type": "code",
                    "description": f"Execute SQL query on {self.target_db} database",
                    "depends_on": [],
                }
            ]
        }

        yield json.dumps(
            {
                "type": "step_start",
                "step_number": 0,
                "description": "Planning analysis steps...",
            }
        )

        all_results = []
        final_sql_used = ""

        step = plan["plan"][0]

        yield json.dumps(
            {
                "type": "step_start",
                "step_number": step["step_number"],
                "description": step["description"],
                "step_type": step["type"],
            }
        )

        sql_query = self._generate_sql(user_query)
        df = None
        last_error = None

        for attempt in range(self.max_retries):
            if not self._sanitize_sql(sql_query):
                yield json.dumps(
                    {
                        "type": "step_result",
                        "data": {
                            "step_number": step["step_number"],
                            "type": "error",
                            "data": "Security Alert: Prohibited SQL commands detected.",
                        },
                    }
                )
                return

            try:
                df = self._execute_code(sql_query)
                final_sql_used = sql_query
                break
            except Exception as e:
                last_error = str(e)
                print(
                    f"DEBUG: SQL Execution failed (Attempt {attempt+1}): {last_error}"
                )

                if attempt < self.max_retries - 1:
                    pass

                sql_query = self._fix_sql(sql_query, last_error)

        exec_result = {}

        if df is not None:
            # Convert to dict format compatible with frontend
            data_dict = df.head(50).fillna("").astype(str).to_dict(orient="records")

            exec_result = {
                "step_number": step["step_number"],
                "step_description": step["description"],
                "step_type": "table",  # Force type table for SQL results
                "type": "table",
                "data": data_dict,
                "columns": list(df.columns),
                "total_rows": len(df),
                "description": f"Retrieved {len(df)} records",
            }
        else:
            # Failed after retries
            exec_result = {
                "step_number": step["step_number"],
                "step_description": step["description"],
                "step_type": "error",
                "type": "error",
                "data": f"Failed to execute query after {self.max_retries} attempts. Error: {last_error}",
            }

        all_results.append(exec_result)

        yield json.dumps({"type": "step_result", "data": exec_result})

        summary_text = self._format_final_response(user_query, all_results)

        formatted_code = f"-- Step 1: Execute Query\n{final_sql_used if final_sql_used else sql_query}"

        yield json.dumps(
            {
                "type": "final_result",
                "data": {
                    "text": summary_text,
                    "steps": all_results,
                    "plan": plan,
                    "code": formatted_code,
                },
            }
        )

    def _generate_stats(self) -> str:
        return "No stats available yet."

    def _generate_preview(self) -> str:
        return "No Preview Available"

    def generate_dossier(self):
        print("DEBUG: Schema: ", self.schema)
        try:
            messages = [
                {
                    "role": "system",
                    "content": DOSSIER_PROMPT.format(
                        schema=self.schema,
                        stats=self._generate_stats(),
                        preview=self._generate_preview(),
                        source_type="SQL database",
                    ),
                }
            ]
            response = call_llm(messages, temperature=0.0)
            clean_response = response.replace("```json", "").replace("```", "").strip()
            return json_repair.loads(clean_response)
        except Exception as e:
            print(f"Dossier generation error: {str(e)}")
            raise Exception(f"Dossier generation failed: {str(e)}")
