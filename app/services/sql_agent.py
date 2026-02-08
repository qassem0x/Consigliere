from sqlalchemy import create_engine, inspect
from litellm import completion
import json


class SQLAgent:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.conn = self.engine.connect()
        self.schema = self._get_schema()

    def __del__(self):
        self.conn.close()

    def _get_schema(self):
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        schema = {}
        for table in tables:
            columns = inspector.get_columns(table)
            schema[table] = [f"{col['name']} ({col['type']})" for col in columns]
        return json.dumps(schema, indent=2)

    def _generate_sql_query(self, user_query: str) -> str:
        return "SQL Query"
