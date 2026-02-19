from typing import Any, Optional, List, Dict
from pydantic import BaseModel


class StepResult(BaseModel):
    step_number: int
    step_description: str
    step_type: str
    type: str
    data: Any
    columns: Optional[List[str]] = None
    total_rows: Optional[int] = None
    description: Optional[str] = None
    mime: Optional[str] = None
    query: Optional[str] = None
    detailed_description: Optional[str] = None
    error: Optional[str] = None


class PlanStep(BaseModel):
    step_number: int
    type: str
    title: str
    description: str
    chart_type: str
    detailed_description: Optional[str] = None


class FinalResultData(BaseModel):
    text: str
    steps: List[Dict[str, Any]]
    plan: Optional[Dict[str, Any]] = None
    code: Optional[str] = None


class FinalResult(BaseModel):
    type: str = "final_result"
    data: FinalResultData


class StepStart(BaseModel):
    type: str = "step_start"
    step_number: int
    description: str
    step_type: Optional[str] = None
    detailed_description: Optional[str] = None


class StepResultResponse(BaseModel):
    type: str = "step_result"
    data: StepResult
