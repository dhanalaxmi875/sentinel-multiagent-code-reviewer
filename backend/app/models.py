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


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if email.count("@") != 1 or any(char.isspace() for char in email):
            raise ValueError("Enter a valid email address.")
        local, _, domain = email.partition("@")
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Enter a valid email address.")
        return email


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime


class CreateReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diff_text: str
    file_paths: list[str] = Field(default_factory=list)
    source: str = "web"
    force: bool = False

    @field_validator("file_paths", mode="before")
    @classmethod
    def normalize_file_paths(cls, value: list[str] | None) -> list[str]:
        if not value:
            return []
        return [path.strip() for path in value if path and path.strip()]


class CreateReviewResponse(BaseModel):
    id: str
    status: ReviewStatus


class FindingResponse(BaseModel):
    id: str
    title: str
    severity: Severity
    confidence: Confidence
    cwe: str | None = None
    file: str | None = None
    line: int | None = None
    evidence: str | None = None
    fix: str | None = None
    sources: list[str] = Field(default_factory=list)
    status: FindingStatus
    rejection_reason: str | None = None


class AgentResponse(BaseModel):
    agent: str
    status: AgentStatus
    duration_s: float | None = None
    finding_count: int | None = None


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
