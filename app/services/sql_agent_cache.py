import pandas as pd
import time
import hashlib
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class SQLAgentCache:
    _instance = None
    _connection_store: Dict[str, Dict[str, Any]] = {}
    _schema_store: Dict[str, Dict[str, Any]] = {}
    _query_store: Dict[str, Dict[str, Any]] = {}

    CONNECTION_TTL = 3600  # 1 hour for connections
    SCHEMA_TTL = 1800  # 30 minutes for schema
    QUERY_TTL = 300  # 5 minutes for query results

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SQLAgentCache, cls).__new__(cls)
        return cls._instance

    def _hash_connection_string(self, connection_string: str) -> str:
        """Create a hash of connection string for cache key (without exposing credentials)"""
        return hashlib.sha256(connection_string.encode()).hexdigest()[:16]

    def _hash_query(self, query: str) -> str:
        """Create a hash of SQL query for cache key"""
        return hashlib.md5(query.encode()).hexdigest()

    def get_engine(self, connection_string: str) -> Engine:
        """
        Retrieves SQLAlchemy engine from cache if available and fresh.
        Otherwise, creates a new engine.
        """
        cache_key = self._hash_connection_string(connection_string)
        current_time = time.time()

        if cache_key in self._connection_store:
            entry = self._connection_store[cache_key]

            # Check if connection is still valid
            if current_time - entry["timestamp"] < self.CONNECTION_TTL:
                try:
                    # Test connection
                    with entry["engine"].connect() as conn:
                        conn.execute("SELECT 1")

                    entry["timestamp"] = current_time
                    print(f"CACHE HIT: Using cached engine for connection")
                    return entry["engine"]
                except Exception as e:
                    print(f"CACHE: Connection test failed, recreating: {e}")
                    del self._connection_store[cache_key]
            else:
                print(f"CACHE: Expired engine for connection")
                # Dispose old engine
                entry["engine"].dispose()
                del self._connection_store[cache_key]

        print(f"CACHE MISS: Creating new engine")
        engine = create_engine(connection_string)

        self._connection_store[cache_key] = {
            "engine": engine,
            "timestamp": current_time,
            "connection_string": connection_string,  # Store for disposal
        }

        return engine

    def get_schema(self, connection_string: str) -> Optional[str]:
        """
        Retrieves cached schema if available and fresh.
        Returns None if not cached or expired.
        """
        cache_key = self._hash_connection_string(connection_string)
        current_time = time.time()

        if cache_key in self._schema_store:
            entry = self._schema_store[cache_key]

            if current_time - entry["timestamp"] < self.SCHEMA_TTL:
                entry["timestamp"] = current_time
                print(f"CACHE HIT: Using cached schema ({len(entry['schema'])} chars)")
                return entry["schema"]
            else:
                print(f"CACHE: Expired schema")
                del self._schema_store[cache_key]

        return None

    def set_schema(self, connection_string: str, schema: str):
        """Store schema in cache"""
        cache_key = self._hash_connection_string(connection_string)
        current_time = time.time()

        self._schema_store[cache_key] = {"schema": schema, "timestamp": current_time}
        print(f"CACHE: Stored schema ({len(schema)} chars)")

    def get_query_result(
        self, connection_string: str, query: str
    ) -> Optional[pd.DataFrame]:
        """
        Retrieves cached query result if available and fresh.
        Returns None if not cached or expired.
        """
        conn_key = self._hash_connection_string(connection_string)
        query_key = self._hash_query(query)
        cache_key = f"{conn_key}:{query_key}"
        current_time = time.time()

        if cache_key in self._query_store:
            entry = self._query_store[cache_key]

            if current_time - entry["timestamp"] < self.QUERY_TTL:
                entry["timestamp"] = current_time
                print(f"CACHE HIT: Using cached query result ({len(entry['df'])} rows)")
                return entry["df"].copy()  # Return copy to prevent mutation
            else:
                print(f"CACHE: Expired query result")
                del self._query_store[cache_key]

        return None

    def set_query_result(self, connection_string: str, query: str, df: pd.DataFrame):
        """Store query result in cache"""
        conn_key = self._hash_connection_string(connection_string)
        query_key = self._hash_query(query)
        cache_key = f"{conn_key}:{query_key}"
        current_time = time.time()

        self._query_store[cache_key] = {
            "df": df.copy(),  # Store copy to prevent external mutation
            "query": query,
            "timestamp": current_time,
        }
        print(f"CACHE: Stored query result ({len(df)} rows)")

    def invalidate_connection(self, connection_string: str):
        """Manually remove a connection from cache (e.g., on disconnect)"""
        cache_key = self._hash_connection_string(connection_string)

        if cache_key in self._connection_store:
            # Dispose engine properly
            self._connection_store[cache_key]["engine"].dispose()
            del self._connection_store[cache_key]
            print(f"CACHE: Manually cleared connection")

        # Also clear related schema and queries
        if cache_key in self._schema_store:
            del self._schema_store[cache_key]
            print(f"CACHE: Cleared schema for connection")

        # Clear all queries for this connection
        query_keys_to_remove = [
            k for k in self._query_store.keys() if k.startswith(cache_key)
        ]
        for key in query_keys_to_remove:
            del self._query_store[key]
        if query_keys_to_remove:
            print(f"CACHE: Cleared {len(query_keys_to_remove)} query results")

    def invalidate_all_queries(self, connection_string: str):
        """Clear all cached queries for a connection (e.g., after data modification)"""
        conn_key = self._hash_connection_string(connection_string)

        query_keys_to_remove = [
            k for k in self._query_store.keys() if k.startswith(conn_key)
        ]
        for key in query_keys_to_remove:
            del self._query_store[key]

        if query_keys_to_remove:
            print(f"CACHE: Invalidated {len(query_keys_to_remove)} query results")

    def clear_all(self):
        """Clear entire cache (e.g., on application restart)"""
        # Dispose all engines
        for entry in self._connection_store.values():
            entry["engine"].dispose()

        self._connection_store.clear()
        self._schema_store.clear()
        self._query_store.clear()
        print("CACHE: Cleared all cached data")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about current cache state"""
        return {
            "connections": len(self._connection_store),
            "schemas": len(self._schema_store),
            "queries": len(self._query_store),
            "total_items": len(self._connection_store)
            + len(self._schema_store)
            + len(self._query_store),
        }
