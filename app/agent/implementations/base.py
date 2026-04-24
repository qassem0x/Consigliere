import json
import logging
from abc import ABC
from typing import AsyncGenerator, List, Optional

from app.agent.domain import ExecutionResult, Intent, Plan
from app.agent.interfaces import IQueryExecutor, ISchemaProvider
from app.agent.llm.client import LLMClient
from app.agent.rendering.chart import ChartRenderer
from app.agent.services import (
    DossierService,
    MetadataService,
    Planner,
    ResponseRenderer,
    SQLBuilder,
    StepOrchestrator,
)
from app.models.db_models import ChatSettings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(
        self,
        llm_client: LLMClient,
        executor: IQueryExecutor,
        schema_provider: ISchemaProvider,
        brain_prompt: str,
        settings: Optional[ChatSettings] = None,
        chat_memory=None,
    ):
        self.llm = llm_client
        self.executor = executor
        self.schema_provider = schema_provider
        self.brain_prompt = brain_prompt
        self.settings = settings or ChatSettings(zero_leaks_mode=False, max_row_limit=100)
        self.chat_memory = chat_memory
        self._schema: Optional[str] = None
        self._dossier_service = DossierService(llm_client)

    @property
    def schema(self) -> str:
        if self._schema is None:
            cached = self.executor.get_schema()
            if cached:
                self._schema = cached
            else:
                self._schema = self.schema_provider.infer()
                self.executor.set_schema(self._schema)
        return self._schema

    @property
    def token_tracker(self):
        return self.llm.token_tracker

    @property
    def cancel_event(self):
        return self.llm.cancel_event

    async def generate_dossier(self) -> dict:
        return await self._dossier_service.generate(self.schema, self._source_type())

    def _source_type(self) -> str:
        return self.__class__.__name__.replace("Agent", "").lower()

    async def answer(self, user_query: str, history_str: str = "") -> AsyncGenerator[str, None]:
        custom_prompt = self.settings.custom_prompt or ""

        planner = Planner(self.llm, self.brain_prompt, self.schema)
        plan = await planner.create_plan(user_query, history_str, str(custom_prompt))

        print("PLAN: ", plan)

        if plan.intent == Intent.GENERAL_CHAT:
            yield self._final_json("I'm Consigliere, your AI data analysis assistant.")
            return

        if plan.intent == Intent.FORBIDDEN:
            yield self._final_json(
                "I can only perform read operations. "
                "I cannot execute INSERT, UPDATE, DELETE, DROP, or other write operations."
            )
            return

        orchestrator = StepOrchestrator(
            llm_client=self.llm,
            executor=self.executor,
            sql_builder=SQLBuilder(self.llm, self.schema),
            chart_renderer=ChartRenderer(self.llm, self.settings, self.executor.plots_dir),
            metadata_service=MetadataService(self.schema, self.settings),
            settings=self.settings,
        )

        yield json.dumps({"type": "step_start", "step_number": 0, "description": "Planning..."})
    
        all_results: List[ExecutionResult] = []
        async for event in orchestrator.run(plan, user_query):
            yield event
            data = json.loads(event)
            if data["type"] == "step_result":
                all_results.append(ExecutionResult.from_dict(data["data"]))

        renderer = ResponseRenderer(self.llm, self.settings)
        accumulated = ""
        for token in renderer.stream(plan.enhanced_prompt, all_results):
            accumulated += token
            yield json.dumps({"type": "token", "data": token, "is_final": False})

        code = "\n\n".join(orchestrator.all_sqls) or "-- No SQL executed"
        yield json.dumps({
            "type": "final_result",
            "data": {
                "text": accumulated,
                "steps": [r.to_dict() for r in all_results],
                "plan": [s.to_dict() for s in plan.steps],
                "code": code,
                "token_usage": self.llm.token_tracker.to_dict(),
            },
        })

    def _final_json(self, text: str) -> str:
        return json.dumps({
            "type": "final_result",
            "data": {"text": text, "steps": [], "code": None},
        })