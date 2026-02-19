import os
import logging
from litellm import completion
import litellm
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import MODEL_NAME, validate_env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

validate_env()

litellm.drop_params = True
litellm.set_verbose = False
litellm.suppress_debug_info = True

if MODEL_NAME.startswith("ollama"):
    litellm.api_base = "http://localhost:11434"

if MODEL_NAME.startswith("openrouter"):
    litellm.api_base = "https://openrouter.ai/api/v1/chat/completions"


def _validate_llm_params(temperature: float, timeout: int) -> None:
    if not (0.0 <= temperature <= 2.0):
        raise ValueError("Temperature must be between 0.0 and 2.0")
    if timeout <= 0:
        raise ValueError("Timeout must be a positive integer")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def call_llm(messages: list, temperature: float = 0.0, timeout: int = 60) -> str:
    _validate_llm_params(temperature, timeout)
    try:
        response = completion(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
        )
        return response.choices[0].message.content.strip()
    except litellm.exceptions.RateLimitError as e:
        logger.error(f"RATE LIMIT HIT: {e}")
        raise Exception("Rate limit exceeded. Please wait a moment and try again.")
    except litellm.exceptions.Timeout as e:
        logger.error(f"TIMEOUT: {e}")
        raise Exception("LLM request timed out. Try a simpler query.")
    except Exception as e:
        logger.error(f"LLM ERROR: {e}")
        raise Exception(f"LLM service error: {str(e)}")


def call_llm_stream(messages: list, temperature: float = 0.0, timeout: int = 60):
    """Stream LLM response token by token.
    
    Yields individual tokens as they are generated.
    After iteration completes, yields a final dict with usage info.
    """
    _validate_llm_params(temperature, timeout)
    try:
        response = completion(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
            stream=True,
        )
        
        # Track tokens manually since streaming doesn't always provide usage
        prompt_tokens = 0
        completion_tokens = 0
        full_content = ""
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_content += token
                completion_tokens += 1
                yield token
            
            # Try to get usage from the final chunk if available
            if hasattr(chunk, 'usage') and chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens
        
        # Estimate prompt tokens (rough approximation: 1 token ≈ 4 chars)
        if prompt_tokens == 0:
            total_chars = sum(len(m.get("content", "")) for m in messages)
            prompt_tokens = total_chars // 4
        
        # Yield usage info as final item
        yield {
            "__usage__": True,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "content": full_content
        }
        
    except litellm.exceptions.RateLimitError as e:
        logger.error(f"RATE LIMIT HIT: {e}")
        raise Exception("Rate limit exceeded. Please wait a moment and try again.")
    except litellm.exceptions.Timeout as e:
        logger.error(f"TIMEOUT: {e}")
        raise Exception("LLM request timed out. Try a simpler query.")
    except Exception as e:
        logger.error(f"LLM ERROR: {e}")
        raise Exception(f"LLM service error: {str(e)}")


def call_llm_with_usage(
    messages: list, temperature: float = 0.0, timeout: int = 60
) -> dict:
    _validate_llm_params(temperature, timeout)
    try:
        response = completion(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
        )
        content = response.choices[0].message.content.strip()

        usage = {
            "content": content,
            "model": response.model,
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": (
                response.usage.completion_tokens if response.usage else 0
            ),
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }
        return usage
    except litellm.exceptions.RateLimitError as e:
        logger.error(f"RATE LIMIT HIT: {e}")
        raise Exception("Rate limit exceeded. Please wait a moment and try again.")
    except litellm.exceptions.Timeout as e:
        logger.error(f"TIMEOUT: {e}")
        raise Exception("LLM request timed out. Try a simpler query.")
    except Exception as e:
        logger.error(f"LLM ERROR: {e}")
        raise Exception(f"LLM service error: {str(e)}")


if __name__ == "__main__":
    print(call_llm([{"role": "user", "content": "what is 7+8? and why"}]))
