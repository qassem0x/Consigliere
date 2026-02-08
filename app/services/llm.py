import os
import dotenv
from litellm import completion
import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

dotenv.load_dotenv()

litellm.drop_params = True
litellm.set_verbose = False

MODEL_NAME = os.getenv("MODEL_NAME", "ollama/llama3.2")


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
