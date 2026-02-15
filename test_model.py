from litellm import completion
import litellm

litellm.api_base = "http://localhost:11434"

response = completion(
    model="ollama/llama2:7b",
    messages=[{"role": "user", "content": "Explain transformers like I'm 12."}],
    api_base="http://localhost:11434",
)

print(response["choices"][0]["message"]["content"])
