import json
import logging

import json_repair

from app.agent.llm.client import LLMClient
from app.agent.prompts import DOSSIER_PROMPT

logger = logging.getLogger(__name__)


class DossierService:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def generate(self, schema: str, source_type: str = "data file") -> dict:
        messages = [{
            "role": "user",
            "content": DOSSIER_PROMPT.format(schema=schema, source_type=source_type),
        }]
        try:
            response = await self.llm.complete_async(messages, temperature=0.4, timeout=60)
            cleaned = response.replace("```json", "").replace("```", "").strip()
            parsed = json_repair.loads(cleaned)
            if isinstance(parsed, dict):
                for field in ("briefing", "key_entities", "data_alerts", "recommended_actions"):
                    parsed.setdefault(field, [] if field != "briefing" else "No briefing")
                return parsed
            raise ValueError("Dossier output was not a dict")
        except Exception as e:
            logger.error(f"Dossier error: {e}")
            return {
                "briefing": "Data analysis completed.",
                "key_entities": [],
                "data_alerts": [],
                "recommended_actions": [],
            }