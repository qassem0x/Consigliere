import hashlib
import logging
import time
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class SQLCacheManager:
    """Manages SQL-specific caching (engines, schema, queries).
    
    Matches the behavior of the old SQLAgentCache class.
    Singleton pattern to share across all SQLAgent instances.
    """
    
    _instance = None
    
    # TTL constants (matching old values)
    CONNECTION_TTL = 3600  # 1 hour for connections
    SCHEMA_TTL = 1800     # 30 minutes for schema
    QUERY_TTL = 600       # 10 minutes for query results
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Separate stores for different cache types
        self._engine_store: Dict[str, Dict[str, Any]] = {}
        self._schema_store: Dict[str, Dict[str, Any]] = {}
        self._query_store: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SQLCacheManager initialized")
    
    def _hash_connection_string(self, connection_string: str) -> str:
        """Create a hash of connection string for cache key (without exposing credentials)."""
        return hashlib.sha256(connection_string.encode()).hexdigest()[:16]
    
    def _hash_query(self, query: str) -> str:
        """Create a hash of SQL query for cache key."""
        return hashlib.md5(query.encode()).hexdigest()
    
    # ==================== ENGINE CACHING ====================
    
    def get_engine(self, connection_string: str) -> Engine:
        """Get or create SQLAlchemy engine.
        
        Tests connection before returning to ensure it's still valid.
        """
        cache_key = self._hash_connection_string(connection_string)
        current_time = time.time()
        
        if cache_key in self._engine_store:
            entry = self._engine_store[cache_key]
            
            # Check if connection is still valid
            if current_time - entry["timestamp"] < self.CONNECTION_TTL:
                try:
                    # Test connection
                    with entry["engine"].connect() as conn:
                        conn.execute(text("SELECT 1"))
                    
                    # Update timestamp
                    entry["timestamp"] = current_time
                    logger.info(f"CACHE HIT: Using cached engine for connection")
                    return entry["engine"]
                except Exception as e:
                    logger.info(f"CACHE: Connection test failed, recreating: {e}")
                    # Fall through to create new engine
            else:
                logger.info(f"CACHE: Expired engine for connection")
                # Fall through to create new engine
        else:
            logger.info(f"CACHE MISS: Creating new engine")
        
        # Create new engine
        engine = create_engine(connection_string)
        
        self._engine_store[cache_key] = {
            "engine": engine,
            "timestamp": current_time,
            "connection_string": connection_string,
        }
        
        return engine
    
    def _dispose_engine(self, cache_key: str):
        """Properly dispose an engine."""
        if cache_key in self._engine_store:
            try:
                self._engine_store[cache_key]["engine"].dispose()
            except Exception:
                pass
            del self._engine_store[cache_key]
    
    # ==================== SCHEMA CACHING ====================
    
    def get_schema(self, connection_string: str) -> Optional[str]:
        """Get cached schema. Returns None if not cached or expired."""
        cache_key = self._hash_connection_string(connection_string)
        current_time = time.time()
        
        if cache_key in self._schema_store:
            entry = self._schema_store[cache_key]
            
            if current_time - entry["timestamp"] < self.SCHEMA_TTL:
                entry["timestamp"] = current_time
                logger.info(f"CACHE HIT: Using cached schema ({len(entry['schema'])} chars)")
                return entry["schema"]
            else:
                logger.info(f"CACHE: Expired schema for {cache_key}")
                del self._schema_store[cache_key]
        
        logger.info(f"CACHE MISS: Schema not cached for {cache_key}")
        return None
    
    def set_schema(self, connection_string: str, schema: str):
        """Store schema in cache."""
        cache_key = self._hash_connection_string(connection_string)
        
        self._schema_store[cache_key] = {
            "schema": schema,
            "timestamp": time.time(),
        }
        logger.info(f"CACHE: Stored schema ({len(schema)} chars)")
    
    # ==================== QUERY RESULT CACHING ====================
    
    def get_query_result(self, connection_string: str, query: str) -> Optional[pd.DataFrame]:
        """Get cached query result. Returns None if not cached or expired."""
        conn_key = self._hash_connection_string(connection_string)
        query_key = self._hash_query(query)
        cache_key = f"{conn_key}:{query_key}"
        current_time = time.time()
        
        if cache_key in self._query_store:
            entry = self._query_store[cache_key]
            
            if current_time - entry["timestamp"] < self.QUERY_TTL:
                entry["timestamp"] = current_time
                logger.info(f"CACHE HIT: Using cached query result ({len(entry['df'])} rows)")
                return entry["df"].copy()  # Return copy to prevent mutation
            else:
                logger.info(f"CACHE: Expired query result")
                del self._query_store[cache_key]
        
        logger.info(f"CACHE MISS: Query result not cached")
        return None
    
    def set_query_result(self, connection_string: str, query: str, df: pd.DataFrame):
        """Store query result in cache."""
        conn_key = self._hash_connection_string(connection_string)
        query_key = self._hash_query(query)
        cache_key = f"{conn_key}:{query_key}"
        
        self._query_store[cache_key] = {
            "df": df.copy(),  # Store copy to prevent external mutation
            "query": query,
            "timestamp": time.time(),
        }
        logger.info(f"CACHE: Stored query result ({len(df)} rows)")
    
    # ==================== INVALIDATION ====================
    
    def invalidate_connection(self, connection_string: str):
        """Manually remove a connection from cache (e.g., on disconnect)."""
        cache_key = self._hash_connection_string(connection_string)
        
        # Dispose engine
        if cache_key in self._engine_store:
            self._dispose_engine(cache_key)
            logger.info(f"CACHE: Manually cleared connection")
        
        # Clear schema
        if cache_key in self._schema_store:
            del self._schema_store[cache_key]
            logger.info(f"CACHE: Cleared schema for connection")
        
        # Clear all queries for this connection
        query_keys_to_remove = [
            k for k in self._query_store.keys() if k.startswith(f"{cache_key}:")
        ]
        for key in query_keys_to_remove:
            del self._query_store[key]
        
        if query_keys_to_remove:
            logger.info(f"CACHE: Cleared {len(query_keys_to_remove)} query results")
    
    def invalidate_queries(self, connection_string: str):
        """Clear all cached queries for a connection (e.g., after data modification)."""
        cache_key = self._hash_connection_string(connection_string)
        
        query_keys_to_remove = [
            k for k in self._query_store.keys() if k.startswith(f"{cache_key}:")
        ]
        for key in query_keys_to_remove:
            del self._query_store[key]
        
        if query_keys_to_remove:
            logger.info(f"CACHE: Invalidated {len(query_keys_to_remove)} query results")
    
    def clear_all(self):
        """Clear entire cache."""
        # Dispose all engines
        for cache_key in list(self._engine_store.keys()):
            self._dispose_engine(cache_key)
        
        self._engine_store.clear()
        self._schema_store.clear()
        self._query_store.clear()
        logger.info("CACHE: Cleared all cached data")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "connections": len(self._engine_store),
            "schemas": len(self._schema_store),
            "queries": len(self._query_store),
            "total_items": (
                len(self._engine_store) + 
                len(self._schema_store) + 
                len(self._query_store)
            ),
        }
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)."""
        if cls._instance is not None:
            cls._instance.clear_all()
            cls._instance = None
        logger.info("SQLCacheManager singleton reset")
