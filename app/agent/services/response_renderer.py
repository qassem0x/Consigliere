import logging
from typing import Generator, List

from app.agent.domain import ExecutionResult
from app.agent.llm.client import LLMClient
from app.agent.prompts import ANALYSIS_FORMAT_PROMPT
from app.models.db_models import ChatSettings

logger = logging.getLogger(__name__)


class ResponseRenderer:
    def __init__(self, llm_client: LLMClient, settings: ChatSettings):
        self.llm = llm_client
        self.settings = settings

    def stream(self, user_query: str, results: List[ExecutionResult]) -> Generator[str, None, None]:
        summary = self._build_summary(results)
        zero_leaks = self.settings.zero_leaks_mode

        if zero_leaks:
            rules = (
                "RULES (Zero Leaks Mode):\n"
                "- Do NOT reveal any actual data values, numbers, metrics, or findings\n"
                "- Only describe what analytical steps were performed\n"
                "- Focus on what was analyzed and how, not what was found"
            )
            findings = "- Describe the analytical workflow (queries run, charts created, aggregations done)"
        else:
            rules = (
                "RULES:\n"
                "1. ONLY use numbers and facts from the Data above\n"
                "2. Never invent product names, categories, percentages, or trends\n"
                "3. Wrap all numbers, metric values, and proper names in backtick code spans"
            )
            findings = "- Share the key numbers and findings (straight from the data, no fluff)"

        messages = [{
            "role": "system",
            "content": ANALYSIS_FORMAT_PROMPT.format(
                user_query=user_query,
                combined_summary=summary,
                zero_leaks_mode=zero_leaks,
                zero_leaks_rules=rules,
                findings_instruction=findings,
            ),
        }]

        try:
            for token in self.llm.stream(messages, temperature=0.7, timeout=30):
                yield token
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"Analysis complete. {summary}"

    def _build_summary(self, results: List[ExecutionResult]) -> str:
        zero_leaks = self.settings.zero_leaks_mode
        parts = []
        for i, res in enumerate(results, 1):
            if res.type == "table":
                if zero_leaks:
                    parts.append(f"Step {i}: Retrieved {res.total_rows or 0} rows. Data REDACTED.")
                else:
                    cols = res.columns or []
                    col_info = f" Columns: {', '.join(cols)}" if cols else ""
                    sample = str(res.data[:10]) if res.data else "[]"
                    parts.append(f"Step {i}: Retrieved {res.total_rows or 0} rows{col_info}, Sample: {sample}")
            elif res.type == "image":
                parts.append(f"Step {i}: Created visualization" + ("" if zero_leaks else f" - {res.description or ''}"))
            elif res.type == "text":
                parts.append(f"Step {i}: " + ("Text REDACTED." if zero_leaks else str(res.data)[:100]))
            elif res.type == "error":
                parts.append(f"Step {i}: Error - {res.data}")
        return "\n".join(parts)