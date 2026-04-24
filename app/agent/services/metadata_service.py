import json
import logging

import pandas as pd

from app.agent.domain import ExecutionResult, Step
from app.models.db_models import ChatSettings

logger = logging.getLogger(__name__)


class MetadataService:
    def __init__(self, schema: str, settings: ChatSettings):
        self.schema = schema
        self.settings = settings

    def execute(self, step: Step, user_query: str) -> ExecutionResult:
        user_query_lower = user_query.lower()
        try:
            schema_json = json.loads(self.schema)
        except Exception:
            schema_json = {"tables": []}

        tables = schema_json.get("tables", [])
        wants_structure = any(kw in user_query_lower for kw in ("column", "structure", "schema", "field"))
        all_results = []

        for table in tables:
            table_name = table.get("name", "data")
            columns = table.get("columns", [])

            if wants_structure:
                rows = [
                    {"Column": col.get("name", ""), "Type": col.get("type", "unknown"), "Role": col.get("role", "unknown")}
                    for col in columns
                ]
            else:
                rows = [
                    {
                        "Column": col.get("name", ""),
                        "Type": col.get("type", "unknown"),
                        "Null %": f"{col.get('profile', {}).get('null_ratio', 0) * 100:.1f}%",
                        "Distinct": col.get("profile", {}).get("distinct_count", "N/A"),
                    }
                    for col in columns
                ]

            if rows:
                df = pd.DataFrame(rows)
                all_results.append({
                    "type": "table",
                    "table_name": table_name,
                    "data": df.fillna("").to_dict(orient="records"),
                    "columns": list(df.columns),
                    "total_rows": len(df),
                })

        if all_results:
            return ExecutionResult(
                type="metadata",
                data={"tables": all_results},
                description="Data schema",
            )
        return ExecutionResult(type="text", data=self.schema, description="Data schema")