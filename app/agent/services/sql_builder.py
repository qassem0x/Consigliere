import logging

from app.agent.llm.client import LLMClient
from app.agent.prompts import (
    FILE_EMPTY_RESULT_PROMPT,
    FILE_SQL_FIX_PROMPT,
    FILE_SQL_GENERATOR_PROMPT,
    STRICT_SQL_RULES,
)
from app.agent.utils import clean_sql_response

logger = logging.getLogger(__name__)


class SQLBuilder:
    def __init__(self, llm_client: LLMClient, schema: str):
        self.llm = llm_client
        self.schema = schema

    def generate(self, query: str) -> str:
        content = (
            FILE_SQL_GENERATOR_PROMPT.format(schema=self.schema, query=query)
            + "\n"
            + STRICT_SQL_RULES
        )
        response = self.llm.complete([{"role": "system", "content": content}], temperature=0.0)
        return clean_sql_response(response)

    def fix(self, sql: str, error: str) -> str:
        content = FILE_SQL_FIX_PROMPT.format(error=error, query=sql, schema=self.schema)
        response = self.llm.complete([{"role": "system", "content": content}], temperature=0.2)
        return clean_sql_response(response)

    def widen(self, sql: str, request: str) -> str:
        content = FILE_EMPTY_RESULT_PROMPT.format(query=sql, user_request=request, schema=self.schema)
        response = self.llm.complete([{"role": "system", "content": content}], temperature=0.3)
        return clean_sql_response(response)