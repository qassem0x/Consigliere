import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator

from app.agents.interfaces import ILanguageModel
from app.models.db_models import ChatSettings

logger = logging.getLogger(__name__)


class CancelledException(Exception):
    """Raised when operation is cancelled by user."""
    pass


class TokenTracker:
    """Track LLM token usage."""

    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def add(self, usage: Dict[str, Any]):
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)

    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class BaseAgent(ABC):
    """Base agent with dependency injection and shared functionality."""

    def __init__(
        self,
        llm: ILanguageModel,
        chat_settings: Optional[ChatSettings] = None,
        cancel_event: Optional[asyncio.Event] = None,
    ):
        if chat_settings is not None:
            self.chat_settings = chat_settings
        else:
            self.chat_settings = ChatSettings(zero_leaks_mode=False, max_row_limit=100)
        
        self.llm = llm
        self.token_tracker = TokenTracker()
        self.cancel_event = cancel_event

    def check_cancelled(self):
        """Check if operation has been cancelled. Raises CancelledException if cancelled."""
        if self.cancel_event and self.cancel_event.is_set():
            raise CancelledException("Operation cancelled by user")

    async def check_cancelled_async(self):
        """Async version of check_cancelled."""
        if self.cancel_event and self.cancel_event.is_set():
            raise CancelledException("Operation cancelled by user")

    async def _call_llm_with_usage_async(
        self, messages: list, temperature: float = 0.0, timeout: int = 60
    ) -> str:
        """Async LLM call with cancellation support. Returns content string."""
        await self.check_cancelled_async()
        response = await self.llm.complete_async(messages, temperature, timeout)
        self.token_tracker.add({
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
        })
        return response.content

    def _call_llm_with_usage(
        self, messages: list, temperature: float = 0.0, timeout: int = 60
    ) -> str:
        """Sync LLM call with usage tracking. Returns content string."""
        self.check_cancelled()
        response = self.llm.complete(messages, temperature, timeout)
        self.token_tracker.add({
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
        })
        return response.content

    def _stream_final_response(
        self, user_query: str, all_results: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Stream final response token by token."""
        from app.core.prompts import ANALYSIS_FORMAT_PROMPT

        summary_parts = []
        for i, result in enumerate(all_results, 1):
            if result["type"] == "table":
                if self.chat_settings.zero_leaks_mode is True:
                    summary_parts.append(
                        f"Step {i}: Retrieved {result.get('total_rows', 0)} rows. Data REDACTED (Zero Leaks Mode)."
                    )
                else:
                    cols = result.get("columns", [])
                    col_info = f" Columns: {', '.join(cols)}" if cols else ""
                    summary_parts.append(
                        f"Step {i}: Retrieved {result.get('total_rows', 0)} rows{col_info}, Data Sample: {result.get('data', [])[:10]}"
                    )
            elif result["type"] == "image":
                if self.chat_settings.zero_leaks_mode is True:
                    summary_parts.append(f"Step {i}: Created a visualization. Details REDACTED (Zero Leaks Mode).")
                else:
                    summary_parts.append(f"Step {i}: Created visualization - {result.get('description', '')}")
            elif result["type"] == "text":
                if self.chat_settings.zero_leaks_mode is True:
                    summary_parts.append(f"Step {i}: Text result REDACTED (Zero Leaks Mode).")
                else:
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
            full_response = ""
            for item in self.llm.stream(messages, temperature=0.7, timeout=30):
                full_response += item
                yield item
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"Analysis complete. {combined_summary}"

    def _yield_step_start(
        self,
        step_number: int,
        description: str,
        step_type: Optional[str] = None,
        detailed_description: Optional[str] = None,
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
        token_usage = self.token_tracker.to_dict()
        data = {
            "type": "final_result",
            "data": {
                "text": text,
                "steps": steps,
                "code": code,
                "token_usage": {
                    "prompt_tokens": token_usage.get("prompt_tokens", 0),
                    "completion_tokens": token_usage.get("completion_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                },
            },
        }
        if plan:
            data["data"]["plan"] = plan
        return json.dumps(data)

    @abstractmethod
    async def answer(self, user_query: str, history_str: str = "") -> AsyncGenerator[str, None]:
        """Main method to answer user queries."""
        pass
