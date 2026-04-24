from app.agent.prompts.base import (
    SUMMARY_SYNTHESIS_PROMPT,
    ANALYSIS_FORMAT_PROMPT,
    DOSSIER_PROMPT,
)

from app.agent.prompts.db import (
    SQL_BRAIN_PROMPT,
    STRICT_SQL_RULES,
)

from app.agent.prompts.file import (
    FILE_BRAIN_PROMPT,
    FILE_SQL_GENERATOR_PROMPT,
    FILE_SQL_FIX_PROMPT,
    FILE_EMPTY_RESULT_PROMPT,
    CHART_JSON_GENERATOR_PROMPT,
    METADATA_PROMPT,
)

__all__ = [
    # Base prompts (universal)
    "SUMMARY_SYNTHESIS_PROMPT",
    "ANALYSIS_FORMAT_PROMPT",
    "DOSSIER_PROMPT",
    # SQL database prompts
    "SQL_BRAIN_PROMPT",
    "STRICT_SQL_RULES",
    # File-based prompts (Excel, CSV, Parquet, JSON)
    "FILE_BRAIN_PROMPT",
    "FILE_SQL_GENERATOR_PROMPT",
    "FILE_SQL_FIX_PROMPT",
    "FILE_EMPTY_RESULT_PROMPT",
    "CHART_JSON_GENERATOR_PROMPT",
    "METADATA_PROMPT",
]