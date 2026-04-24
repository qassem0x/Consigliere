import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class InMemoryCache:
    _instance: Optional["InMemoryCache"] = None
    DEFAULT_TTL = 1800

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store: Dict[str, Dict[str, Any]] = {}
            cls._instance._initialized = True
            logger.info("InMemoryCache initialized")
        return cls._instance

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if not entry:
            logger.debug(f"CACHE MISS: {key}")
            return None
        if time.time() - entry["timestamp"] < entry["ttl"]:
            entry["timestamp"] = time.time()
            logger.debug(f"CACHE HIT: {key}")
            return entry["value"]
        logger.debug(f"CACHE EXPIRED: {key}")
        del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self._store[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl if ttl is not None else self.DEFAULT_TTL,
        }
        logger.debug(f"CACHE SET: {key}")

    def delete(self, key: str):
        if key in self._store:
            del self._store[key]
            logger.debug(f"CACHE DELETE: {key}")

    def clear(self):
        self._store.clear()
        logger.info("CACHE CLEARED")

    def get_stats(self) -> Dict[str, Any]:
        return {"total_keys": len(self._store), "keys": list(self._store.keys())}

    @classmethod
    def reset_instance(cls):
        if cls._instance is not None:
            cls._instance._store.clear()
            cls._instance = None
        logger.info("InMemoryCache singleton reset")