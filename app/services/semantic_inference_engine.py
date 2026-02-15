import json
from sqlalchemy import inspect, text
from sqlalchemy.sql.elements import quoted_name
from sqlalchemy.types import (
    Integer,
    Numeric,
    Float,
    Boolean,
    Date,
    DateTime,
    Text,
    String,
    JSON,
    BigInteger,
    SmallInteger,
    TIMESTAMP,
    Time,
)


class SemanticInferenceEngine:
    def __init__(self, engine, schema=None):
        self.engine = engine
        self.inspector = inspect(self.engine)

        if schema:
            self.schema = schema
        else:
            # MYSQL
            if self.inspector.get_table_names():
                self.schema = None

            # PostgreSQL
            elif (
                "public" in self.inspector.get_schema_names()
                and self.inspector.get_table_names(schema="public")
            ):
                self.schema = "public"

            # SQL Server
            elif (
                "dbo" in self.inspector.get_schema_names()
                and self.inspector.get_table_names(schema="dbo")
            ):
                self.schema = "dbo"

            else:
                self.schema = None

    def infer(self):
        schema_model = {"tables": [], "relationships": []}

        table_names = self.inspector.get_table_names(schema=self.schema)
        self.row_counts = {table: self._get_row_count(table) for table in table_names}

        for table in table_names:
            table_model = self._analyze_table(table)
            schema_model["tables"].append(table_model)

        schema_model["relationships"] = self._infer_relationships()

        return json.dumps(schema_model, indent=2)

    def _get_safe_table_path(self, table_name):
        """Handles schema.table formatting and quoting."""
        q_table = quoted_name(table_name, quote=True)
        if self.schema:
            q_schema = quoted_name(self.schema, quote=True)
            return f"{q_schema}.{q_table}"
        return f"{q_table}"

    def _analyze_table(self, table_name):
        cols = self.inspector.get_columns(table_name, schema=self.schema)
        pks = self.inspector.get_pk_constraint(table_name, schema=self.schema)
        fks = self.inspector.get_foreign_keys(table_name, schema=self.schema)

        row_count = self.row_counts.get(table_name, 0)
        column_models = []

        for col in cols:
            profile = self._profile_column(table_name, col["name"], row_count)
            role = self._infer_column_role(col, profile, pks, fks)

            column_models.append(
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "profile": profile,
                    "role": role,
                }
            )

        table_role = self._infer_table_role(column_models, fks)

        return {
            "name": table_name,
            "schema": self.schema,
            "row_count": row_count,
            "primary_keys": pks.get("constrained_columns", []),
            "foreign_keys": [
                {
                    "column": fk.get("constrained_columns", []),
                    "references": f"{fk['referred_table']}({fk['referred_columns']})",
                }
                for fk in fks
            ],
            "role": table_role,
            "columns": column_models,
        }

    def _profile_column(self, table_name, column_name, row_count):
        safe_path = self._get_safe_table_path(table_name)
        safe_column = quoted_name(column_name, quote=True)

        query = text(
            f"""
            SELECT 
                COUNT({safe_column}) AS non_null_count,
                COUNT(DISTINCT {safe_column}) AS distinct_count
            FROM {safe_path}
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(query).fetchone()

        non_null_count = result[0] if result else 0
        distinct_count = result[1] if result else 0

        null_count = row_count - non_null_count
        distinct_ratio = distinct_count / row_count if row_count > 0 else 0
        null_ratio = null_count / row_count if row_count > 0 else 0

        return {
            "distinct_count": distinct_count,
            "distinct_ratio": round(distinct_ratio, 4),
            "null_ratio": round(null_ratio, 4),
        }

    def _infer_column_role(self, column, profile, pks, fks):
        col_name = column["name"]
        col_type = column["type"]

        if col_name in pks.get("constrained_columns", []):
            return "primary_key"

        for fk in fks:
            if col_name in fk.get("constrained_columns", []):
                return "foreign_key"

        if isinstance(col_type, (Date, DateTime, TIMESTAMP, Time)):
            return "time_dimension"

        if isinstance(col_type, Boolean):
            return "boolean"

        if isinstance(col_type, (Integer, BigInteger, SmallInteger, Numeric, Float)):
            if (
                isinstance(col_type, (Integer, BigInteger))
                and profile["distinct_ratio"] > 0.95
            ):
                return "identifier"

            if (
                isinstance(col_type, (Numeric, Float))
                or profile["distinct_ratio"] > 0.3
            ):
                return "measure"

            return "dimension_numeric"

        if isinstance(col_type, JSON):
            return "dimension_json"

        if isinstance(col_type, (String, Text)):
            if profile["distinct_ratio"] < 0.2:
                return "dimension_categorical"
            return "text_content"

        return "unknown"

    def _infer_table_role(self, column_models, fks):
        measure_count = sum(1 for col in column_models if col["role"] == "measure")
        fk_count = len(fks)

        if measure_count > 0 and fk_count > 0:
            return "fact_table"

        if fk_count == 0 and measure_count == 0:
            return "dimension_table"

        if fk_count > 0 and measure_count == 0:
            return "bridge_table"

        return "entity_table"

    def _infer_relationships(self):
        relationships = []
        table_names = self.inspector.get_table_names(schema=self.schema)

        for table in table_names:
            fks = self.inspector.get_foreign_keys(table, schema=self.schema)
            for fk in fks:
                relationships.append(
                    {
                        "from_table": table,
                        "from_column": fk.get("constrained_columns", []),
                        "to_table": fk["referred_table"],
                        "to_column": fk.get("referred_columns", []),
                    }
                )

        return relationships

    def _get_row_count(self, table_name):
        safe_path = self._get_safe_table_path(table_name)
        with self.engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT COUNT(*) AS count FROM {safe_path}")
            ).fetchone()
        return result[0] if result else 0


if __name__ == "__main__":
    from sqlalchemy import create_engine

    pass
