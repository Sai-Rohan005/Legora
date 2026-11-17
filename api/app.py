"""FastAPI service; launch with uvicorn api.app:app."""

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from threading import Lock
from time import perf_counter
from typing import Any, Protocol

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.models import (
    Citation, DependencyStatus, HealthResponse, QueryRequest, QueryResponse,
)
from LegalRag.citation_check import CitationReport, check_citations
from legora.config import Settings, get_settings
from legora.logging import setup_logging

logger = logging.getLogger(__name__)


class Pipeline(Protocol):
    """The small lifecycle/query interface needed by the HTTP layer."""

    retriever: Any
    llm: Any

    def search(
        self, query: str, top_k: int | None = None,
        include_graph: bool = True, include_judgments: bool = True
    ) -> dict:
        """Return a pipeline result with measured timings."""
        ...

    def close(self) -> None:
        """Close the resources owned by this pipeline."""
        ...


def load_pipeline() -> Pipeline:
    """Import and construct heavyweight components only during lifespan startup."""
    from LegalRag.rag_pipeline import RAGPipeline

    return RAGPipeline()


def query_response(result: dict) -> QueryResponse:
    """Expose source identifiers and scalar diagnostics without raw graph objects."""
    retrieval = result["retrieval"]
    citations = []
    for point in retrieval["statutory_results"]:
        payload = point.payload or {}
        if payload.get("chunk_id"):
            citations.append(Citation(
                source="statute", id=str(payload["chunk_id"]),
                title=payload.get("title") or payload.get("document"),
            ))
    for judgment in retrieval["judgments"]:
        identifier = judgment.get("tid") or judgment.get("id")
        if identifier is not None:
            citations.append(Citation(
                source="judgment", id=str(identifier), title=judgment.get("title"),
                url=f"https://indiankanoon.org/doc/{identifier}/" if str(identifier).isdigit() else None,
            ))
    evaluation = result["evaluation"]
    citation_check = CitationReport.model_validate(result["citation_check"]) if "citation_check" in result else check_citations(result["answer"], retrieval)
    return QueryResponse(
        answer=result["answer"], citations=citations,
        unsupported_citations=citation_check.unsupported_citations,
        citation_precision=citation_check.citation_precision,
        citation_checks=citation_check.citations,
        retrieval_debug={
            "vector_hits": len(retrieval["vector_results"]),
            "reranked": len(retrieval["statutory_results"]),
            "node_ids": retrieval["node_ids"],
        },
        evaluation={
            "score": evaluation.get("overall_score", 0),
            "stage": evaluation.get("failure_stage"),
        },
        attempts=result["attempts"], latency_ms=result["latency_ms"],
    )


def dependency_checks(pipeline: Pipeline) -> dict[str, Callable[[], object]]:
    """Probe existing clients without loading models or generating billable text."""
    return {
        "qdrant": pipeline.retriever.hybrid.vector_db.client.get_collections,
        "neo4j": lambda: pipeline.retriever.hybrid.graph.run_query("RETURN 1 AS ok"),
        "gemini": lambda: pipeline.llm.client.models.get(model=pipeline.llm.model),
    }


def create_app(
    pipeline_factory: Callable[[], Pipeline] = load_pipeline,
    settings: Settings | None = None,
    checks_factory: Callable[[Pipeline], dict[str, Callable[[], object]]] = dependency_checks,
) -> FastAPI:
    """Build an app with injectable services for tests and one pipeline per worker."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Load the models once, then close clients when this worker shuts down."""
        configuration = settings or get_settings()
        setup_logging(configuration.log_level)
        pipeline = await anyio.to_thread.run_sync(pipeline_factory)
        application.state.pipeline = pipeline
        application.state.settings = configuration
        application.state.query_lock = Lock()
        try:
            yield
        finally:
            await anyio.to_thread.run_sync(pipeline.close)

    application = FastAPI(title="Legora", lifespan=lifespan, debug=False)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        """Return field locations and error types without reflecting user input."""
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": item["loc"], "type": item["type"]} for item in error.errors()
        ]})

    @application.post("/query", response_model=QueryResponse)
    def query(body: QueryRequest, request: Request) -> QueryResponse:
        """Serialize access to mutable pipeline state and map failures safely."""
        lock = request.app.state.query_lock
        acquired = lock.acquire(timeout=request.app.state.settings.query_lock_timeout_seconds)
        if not acquired:
            raise HTTPException(status_code=502, detail="Query service is busy; retry later.")
        try:
            result = request.app.state.pipeline.search(
                body.query, top_k=body.top_k,
                include_graph=body.include_graph, include_judgments=body.include_judgments,
            )
            return query_response(result)
        except Exception as error:
            logger.error("Query failed", extra={"error_type": type(error).__name__})
            raise HTTPException(status_code=502, detail="Unable to complete query due to a backend failure.") from None
        finally:
            lock.release()

    @application.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> JSONResponse:
        """Check all dependencies concurrently, with a deadline for every probe."""
        statuses: dict[str, DependencyStatus] = {}

        async def probe(name: str, check: Callable[[], object]) -> None:
            """Bound one probe and retain its status even if another fails."""
            started = perf_counter()
            status = "ok"
            try:
                with anyio.fail_after(request.app.state.settings.external_timeout_seconds):
                    await anyio.to_thread.run_sync(check, abandon_on_cancel=True)
            except TimeoutError:
                status = "timeout"
            except Exception:
                status = "error"
            statuses[name] = DependencyStatus(
                status=status, latency_ms=round((perf_counter() - started) * 1000, 3)
            )

        async with anyio.create_task_group() as group:
            for name, check in checks_factory(request.app.state.pipeline).items():
                group.start_soon(probe, name, check)
        healthy = all(item.status == "ok" for item in statuses.values())
        response = HealthResponse(status="ok" if healthy else "degraded", dependencies=statuses)
        return JSONResponse(status_code=200 if healthy else 502, content=response.model_dump())

    return application


app = create_app()
