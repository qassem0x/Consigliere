import asyncio
import logging
from typing import Dict, Generator, List, Optional

from app.agent.domain import TokenUsage
from app.agent.exceptions import CancelledException
from app.agent.interfaces import ILanguageModel
from app.agent.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, llm: ILanguageModel, cancel_event: Optional[asyncio.Event] = None):
        self.llm = llm
        self.cancel_event = cancel_event
        self.token_tracker = TokenTracker()

    def check_cancelled(self):
        if self.cancel_event and self.cancel_event.is_set():
            raise CancelledException("Operation cancelled by user")

    async def check_cancelled_async(self):
        if self.cancel_event and self.cancel_event.is_set():
            raise CancelledException("Operation cancelled by user")

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.0, timeout: int = 60) -> str:
        self.check_cancelled()
        response = self.llm.complete(messages, temperature, timeout)
        self.token_tracker.add({
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
        })
        return response.content

    async def complete_async(self, messages: List[Dict[str, str]], temperature: float = 0.0, timeout: int = 60) -> str:
        await self.check_cancelled_async()
        response = await self.llm.complete_async(messages, temperature, timeout)
        self.token_tracker.add({
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
        })
        return response.content

    def stream(self, messages: List[Dict[str, str]], temperature: float = 0.7, timeout: int = 30) -> Generator[str, None, None]:
        for token, usage in self.llm.stream(messages, temperature, timeout):
            if usage.total_tokens:
                self.token_tracker.add({
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                })
            yield token

    def reset_tokens(self):
        self.token_tracker.reset()