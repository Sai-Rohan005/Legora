"""Public request and response contracts, independent of model libraries."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from LegalRag.citation_check import CheckedCitation


class QueryRequest(BaseModel):
    """A legal question and optional retrieval controls."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    query: str = Field(min_length=1, max_length=20000)
    top_k: int | None = Field(default=None, ge=1, le=100)
    include_graph: bool = True
    include_judgments: bool = True


class Citation(BaseModel):
    """A retained statutory chunk or fetched judgment, never an invented source."""

    source: Literal["statute", "judgment"]
    id: str
    title: str | None = None
    url: str | None = None


class RetrievalDebug(BaseModel):
    """Counts and root IDs from the final retrieval attempt."""

    vector_hits: int = Field(ge=0)
    reranked: int = Field(ge=0)
    node_ids: list[str]


class Evaluation(BaseModel):
    """The evaluator's score and reported failure stage, if any."""

    score: float = Field(ge=0, le=100)
    stage: str | None


class LatencyMs(BaseModel):
    """Measured stage durations summed across attempts; skipped stages take zero."""

    analysis: float = Field(ge=0)
    retrieval: float = Field(ge=0)
    rerank: float = Field(ge=0)
    graph: float = Field(ge=0)
    generation: float = Field(ge=0)
    judge: float = Field(ge=0)


class QueryResponse(BaseModel):
    """A JSON-safe answer with provenance and diagnostics."""

    answer: str
    unsupported_citations: list[str] = Field(default_factory=list)
    citation_precision: float | None = Field(default=None, ge=0, le=1)
    citation_checks: list[CheckedCitation] = Field(default_factory=list)
    citations: list[Citation]
    retrieval_debug: RetrievalDebug
    evaluation: Evaluation
    attempts: int = Field(ge=1)
    latency_ms: LatencyMs


class DependencyStatus(BaseModel):
    """A bounded connectivity probe without credentials or exception details."""

    status: Literal["ok", "error", "timeout"]
    latency_ms: float = Field(ge=0)


class HealthResponse(BaseModel):
    """Reachability of every required backend dependency."""

    status: Literal["ok", "degraded"]
    dependencies: dict[str, DependencyStatus]
