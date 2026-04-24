import json
import logging
from typing import Any, Dict

import duckdb

logger = logging.getLogger(__name__)


class FileInferenceEngine:
    """Schema inference engine for file-based data sources."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def infer(self) -> str:
        """Infer schema from DuckDB connection."""
        try:
            columns_info = self.conn.execute("DESCRIBE data").fetchall()

            if not columns_info:
                return json.dumps({"tables": [{"name": "data", "columns": []}]})

            column_models = []
            for col in columns_info:
                col_name, col_type = col[0], col[1]
                try:
                    stats = self.conn.execute(f"""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(DISTINCT {col_name}) as distinct_count,
                            COUNT(CASE WHEN {col_name} IS NULL THEN 1 END) as null_count
                        FROM data
                    """).fetchone()

                    null_ratio = stats[2] / stats[0] if stats[0] > 0 else 0

                    profile = {
                        "distinct_count": stats[1],
                        "null_ratio": null_ratio,
                    }

                    if "int" in col_type.lower() or "double" in col_type.lower() or "float" in col_type.lower():
                        stats_ext = self.conn.execute(f"""
                            SELECT MIN({col_name}), MAX({col_name}), AVG({col_name})
                            FROM data WHERE {col_name} IS NOT NULL
                        """).fetchone()
                        if stats_ext[0]:
                            profile["min"] = stats_ext[0]
                            profile["max"] = stats_ext[1]
                            profile["mean"] = stats_ext[2]

                except Exception as e:
                    logger.warning(f"Failed to get stats for column {col_name}: {e}")
                    profile = {}

                role = self._infer_column_role(col_type, profile.get("distinct_count", 0))

                column_models.append({
                    "name": col_name,
                    "type": col_type,
                    "profile": profile,
                    "role": role,
                })

            schema_model = {
                "tables": [{
                    "name": "data",
                    "columns": column_models,
                    "role": "data_table",
                }]
            }

            return json.dumps(schema_model, indent=2)

        except Exception as e:
            logger.error(f"Schema inference failed: {e}")
            return json.dumps({"tables": [{"name": "data", "columns": []}]})

    def _infer_column_role(self, col_type: str, distinct_count: int) -> str:
        """Infer column role based on type and cardinality."""
        col_type_lower = col_type.lower()

        if "date" in col_type_lower or "timestamp" in col_type_lower:
            return "time_dimension"

        if "int" in col_type_lower or "double" in col_type_lower or "float" in col_type_lower:
            if distinct_count > 100:
                return "measure"
            return "dimension_numeric"

        if "varchar" in col_type_lower or "text" in col_type_lower:
            if distinct_count < 20:
                return "dimension_categorical"
            return "text_content"

        return "unknown"
