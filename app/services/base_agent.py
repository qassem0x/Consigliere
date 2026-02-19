import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from app.core.prompts import ANALYSIS_FORMAT_PROMPT
from app.core.llm import call_llm
from app.models.db_models import ChatSettings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(self, chat_settings: Optional[ChatSettings] = None):
        if chat_settings is not None:
            self.chat_settings = chat_settings
        else:
            self.chat_settings = ChatSettings(zero_leaks_mode=False, max_row_limit=100)

    @abstractmethod
    def _consult_brain(self, user_query: str, history_str: str = ""):
        """Implement agent-specific brain consultation."""
        pass

    def _format_final_response(
        self, user_query: str, all_results: List[Dict[str, Any]]
    ) -> str:
        """Convert technical results into natural language response."""
        summary_parts = []
        for i, result in enumerate(all_results, 1):
            if result["type"] == "table":
                if self.chat_settings.zero_leaks_mode is True:
                    summary_parts.append(
                        f"Step {i}: Retrieved {result.get('total_rows', 0)} rows. Data REDACTED (Zero Leaks Mode)."
                    )
                else:
                    cols = result.get('columns', [])
                    col_info = f" Columns: {', '.join(cols)}" if cols else ""
                    summary_parts.append(
                        f"Step {i}: Retrieved {result.get('total_rows', 0)} rows{col_info}, Data Sample: {result.get('data', [])[:10]}"
                    )
            elif result["type"] == "image":
                summary_parts.append(
                    f"Step {i}: Created visualization - {result.get('description', '')}"
                )
            elif result["type"] == "text":
                summary_parts.append(f"Step {i}: {result['data'][:100]}")
            elif result["type"] == "error":
                summary_parts.append(f"Step {i}: Error - {result.get('data', '')}")

        combined_summary = "\n".join(summary_parts)

        messages = [
            {
                "role": "system",
                "content": ANALYSIS_FORMAT_PROMPT.format(
                    user_query=user_query,
                    combined_summary=combined_summary,
                    zero_leaks_mode=self.chat_settings.zero_leaks_mode,
                ),
            }
        ]

        try:
            response = call_llm(messages, temperature=0.7, timeout=30)
            return response
        except Exception as e:
            logger.error(f"Format error: {e}")
            return f"Analysis complete. {combined_summary}"

    def _yield_step_start(
        self, step_number: int, description: str, step_type: Optional[str] = None, detailed_description: Optional[str] = None
    ) -> str:
        """Yield step_start JSON for streaming response."""
        data: Dict[str, Any] = {
            "type": "step_start",
            "step_number": step_number,
            "description": description,
        }
        if step_type:
            data["step_type"] = step_type
        if detailed_description:
            data["detailed_description"] = detailed_description
        return json.dumps(data)

    def _yield_step_result(self, result: Dict[str, Any]) -> str:
        """Yield step_result JSON for streaming response."""
        return json.dumps({"type": "step_result", "data": result})

    def _yield_final_result(
        self,
        text: str,
        steps: List[Dict[str, Any]],
        plan: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None,
    ) -> str:
        """Yield final_result JSON for streaming response."""
        data = {
            "type": "final_result",
            "data": {
                "text": text,
                "steps": steps,
                "code": code,
            },
        }
        if plan:
            data["data"]["plan"] = plan
        return json.dumps(data)

    def _yield_planning_step(self, step_number: int = 0, description: str = "Planning...") -> str:
        """Yield initial planning step."""
        return json.dumps({
            "type": "step_start",
            "step_number": step_number,
            "description": description,
        })
