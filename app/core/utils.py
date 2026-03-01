import pandas as pd
import numpy as np
import math
from typing import Any


def make_json_safe(value: Any) -> Any:
    """Recursively convert value to JSON-serializable type"""
    if isinstance(value, pd.DataFrame):
        return make_json_safe(value.to_dict(orient="records"))
    elif isinstance(value, pd.Series):
        return make_json_safe(value.to_dict())
    elif isinstance(value, np.integer):
        return int(value)
    elif isinstance(value, np.floating):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, dict):
        return {k: make_json_safe(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [make_json_safe(item) for item in value]
    elif pd.isna(value):
        return None
    return value


def sanitize_nan(obj: Any) -> Any:
    """Recursively replace NaN/Infinity float values with None so they
    serialize as JSON null instead of the bare token NaN, which PostgreSQL
    JSONB rejects."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_nan(v) for v in obj]
    return obj
