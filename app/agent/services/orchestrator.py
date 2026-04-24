import json
import logging
from typing import Any, AsyncGenerator, List, Optional

import pandas as pd

from app.agent.domain import ExecutionResult, Plan, Step, StepType
from app.agent.llm.client import LLMClient
from app.agent.prompts import SUMMARY_SYNTHESIS_PROMPT
from app.agent.rendering.chart import ChartRenderer
from app.agent.services.metadata_service import MetadataService
from app.agent.services.sql_builder import SQLBuilder
from app.agent.utils import sanitize_sql
from app.models.db_models import ChatSettings

logger = logging.getLogger(__name__)


class StepOrchestrator:
    def __init__(
        self,
        llm_client: LLMClient,
        executor: Any,
        sql_builder: SQLBuilder,
        chart_renderer: ChartRenderer,
        metadata_service: MetadataService,
        settings: ChatSettings,
    ):
        self.llm = llm_client
        self.executor = executor
        self.sql_builder = sql_builder
        self.chart_renderer = chart_renderer
        self.metadata_service = metadata_service
        self.settings = settings
        self.all_sqls: List[str] = []

    async def run(self, plan: Plan, user_query: str) -> AsyncGenerator[str, None]:
        results: List[ExecutionResult] = []
        self.all_sqls = []

        for step in plan.steps:
            await self.llm.check_cancelled_async()

            if step.type != StepType.SUMMARY:
                yield self._event("step_start", step)

            if step.type in (StepType.METRIC, StepType.TABLE):
                result = await self._query_step(step)
            elif step.type == StepType.CHART:
                result = await self._chart_step(step, user_query)
            elif step.type == StepType.METADATA:
                result = self.metadata_service.execute(step, user_query)
            elif step.type == StepType.SUMMARY:
                result = await self._summary_step(step, user_query, results)
            else:
                result = ExecutionResult(
                    step_number=step.number,
                    type="error",
                    data=f"Unknown step type: {step.type}",
                )

            results.append(result)
            yield self._event("step_result", step, result)

    async def _chart_step(self, step: Step, user_query: str) -> ExecutionResult:
        sql = self.sql_builder.generate(step.description)
        result = self.executor.execute(sql)

        if result.type == "error":
            logger.error(f"Chart SQL failed for step {step.number}: {result.data}")
            return ExecutionResult(
                step_number=step.number,
                step_description=step.title,
                step_type="chart",
                type="error",
                data=f"Chart query failed: {result.data}",
            )

        if result.type != "table" or not result.data:
            return ExecutionResult(
                step_number=step.number,
                step_description=step.title,
                step_type="chart",
                type="error",
                data="Query returned no rows for chart.",
            )

        df = pd.DataFrame(result.data, columns=result.columns)

        spec = self.chart_renderer.generate_spec(step, df, user_query)
        if spec is None:
            return ExecutionResult(
                step_number=step.number,
                step_description=step.title,
                step_type="chart",
                type="error",
                data="Failed to generate chart spec.",
            )

        return self.chart_renderer.render(spec, df, step)

    async def _query_step(self, step: Step) -> ExecutionResult:
        sql = self.sql_builder.generate(step.description)
        used_sql = sql
        last_error = None
        result = None

        for attempt in range(3):
            if not sanitize_sql(sql):
                return ExecutionResult(
                    step_number=step.number,
                    step_description=step.title,
                    step_type="error",
                    type="error",
                    data="Security Alert: Prohibited SQL commands detected.",
                )

            result = self.executor.execute(sql)
            if result.type != "error":
                used_sql = sql
                break

            last_error = result.data
            logger.warning(f"Step {step.number} attempt {attempt + 1}: {last_error}")
            if attempt < 2:
                sql = self.sql_builder.fix(sql, last_error)

        if result and result.type == "table" and not result.data:
            wider_sql = self.sql_builder.widen(used_sql, step.description)
            if sanitize_sql(wider_sql):
                wider_result = self.executor.execute(wider_sql)
                if wider_result.type == "table" and wider_result.data:
                    result = wider_result

        if result is None or result.type == "error":
            result = ExecutionResult(
                step_number=step.number,
                step_description=step.title,
                step_type="error",
                type="error",
                data=result.data if result else f"Failed after retries: {last_error}",
            )
        else:
            result.step_number = step.number
            result.step_description = step.title
            result.step_type = step.type.value

        self.all_sqls.append(f"-- Step {step.number}: {step.title}\n{used_sql}")
        return result

    async def _summary_step(self, step: Step, user_query: str, previous: List[ExecutionResult]) -> ExecutionResult:
        context = self._build_context(previous)
        messages = [{
            "role": "system",
            "content": SUMMARY_SYNTHESIS_PROMPT.format(
                user_query=user_query,
                context_str=context,
                step_description=step.title,
            ),
        }]
        try:
            text = await self.llm.complete_async(messages, temperature=0.5, timeout=30)
            return ExecutionResult(step_number=step.number, step_type="summary", type="text", data=text)
        except Exception:
            return ExecutionResult(step_number=step.number, step_type="summary", type="text", data="Summary generation failed.")

    @staticmethod
    def _build_context(results: List[ExecutionResult]) -> str:
        parts = []
        for i, res in enumerate(results, 1):
            if res.type == "table":
                parts.append(f"Step {i}: {res.total_rows or 0} rows")
            elif res.type == "image":
                parts.append(f"Step {i}: Chart created")
            elif res.type == "error":
                parts.append(f"Step {i}: Error - {res.data}")
            else:
                parts.append(f"Step {i}: {str(res.data)[:100] if isinstance(res.data, str) else 'Done'}")
        return "\n\n".join(parts)

    @staticmethod
    def _event(event_type: str, step: Step, result: Optional[ExecutionResult] = None) -> str:
        payload = {"type": event_type, "step_number": step.number}
        if event_type == "step_start":
            payload["description"] = step.title
            payload["step_type"] = step.type.value
        elif event_type == "step_result":
            if result is None:
                logger.error(f"_event called with result=None for step {step.number}")
                result = ExecutionResult(
                    step_number=step.number,
                    step_description=step.title,
                    step_type=step.type.value,
                    type="error",
                    data="Internal error: step result was lost",
                )
            payload["data"] = result.to_dict()
        return json.dumps(payload, default=str)