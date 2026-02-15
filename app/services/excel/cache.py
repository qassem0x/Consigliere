import pandas as pd
import time
from typing import Dict, Any


class DataCache:
    _instance = None
    _store: Dict[str, Any] = {}
    TTL = 1800

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataCache, cls).__new__(cls)
        return cls._instance

    def get_data(self, file_path: str) -> pd.DataFrame:
        """
        Retrieves DataFrame from RAM if available and fresh.
        Otherwise, loads it from the disk.
        """
        current_time = time.time()

        if file_path in self._store:
            entry = self._store[file_path]

            if current_time - entry["timestamp"] < self.TTL:
                entry["timestamp"] = current_time
                return entry["df"]
            else:
                print(f"CACHE: Expired entry for {file_path}")
                del self._store[file_path]

        print(f"CACHE MISS: Loading from disk -> {file_path}")
        try:
            if file_path.endswith(".parquet"):
                df = pd.read_parquet(file_path)
            elif file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_parquet(file_path)

            self._store[file_path] = {"df": df, "timestamp": current_time}
            return df
        except Exception as e:
            print(f"CACHE ERROR: {e}")
            raise e

    def invalidate(self, file_path: str):
        """Manually remove a file from memory (e.g., on chat delete)"""
        if file_path in self._store:
            del self._store[file_path]
            print(f"CACHE: Manually cleared {file_path}")
