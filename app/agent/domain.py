from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Intent(str, Enum):
    DATA_ACTION = "DATA_ACTION"
    GENERAL_CHAT = "GENERAL_CHAT"
    FORBIDDEN = "FORBIDDEN"
    METADATA = "METADATA"


class AnalysisDepth(str, Enum):
    SIMPLE = "SIMPLE"
    STANDARD = "STANDARD"
    STRATEGIC = "STRATEGIC"


class StepType(str, Enum):
    METRIC = "metric"
    TABLE = "table"
    CHART = "chart"
    SUMMARY = "summary"
    METADATA = "metadata"


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class Step:
    number: int
    type: StepType
    title: str
    description: str
    chart_type: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Step":
        return cls(
            number=d.get("step_number", 0),
            type=StepType(d.get("type", "table")),
            title=d.get("title", ""),
            description=d.get("description", d.get("detailed_description", "")),
            chart_type=d.get("chart_type"),
        )

    def to_dict(self) -> dict:
        return {
            "step_number": self.number,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "chart_type": self.chart_type,
        }


@dataclass
class Plan:
    intent: Intent
    depth: Optional[AnalysisDepth]
    enhanced_prompt: str
    steps: List[Step]

    @classmethod
    def from_dict(cls, d: dict, user_query: str) -> "Plan":
        intent = Intent(d.get("intent", "DATA_ACTION"))
        depth = d.get("analysis_depth")
        if depth:
            depth = AnalysisDepth(depth)
        enhanced = d.get("enhanced_prompt", d.get("enhanced_query", user_query))
        raw_steps = d.get("plan", [])
        steps = [Step.from_dict(s) for s in raw_steps]
        return cls(intent=intent, depth=depth, enhanced_prompt=enhanced, steps=steps)


@dataclass
class ExecutionResult:
    step_number: int = 0
    step_description: str = ""
    step_type: str = "table"
    type: str = "text"
    data: Any = None
    columns: Optional[List[str]] = None
    total_rows: Optional[int] = None
    query: Optional[str] = None
    mime: Optional[str] = None
    description: Optional[str] = None
    chart_json: Optional[dict] = None

    @classmethod
    def from_dict(cls, d: dict) -> "ExecutionResult":
        if d is None:
            return cls(
                step_number=0,
                step_description="",
                step_type="table",
                type="error",
                data="Empty result payload",
            )
        return cls(
            step_number=d.get("step_number", 0),
            step_description=d.get("step_description", ""),
            step_type=d.get("step_type", "table"),
            type=d.get("type", "text"),
            data=d.get("data"),
            columns=d.get("columns"),
            total_rows=d.get("total_rows"),
            query=d.get("query"),
            mime=d.get("mime"),
            description=d.get("description"),
            chart_json=d.get("chart_json"),
        )

    def to_dict(self) -> dict:
        d = {
            "step_number": self.step_number,
            "step_description": self.step_description,
            "step_type": self.step_type,
            "type": self.type,
            "data": self.data,
        }
        for attr in ("columns", "total_rows", "query", "mime", "description", "chart_json"):
            val = getattr(self, attr)
            if val is not None:
                d[attr] = val
        return d


@dataclass
class ChartSpec:
    type: str
    x: str
    y: str
    title: str
    xlabel: str
    ylabel: str
    sort: Optional[str] = None
    limit: Optional[int] = None

    @classmethod
    def from_dict(cls, d: dict) -> "ChartSpec":
        return cls(
            type=d.get("type", "bar"),
            x=d.get("x", ""),
            y=d.get("y", ""),
            title=d.get("title", "Chart"),
            xlabel=d.get("xlabel", ""),
            ylabel=d.get("ylabel", ""),
            sort=d.get("sort"),
            limit=d.get("limit"),
        )

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "title": self.title,
            "xlabel": self.xlabel,
            "ylabel": self.ylabel,
            "sort": self.sort,
            "limit": self.limit,
        }