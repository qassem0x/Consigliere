import json
import pandas as pd
import numpy as np
from datetime import datetime, date


class ExcelInferenceEngine:
    def __init__(self, df: pd.DataFrame):
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Expected a pandas DataFrame")
        self.df = df

    def infer(self):
        schema_model = {
            "sheets": [],
            "relationships": [],
        }

        sheet_model = self._analyze_sheet(self.df)
        schema_model["sheets"].append(sheet_model)

        return json.dumps(schema_model, indent=2)

    def _analyze_sheet(self, df: pd.DataFrame):
        row_count = len(df)
        column_models = []

        for col in df.columns:
            profile = self._profile_column(df, col, row_count)
            role = self._infer_column_role(df[col], profile)

            column_models.append(
                {
                    "name": col,
                    "type": str(df[col].dtype),
                    "profile": profile,
                    "role": role,
                }
            )

        sheet_role = self._infer_sheet_role(column_models, df)

        return {
            "name": "Sheet1",
            "row_count": row_count,
            "columns": column_models,
            "role": sheet_role,
        }

    def _profile_column(self, df: pd.DataFrame, column_name: str, row_count: int):
        col = df[column_name]

        non_null_count = col.notna().sum()
        null_count = row_count - non_null_count
        distinct_count = col.nunique()

        distinct_ratio = distinct_count / row_count if row_count > 0 else 0
        null_ratio = null_count / row_count if row_count > 0 else 0

        profile = {
            "distinct_count": int(distinct_count),
            "distinct_ratio": round(distinct_ratio, 4),
            "null_ratio": round(null_ratio, 4),
        }

        if pd.api.types.is_numeric_dtype(col):
            profile["min"] = float(col.min()) if pd.notna(col.min()) else None
            profile["max"] = float(col.max()) if pd.notna(col.max()) else None
            profile["mean"] = float(col.mean()) if pd.notna(col.mean()) else None
            profile["std"] = float(col.std()) if pd.notna(col.std()) else None

        if pd.api.types.is_datetime64_any_dtype(col):
            profile["min"] = str(col.min()) if pd.notna(col.min()) else None
            profile["max"] = str(col.max()) if pd.notna(col.max()) else None

        return profile

    def _infer_column_role(self, column: pd.Series, profile: dict):
        col_name = column.name
        col_type = column.dtype
        distinct_ratio = profile.get("distinct_ratio", 0)
        null_ratio = profile.get("null_ratio", 0)

        if pd.api.types.is_datetime64_any_dtype(column):
            return "time_dimension"

        if pd.api.types.is_bool_dtype(column):
            return "boolean"

        if pd.api.types.is_numeric_dtype(column):
            if distinct_ratio > 0.95 and null_ratio == 0:
                return "identifier"

            if distinct_ratio > 0.3:
                return "measure"

            return "dimension_numeric"

        if pd.api.types.is_categorical_dtype(column):
            return "dimension_categorical"

        if pd.api.types.is_object_dtype(column):
            if distinct_ratio < 0.2:
                return "dimension_categorical"
            if distinct_ratio > 0.9 and null_ratio == 0:
                return "identifier"
            return "text_content"

        return "unknown"

    def _infer_sheet_role(self, column_models: list, df: pd.DataFrame):
        measure_count = sum(1 for col in column_models if col["role"] == "measure")
        dimension_count = sum(
            1
            for col in column_models
            if col["role"] in ("dimension_categorical", "dimension_numeric", "text_content")
        )
        identifier_count = sum(1 for col in column_models if col["role"] == "identifier")

        if measure_count > 0 and dimension_count > 0:
            return "data_table"

        if dimension_count > 0 and measure_count == 0:
            return "lookup_table"

        if identifier_count > 0 and dimension_count > 0 and measure_count > 0:
            return "fact_table"

        return "entity_table"
