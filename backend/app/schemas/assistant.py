from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssistantQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AssistantPeriod(BaseModel):
    start_date: date
    end_date: date


class AssistantEvidence(BaseModel):
    tool_name: str
    period: AssistantPeriod | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class AssistantSource(BaseModel):
    document_id: str
    document_name: str
    page_number: int | None = None
    chunk_id: str
    chunk_index: int


class AssistantQueryResponse(BaseModel):
    answer: str
    data: dict[str, Any]
    tools_used: list[str]
    period: AssistantPeriod | None = None
    warnings: list[str]
    evidence: list[AssistantEvidence]
    sources: list[AssistantSource] = Field(default_factory=list)


class FinancialToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class FinancialToolResult(BaseModel):
    name: str
    arguments: dict[str, Any]
    data: dict[str, Any]
    period: AssistantPeriod | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
