import os
from litellm import completion
import litellm
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import MODEL_NAME, validate_env

validate_env()

litellm.drop_params = True
litellm.set_verbose = False
litellm.suppress_debug_info = True

if MODEL_NAME.startswith("ollama"):
    litellm.api_base = "http://localhost:11434"

if MODEL_NAME.startswith("openrouter"):
    litellm.api_base = "https://openrouter.ai/api/v1/chat/completions"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def call_llm(messages: list, temperature: float = 0.0, timeout: int = 60) -> str:
    try:
        response = completion(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
        )
        return response.choices[0].message.content.strip()
    except litellm.exceptions.RateLimitError as e:
        print(f"RATE LIMIT HIT: {e}")
        raise Exception("Rate limit exceeded. Please wait a moment and try again.")
    except litellm.exceptions.Timeout as e:
        print(f"TIMEOUT: {e}")
        raise Exception("LLM request timed out. Try a simpler query.")
    except Exception as e:
        print(f"LLM ERROR: {e}")
        raise Exception(f"LLM service error: {str(e)}")


def call_llm_with_usage(
    messages: list, temperature: float = 0.0, timeout: int = 60
) -> dict:
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
        print(f"RATE LIMIT HIT: {e}")
        raise Exception("Rate limit exceeded. Please wait a moment and try again.")
    except litellm.exceptions.Timeout as e:
        print(f"TIMEOUT: {e}")
        raise Exception("LLM request timed out. Try a simpler query.")
    except Exception as e:
        print(f"LLM ERROR: {e}")
        raise Exception(f"LLM service error: {str(e)}")


if __name__ == "__main__":
    print(call_llm([{"role": "user", "content": "what is 7+8? and why"}]))
