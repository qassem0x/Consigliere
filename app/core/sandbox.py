"""
Safe Python code execution sandbox for AI agents.

Uses safepyrun (AnswerDotAI) to execute untrusted code in a controlled environment.
Based on RestrictedPython with an allowlist approach for data science workloads.

Usage:
    from app.core.sandbox import execute_code

    result = await execute_code("df.groupby('region').sum()", df=df)
"""

import asyncio
from functools import partial
from typing import Any, Dict, Optional
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


class Sandbox:
    """
    Safe code execution sandbox for data analysis agents.

    Uses allowlist-based approach - only explicitly allowed functions/methods
    can be called. This is safer than blacklist-based exec() which relies on
    filtering dangerous keywords.
    """

    def __init__(self):
        self._sandbox = None
        self._lock = asyncio.Lock()

    def _create_sandbox(self):
        """Create a new safepyrun sandbox with data science allowlist."""
        from safepyrun import RunPython

        sandbox = RunPython()

        # Core data science libraries
        sandbox.allow("pandas")
        sandbox.allow("pandas.DataFrame")
        sandbox.allow("pandas.Series")
        sandbox.allow("pandas.GroupBy")
        sandbox.allow("numpy")
        sandbox.allow("numpy.array")
        sandbox.allow("numpy.nan")
        sandbox.allow("matplotlib")
        sandbox.allow("matplotlib.pyplot")
        sandbox.allow("matplotlib.figure")

        # Safe builtins
        sandbox.allow("print")
        sandbox.allow("len")
        sandbox.allow("sum")
        sandbox.allow("min")
        sandbox.allow("max")
        sandbox.allow("abs")
        sandbox.allow("sorted")
        sandbox.allow("range")
        sandbox.allow("enumerate")
        sandbox.allow("zip")
        sandbox.allow("any")
        sandbox.allow("all")
        sandbox.allow("map")
        sandbox.allow("filter")

        # String operations
        sandbox.allow("str")
        sandbox.allow("int")
        sandbox.allow("float")
        sandbox.allow("bool")
        sandbox.allow("list")
        sandbox.allow("dict")
        sandbox.allow("tuple")
        sandbox.allow("set")

        # Math operations
        sandbox.allow("round")
        sandbox.allow("divmod")
        sandbox.allow("pow")

        return sandbox

    async def execute(
        self,
        code: str,
        df: Optional[pd.DataFrame] = None,
        plt_obj: Optional[plt] = None,
        pd_module: Optional[pd] = None,
        np_module: Optional[np] = None,
    ) -> Dict[str, Any]:
        """
        Execute code in sandbox.

        Args:
            code: Python code to execute
            df: Optional DataFrame to make available as 'df'
            plt_obj: Optional matplotlib.pyplot to make available
            pd_module: Optional pandas module to make available
            np_module: Optional numpy module to make available

        Returns:
            Dict with 'result', 'output', 'error' keys
        """
        async with self._lock:
            if self._sandbox is None:
                self._sandbox = self._create_sandbox()

        # Prepare context
        context = {}
        if df is not None:
            context["df"] = df
        if plt_obj is not None:
            context["plt"] = plt_obj
        if pd_module is not None:
            context["pd"] = pd_module
        if np_module is not None:
            context["np"] = np_module

        try:
            result = await self._sandbox(code, **context)
            return {
                "result": result.get("result"),
                "output": result.get("output", ""),
                "error": None,
            }
        except Exception as e:
            return {
                "result": None,
                "output": "",
                "error": str(e),
            }


# Global sandbox instance
_sandbox_instance: Optional[Sandbox] = None


def get_sandbox() -> Sandbox:
    """Get or create the global sandbox instance."""
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = Sandbox()
    return _sandbox_instance


async def execute_code(
    code: str, df: Optional[pd.DataFrame] = None, **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to execute code in sandbox.

    Args:
        code: Python code to execute
        df: Optional DataFrame
        **kwargs: Additional context variables

    Returns:
        Dict with 'result', 'output', 'error' keys
    """
    sandbox = get_sandbox()

    # Handle matplotlib - need to pass the module, not instance
    plt_context = kwargs.pop("plt", plt)
    pd_context = kwargs.pop("pd", pd)
    np_context = kwargs.pop("np", np)

    return await sandbox.execute(
        code,
        df=df,
        plt_obj=plt_context,
        pd_module=pd_context,
        np_module=np_context,
    )


def execute_code_sync(
    code: str, df: Optional[pd.DataFrame] = None, **kwargs
) -> Dict[str, Any]:
    """
    Synchronous wrapper for execute_code.

    Use this if you're in a sync context.
    """
    return asyncio.run(execute_code(code, df=df, **kwargs))
