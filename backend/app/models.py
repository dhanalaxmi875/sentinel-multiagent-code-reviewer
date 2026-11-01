from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReviewStatus = Literal["queued", "running", "done", "failed"]
Verdict = Literal["APPROVE", "REQUEST_CHANGES"]
AgentStatus = Literal["idle", "running", "done", "skipped", "failed"]
Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
Confidence = Literal["HIGH", "MEDIUM", "LOW"]
FindingStatus = Literal["kept", "rejected"]


class CreateReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diff_text: str
    file_paths: list[str] = Field(default_factory=list)
    source: str = "web"
    force: bool = False

    @field_validator("file_paths")
    @classmethod
    def normalize_file_paths(cls, value: list[str]) -> list[str]:
        return [path.strip() for path in value if path.strip()]


class CreateReviewResponse(BaseModel):
    id: str
    status: ReviewStatus


class FindingResponse(BaseModel):
    id: str
    title: str
    severity: Severity
    confidence: Confidence
    cwe: str
    file: str
    line: int
    evidence: str
    fix: str
    sources: list[str]
    status: FindingStatus
    rejection_reason: str | None = None


class AgentResponse(BaseModel):
    agent: str
    status: AgentStatus
    duration_s: float
    finding_count: int


class LogResponse(BaseModel):
    ts: datetime
    level: str
    message: str


class ReviewResponse(BaseModel):
    id: str
    status: ReviewStatus
    verdict: Verdict | None = None
    duration_s: float | None = None
    error: str | None = None
    report_md: str | None = None
    diff_text: str
    agents: list[AgentResponse]
    findings: list[FindingResponse]
    logs: list[LogResponse]
    is_demo: bool = False
    is_replay: bool = False
    created_at: datetime
    finished_at: datetime | None = None


class ReviewSummary(BaseModel):
    id: str
    status: ReviewStatus
    verdict: Verdict | None = None
    finding_counts: dict[Literal["critical", "high", "medium", "low"], int]
    created_at: datetime
    duration_s: float | None = None


class StatsResponse(BaseModel):
    total_reviews: int
    finding_counts: dict[Literal["critical", "high", "medium", "low"], int]
    verdict_split: dict[Literal["approve", "request_changes"], int]
    avg_review_time_s: float


class SampleResponse(BaseModel):
    id: str
    name: str
    description: str
    diff_text: str
    file_paths: list[str] = Field(default_factory=list)
