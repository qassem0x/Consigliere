from typing import Dict, Generator, Tuple
from app.agents.interfaces import ILanguageModel, LLMResponse
from app.core.llm import call_llm_with_usage, call_llm_with_usage_async, call_llm_stream


class LiteLLMAdapter(ILanguageModel):
    """Adapter that wraps litellm LLM calls."""

    def complete(
        self, messages: list[dict], temperature: float, timeout: int
    ) -> LLMResponse:
        response = call_llm_with_usage(messages, temperature, timeout)
        return LLMResponse(
            content=response.get("content", ""),
            model=response.get("model", ""),
            prompt_tokens=response.get("prompt_tokens", 0),
            completion_tokens=response.get("completion_tokens", 0),
            total_tokens=response.get("total_tokens", 0),
        )

    async def complete_async(
        self, messages: list[dict], temperature: float, timeout: int
    ) -> LLMResponse:
        response = await call_llm_with_usage_async(messages, temperature, timeout)
        return LLMResponse(
            content=response.get("content", ""),
            model=response.get("model", ""),
            prompt_tokens=response.get("prompt_tokens", 0),
            completion_tokens=response.get("completion_tokens", 0),
            total_tokens=response.get("total_tokens", 0),
        )

    def stream(
        self, messages: list[dict], temperature: float, timeout: int
    ) -> Generator[Tuple[str, Dict[str, int]], None, None]:
        """Stream response. Yields (token, usage_dict) tuples.
        
        Usage dict contains prompt_tokens, completion_tokens, total_tokens.
        Empty dict for regular tokens, populated on final usage token (after all content).
        """
        usage = {}
        
        for item in call_llm_stream(messages, temperature, timeout):
            if isinstance(item, dict) and item.get("__usage__"):
                usage = {
                    "prompt_tokens": item.get("prompt_tokens", 0),
                    "completion_tokens": item.get("completion_tokens", 0),
                    "total_tokens": item.get("total_tokens", 0),
                }
                yield "", usage
                break
            yield item, usage
            usage = {}
