import hashlib
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _get_readonly_connect_args(connection_string: str) -> dict:
    if not connection_string:
        return {}
    lower = connection_string.lower()
    if lower.startswith("postgresql") or lower.startswith("postgres"):
        return {"options": "-c default_transaction_read_only=on"}
    elif lower.startswith("mysql"):
        return {"read_only": True}
    return {}


class SQLCacheManager:
    _instance = None
    CONNECTION_TTL = 3600
    SCHEMA_TTL = 1800
    QUERY_TTL = 600

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._engine_store: Dict[str, Any] = {}
            cls._instance._schema_store: Dict[str, Any] = {}
            cls._instance._query_store: Dict[str, Any] = {}
            cls._instance._initialized = True
            logger.info("SQLCacheManager initialized")
        return cls._instance

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    @staticmethod
    def _mask_connection_string(conn_str: str) -> str:
        parsed = urlparse(conn_str)
        if parsed.password:
            return conn_str.replace(parsed.password, "****")
        return conn_str

    def _conn_key(self, connection_string: str) -> str:
        return self._hash(connection_string)

    def _query_key(self, connection_string: str, query: str) -> str:
        return f"{self._conn_key(connection_string)}:{hashlib.md5(query.encode()).hexdigest()}"

    def get_engine(self, connection_string: str) -> Engine:
        key = self._conn_key(connection_string)
        now = time.time()
        entry = self._engine_store.get(key)

        if entry and now - entry["timestamp"] < self.CONNECTION_TTL:
            try:
                with entry["engine"].connect() as conn:
                    conn.execute(text("SELECT 1"))
                entry["timestamp"] = now
                logger.info("CACHE HIT: engine")
                return entry["engine"]
            except Exception as e:
                logger.info(f"CACHE: connection test failed, recreating: {e}")
                self._dispose_engine(key)

        logger.info("CACHE MISS: creating new engine")
        readonly_args = _get_readonly_connect_args(connection_string)
        engine = create_engine(connection_string, connect_args=readonly_args)
        self._engine_store[key] = {
            "engine": engine,
            "timestamp": now,
            "connection_string": self._mask_connection_string(connection_string),
        }
        return engine

    def _dispose_engine(self, key: str):
        entry = self._engine_store.pop(key, None)
        if entry:
            try:
                entry["engine"].dispose()
            except Exception:
                pass

    def get_schema(self, connection_string: str) -> Optional[str]:
        key = self._conn_key(connection_string)
        entry = self._schema_store.get(key)
        if entry and time.time() - entry["timestamp"] < self.SCHEMA_TTL:
            entry["timestamp"] = time.time()
            logger.info(f"CACHE HIT: schema ({len(entry['schema'])} chars)")
            return entry["schema"]
        logger.info("CACHE MISS: schema")
        return None

    def set_schema(self, connection_string: str, schema: str):
        key = self._conn_key(connection_string)
        self._schema_store[key] = {"schema": schema, "timestamp": time.time()}
        logger.info(f"CACHE: stored schema ({len(schema)} chars)")

    def get_query_result(self, connection_string: str, query: str) -> Optional[pd.DataFrame]:
        key = self._query_key(connection_string, query)
        entry = self._query_store.get(key)
        if entry and time.time() - entry["timestamp"] < self.QUERY_TTL:
            entry["timestamp"] = time.time()
            logger.info(f"CACHE HIT: query result ({len(entry['df'])} rows)")
            return entry["df"].copy()
        logger.info("CACHE MISS: query result")
        return None

    def set_query_result(self, connection_string: str, query: str, df: pd.DataFrame):
        key = self._query_key(connection_string, query)
        self._query_store[key] = {"df": df.copy(), "query": query, "timestamp": time.time()}
        logger.info(f"CACHE: stored query result ({len(df)} rows)")

    def invalidate_connection(self, connection_string: str):
        key = self._conn_key(connection_string)
        self._dispose_engine(key)
        self._schema_store.pop(key, None)
        qkeys = [k for k in self._query_store if k.startswith(f"{key}:")]
        for k in qkeys:
            del self._query_store[k]
        logger.info(f"CACHE: invalidated connection + {len(qkeys)} queries")

    def invalidate_queries(self, connection_string: str):
        key = self._conn_key(connection_string)
        qkeys = [k for k in self._query_store if k.startswith(f"{key}:")]
        for k in qkeys:
            del self._query_store[k]
        logger.info(f"CACHE: invalidated {len(qkeys)} queries")

    def clear_all(self):
        for key in list(self._engine_store.keys()):
            self._dispose_engine(key)
        self._engine_store.clear()
        self._schema_store.clear()
        self._query_store.clear()
        logger.info("CACHE: cleared all")

    def get_stats(self) -> Dict[str, int]:
        return {
            "connections": len(self._engine_store),
            "schemas": len(self._schema_store),
            "queries": len(self._query_store),
        }

    @classmethod
    def reset_instance(cls):
        if cls._instance is not None:
            cls._instance.clear_all()
            cls._instance = None
        logger.info("SQLCacheManager singleton reset")