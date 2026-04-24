import hashlib
import logging
import os
import time
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from app.agent.domain import ExecutionResult
from app.agent.utils import clean_sql_response, sanitize_sql

logger = logging.getLogger(__name__)


def _sanitize_records(records: list[dict]) -> list[dict]:
    """Convert non-JSON-serializable types to native Python."""
    clean = []
    for row in records:
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                clean_row[k] = float(v)
            elif isinstance(v, (np.integer, np.floating)):
                clean_row[k] = v.item()
            elif isinstance(v, np.ndarray):
                clean_row[k] = v.tolist()
            elif pd.isna(v):
                clean_row[k] = None
            else:
                clean_row[k] = v
        clean.append(clean_row)
    return clean


class BaseExecutor(ABC):
    """Shared logic for SQL and File executors: caching, sanitization, cleaning."""

    QUERY_TTL = 600
    SCHEMA_TTL = 1800

    def __init__(self, source_key: str, max_row_limit: int = 100, plots_dir: str = "static/plots"):
        self.source_key = source_key
        self.max_row_limit = max_row_limit
        self.plots_dir = plots_dir
        self._query_cache: Dict[str, Any] = {}
        self._schema_cache: Optional[Dict[str, Any]] = None
        os.makedirs(plots_dir, exist_ok=True)

    # -- caching ---------------------------------------------------------

    def _hash_query(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()

    def _cache_key(self, query: str) -> str:
        return f"{self.source_key}:{self._hash_query(query)}"

    def _get_cached_result(self, query: str) -> Optional[ExecutionResult]:
        key = self._cache_key(query)
        entry = self._query_cache.get(key)
        if not entry:
            return None
        if time.time() - entry["timestamp"] < self.QUERY_TTL:
            entry["timestamp"] = time.time()
            logger.debug("CACHE HIT: query result")
            return entry["result"]
        del self._query_cache[key]
        return None

    def _set_cached_result(self, query: str, result: ExecutionResult):
        self._query_cache[self._cache_key(query)] = {
            "result": result,
            "query": query,
            "timestamp": time.time(),
        }

    def get_schema(self) -> Optional[str]:
        if self._schema_cache and time.time() - self._schema_cache["timestamp"] < self.SCHEMA_TTL:
            self._schema_cache["timestamp"] = time.time()
            return self._schema_cache["schema"]
        return None

    def set_schema(self, schema: str):
        self._schema_cache = {"schema": schema, "timestamp": time.time()}

    # -- sanitization ----------------------------------------------------

    @staticmethod
    def sanitize(sql_query: str) -> bool:
        return sanitize_sql(sql_query)

    @staticmethod
    def clean(response: str) -> str:
        return clean_sql_response(response)

    # -- execution -------------------------------------------------------

    def execute(self, sql_query: str) -> ExecutionResult:
        cached = self._get_cached_result(sql_query)
        if cached is not None:
            return cached
        result = self._execute_core(sql_query)
        self._set_cached_result(sql_query, result)
        return result

    def _df_to_result(self, df: pd.DataFrame, sql_query: str) -> ExecutionResult:
        df_clean = df.where(pd.notnull(df), None)

        # Only stringify datetimes — leave ints/floats untouched for charts
        for col in df_clean.columns:
            if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
                df_clean[col] = df_clean[col].dt.strftime("%Y-%m-%d %H:%M:%S")

        # JSON cannot serialize Decimal, int64, float64, etc.
        # Convert to plain Python objects.
        records = df_clean.head(self.max_row_limit).to_dict(orient="records")
        clean_records = _sanitize_records(records)

        return ExecutionResult(
            type="table",
            data=clean_records,
            columns=list(df.columns),
            total_rows=len(df),
            query=sql_query,
        )

    @abstractmethod
    def _execute_core(self, sql_query: str) -> ExecutionResult:
        pass