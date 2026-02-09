import json_repair
from app.core.prompts import ROUTER_PROMPT
from app.services.llm import call_llm


class BaseAgent:
    def __init__(self):
        pass

    def _decide_intent(self, user_query: str, history_str: str = "") -> str:
        """Route query to appropriate handler"""
        messages = [
            {
                "role": "user",
                "content": ROUTER_PROMPT.format(
                    query=user_query,
                    history=history_str if history_str else "No previous conversation.",
                ),
            }
        ]

        try:
            text = call_llm(messages, temperature=0.0, timeout=30)

            # Clean markdown code blocks if present
            if "```" in text:
                text = text.replace("```json", "").replace("```", "").strip()

            parsed = json_repair.loads(text)
            intent = parsed.get("intent", "DATA_ACTION")
            print(f"DEBUG: Router decided intent = {intent}")
            return intent

        except Exception as e:
            print(f"ROUTER ERROR: {e}")
            return "DATA_ACTION"  # Fail-safe: assume data question
