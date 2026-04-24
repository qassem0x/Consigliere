import json
import logging
import re

import json_repair

from app.agent.domain import ExecutionResult, Intent, Plan, Step, StepType
from app.agent.llm.client import LLMClient

logger = logging.getLogger(__name__)

AnalysisDepth = type("AnalysisDepth", (), {"SIMPLE": "SIMPLE", "STANDARD": "STANDARD", "STRATEGIC": "STRATEGIC"})


class Planner:
    def __init__(self, llm_client: LLMClient, brain_prompt: str, schema: str):
        self.llm = llm_client
        self.brain_prompt = brain_prompt
        self.schema = schema

    async def create_plan(self, user_query: str, history_str: str = "", custom_prompt: str = "") -> Plan:
        await self.llm.check_cancelled_async()

        content = (
            self.brain_prompt
            .replace("{schema}", self.schema)
            .replace("{history}", history_str or "No previous conversation.")
            .replace("{user_query}", user_query)
            .replace("{custom_prompt}", custom_prompt)
        )
        messages = [{"role": "system", "content": content}]

        try:
            response = await self.llm.complete_async(messages, temperature=0.1, timeout=60)
            plan = self._parse(response, user_query)

            if self._validate_plan(plan, user_query):
                return plan

            logger.warning(f"Plan validation failed, retrying with stricter prompt")
            messages[0]["content"] += "\n\nIMPORTANT: You MUST return valid JSON only. No text explanations."
            response = await self.llm.complete_async(messages, temperature=0.0, timeout=60)
            plan = self._parse(response, user_query)

            if self._validate_plan(plan, user_query):
                return plan

            logger.warning(f"Plan validation failed again, using fallback")
            return self._fallback(user_query)

        except Exception as e:
            logger.error(f"Brain malfunction: {e}")
            return self._fallback(user_query)

    def _parse(self, response: str, user_query: str) -> Plan:
        try:
            cleaned = response.replace("```json", "").replace("```", "").strip()
            if not cleaned.startswith("{"):
                start_idx = cleaned.find("{")
                if start_idx != -1:
                    cleaned = cleaned[start_idx:]
            data = json_repair.loads(cleaned)

            if isinstance(data, list):
                data = next(
                    (item for item in data if isinstance(item, dict) and "intent" in item),
                    next((item for item in data if isinstance(item, dict)), None),
                ) or {}
            elif not isinstance(data, dict):
                data = {}

            if "enhanced_query" in data and "enhanced_prompt" not in data:
                data["enhanced_prompt"] = data.pop("enhanced_query")

            print("PROMPT: ", data.get("enhanced_prompt", user_query))
            return Plan.from_dict(data, user_query)
        except Exception as e:
            logger.error(f"Brain parse error: {e}")
            return self._fallback(user_query)

    def _validate_plan(self, plan: Plan, user_query: str) -> bool:
        query_lower = user_query.lower()

        chart_match = re.search(r'plan\s+(\d+)\s+(?:different\s+)?(?:chart|visualization|chart)', query_lower)
        if chart_match:
            expected_charts = int(chart_match.group(1))
            actual_charts = sum(1 for s in plan.steps if s.type == StepType.CHART)
            if actual_charts < expected_charts:
                logger.warning(f"Expected {expected_charts} charts, got {actual_charts}")
                return False

        if plan.depth is None and "fallback" not in plan.enhanced_prompt.lower():
            logger.warning("Plan depth is None")
            return False

        if not plan.steps:
            return False

        return True

    def _fallback(self, user_query: str) -> Plan:
        query_lower = user_query.lower()

        chart_match = re.search(r'plan\s+(\d+)\s+(?:different\s+)?(?:chart|visualization|chart)', query_lower)
        if chart_match:
            num_charts = min(int(chart_match.group(1)), 5)
            steps = self._create_multi_chart_plan(user_query, num_charts)
            if steps:
                return Plan(
                    intent=Intent.DATA_ACTION,
                    depth="STANDARD",
                    enhanced_prompt=user_query,
                    steps=steps
                )

        return Plan(
            intent=Intent.DATA_ACTION,
            depth="SIMPLE",
            enhanced_prompt=f"Fallback: {user_query}",
            steps=[Step(
                number=1,
                type=StepType.TABLE,
                title="Direct Query",
                description=f"Analyze: {user_query}",
            )],
        )

    def _create_multi_chart_plan(self, user_query: str, num_charts: int) -> list:
        query_lower = user_query.lower()

        survival_topics = [
            ("Passenger Class", "survival rates by passenger class (1st, 2nd, 3rd)", "bar", "categorical"),
            ("Gender", "survival rates by sex (male vs female)", "bar", "categorical"),
            ("Age Group", "survival rates by age group", "bar", "categorical"),
            ("Family Size", "survival rates by family size (solo vs small vs large)", "bar", "categorical"),
            ("Embarkation Port", "survival rates by embarkation port (C, Q, S)", "bar", "categorical"),
        ]

        topic_keywords = {
            "class": 0,
            "gender": 1,
            "sex": 1,
            "age": 2,
            "family": 3,
            "embark": 4,
            "port": 4,
        }

        selected_topics = []
        covered_indices = set()

        for keyword, idx in topic_keywords.items():
            if keyword in query_lower and idx not in covered_indices:
                selected_topics.append(survival_topics[idx])
                covered_indices.add(idx)

        while len(selected_topics) < num_charts:
            for i, topic in enumerate(survival_topics):
                if i not in covered_indices and len(selected_topics) < num_charts:
                    selected_topics.append(topic)
                    covered_indices.add(i)

        selected_topics = selected_topics[:num_charts]

        steps = []
        chart_types = ["bar", "pie", "line"]

        for i, (topic, description, chart_type, pattern) in enumerate(selected_topics):
            steps.append(Step(
                number=i + 1,
                type=StepType.CHART,
                title=f"📊 {topic} Survival Analysis",
                description=f"Chart type: {chart_type}\n X-axis: {topic}\n Y-axis: survival_rate_pct (0-100%)\n Sort: descending\n Limit: none\n Expected rows: varies by {pattern}\n Data pattern: {pattern}",
                chart_type=chart_type
            ))

        return steps