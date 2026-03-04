import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class InMemoryCache:
    """In-memory cache with singleton pattern and TTL support.
    
    Matches the behavior of the old DataCache class.
    """
    
    _instance = None
    _store: Dict[str, Dict[str, Any]] = {}
    DEFAULT_TTL = 1800  # 30 minutes
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._store = {}
        self.default_ttl = self.DEFAULT_TTL
        logger.info("InMemoryCache initialized")
    
    def get(self, key: str) -> Any:
        """Get value from cache. Returns None if not found or expired."""
        if key not in self._store:
            logger.debug(f"CACHE MISS: {key}")
            return None
        
        entry = self._store[key]
        current_time = time.time()
        
        # Check TTL
        if current_time - entry["timestamp"] < entry["ttl"]:
            # Cache hit - update timestamp to keep it fresh
            entry["timestamp"] = current_time
            logger.debug(f"CACHE HIT: {key}")
            return entry["value"]
        else:
            # Expired
            logger.debug(f"CACHE EXPIRED: {key}")
            del self._store[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL (defaults to DEFAULT_TTL)."""
        self._store[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl if ttl is not None else self.default_ttl,
        }
        logger.debug(f"CACHE SET: {key}")
    
    def delete(self, key: str):
        """Delete a specific key from cache."""
        if key in self._store:
            del self._store[key]
            logger.debug(f"CACHE DELETE: {key}")
    
    def invalidate(self, key: str):
        """Alias for delete for backward compatibility."""
        self.delete(key)
    
    def clear(self):
        """Clear all cache entries."""
        self._store.clear()
        logger.info("CACHE CLEARED: All entries removed")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "total_keys": len(self._store),
            "keys": list(self._store.keys()),
        }
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)."""
        if cls._instance is not None:
            cls._instance._store.clear()
            cls._instance = None
        logger.info("InMemoryCache singleton reset")
