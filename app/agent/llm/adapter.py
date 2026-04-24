from typing import Dict, Generator, Tuple

from app.agent.domain import LLMResponse, TokenUsage
from app.agent.interfaces import ILanguageModel
from app.core.llm import call_llm_with_usage, call_llm_with_usage_async, call_llm_stream


class LiteLLMAdapter(ILanguageModel):
    def _to_response(self, response: dict) -> LLMResponse:
        return LLMResponse(
            content=response.get("content", ""),
            model=response.get("model", ""),
            prompt_tokens=response.get("prompt_tokens", 0),
            completion_tokens=response.get("completion_tokens", 0),
            total_tokens=response.get("total_tokens", 0),
        )

    def complete(self, messages: list[dict], temperature: float, timeout: int) -> LLMResponse:
        return self._to_response(call_llm_with_usage(messages, temperature, timeout))

    async def complete_async(self, messages: list[dict], temperature: float, timeout: int) -> LLMResponse:
        return self._to_response(await call_llm_with_usage_async(messages, temperature, timeout))

    def stream(self, messages: list[dict], temperature: float, timeout: int) -> Generator[Tuple[str, TokenUsage], None, None]:
        usage = TokenUsage()
        for item in call_llm_stream(messages, temperature, timeout):
            if isinstance(item, dict) and item.get("__usage__"):
                usage = TokenUsage(
                    prompt_tokens=item.get("prompt_tokens", 0),
                    completion_tokens=item.get("completion_tokens", 0),
                    total_tokens=item.get("total_tokens", 0),
                )
                yield "", usage
                break
            yield item, usage
            usage = TokenUsage()