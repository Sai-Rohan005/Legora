"""Measure paired baseline/optimized latency and quality on reviewed gold questions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from LegalRag.citation_check import check_citations, root_id
from eval.judge_validation import sample_questions
from eval.models import GoldItem
from eval.run_answer_eval import load_pipeline
from eval.storage import atomic_text, load_gold

STAGES = ("analysis", "embedding", "vector_search", "rerank", "neo4j", "generation", "judge", "total")


def percentile(values: list[float], probability: float) -> float:
    """Compute a linearly interpolated empirical percentile with explicit sample count."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot profile an empty sample")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def provision_recall(item: GoldItem, result: dict) -> float | None:
    """Recall@5 on retained reranked root provisions; unanswerable rows are excluded."""
    if not item.answerable:
        return None
    retained = result["retrieval"].get("statutory_results", [])[:5]
    retrieved = {root_id((point.payload if hasattr(point, "payload") else point)["chunk_id"]) for point in retained}
    expected = {root_id(identifier) for identifier in item.expected_chunk_ids}
    if len(item.expected_chunk_ids) == 1:
        return float(bool(retrieved & (expected | {root_id(identifier) for identifier in item.acceptable_alternates})))
    return len(retrieved & expected) / len(expected)


def configure(pipeline: Any, optimized: bool, workers: int, clear: bool) -> None:
    """Switch one implementation without copying retrieval logic or reloading heavy models."""
    hybrid = pipeline.retriever.hybrid
    hybrid.vector_search_workers = workers if optimized else 1
    hybrid.batch_graph_expansion = optimized
    for owner in (hybrid.analyser, hybrid.embedder):
        owner.query_cache.enabled = optimized
        if clear:
            owner.query_cache.clear()


def run_profiles(items: list[GoldItem], pipeline: Any, workers: int = 4) -> list[dict]:
    """Pair all questions across baseline, optimized cold-start, then optimized warm-cache."""
    rows = []
    for mode in ("before", "after_cold", "after_warm"):
        configure(pipeline, mode != "before", workers, clear=mode != "after_warm")
        for item in items:
            started = perf_counter()
            result = pipeline.search(item.question)
            elapsed = (perf_counter() - started) * 1000
            check = check_citations(result["answer"], result["retrieval"])
            stages = result["stage_latency_ms"]
            if any(stage not in stages for stage in STAGES[:-1]):
                raise ValueError("Pipeline result is missing stage measurements")
            rows.append({
                "id": item.id, "mode": mode, "latency_ms": {**stages, "total": elapsed},
                "recall_at_5": provision_recall(item, result),
                "supported_citations": check.supported_count, "total_citations": check.total_citations,
                "attempts": result["attempts"],
            })
    return rows


def quality(rows: list[dict]) -> dict:
    """Use answerable-only macro recall and occurrence-weighted citation precision."""
    recalls = [row["recall_at_5"] for row in rows if row["recall_at_5"] is not None]
    citations = sum(row["total_citations"] for row in rows)
    return {"recall_at_5": sum(recalls) / len(recalls) if recalls else None,
            "citation_precision": sum(row["supported_citations"] for row in rows) / citations if citations else None}


def render_report(rows: list[dict], count: int, seed: int, startup_ms: float) -> str:
    """Document measured deltas and refuse to recommend unproven/regressing configurations."""
    modes = ("before", "after_cold", "after_warm")
    groups = {mode: [row for row in rows if row["mode"] == mode] for mode in modes}
    if any(len(group) != count or len({row["id"] for row in group}) != count for group in groups.values()):
        raise ValueError("Each profile mode must cover the same complete sample")
    if any({row["id"] for row in groups[mode]} != {row["id"] for row in groups["before"]} for mode in modes):
        raise ValueError("Profile modes must use matched question IDs")
    report = (f"# Pipeline latency\n\n{count} reviewed gold questions per mode; sampling seed {seed}. "
              f"One model startup excluded from query timings: {startup_ms:.2f} ms. "
              "Stage durations sum all attempts for each question. Vector-search time excludes embedding. "
              "Total also includes judgments, citation checking, retries and other overhead.\n\n"
              "| Stage | Before p50 ms | Before p95 ms | After cold p50 ms | After cold p95 ms | After warm p50 ms | After warm p95 ms |\n"
              "|---|---:|---:|---:|---:|---:|---:|\n")
    for stage in STAGES:
        values = [percentile([row["latency_ms"][stage] for row in groups[mode]], probability) for mode in modes for probability in (.5, .95)]
        report += f"| {stage} | " + " | ".join(f"{value:.2f}" for value in values) + " |\n"
    report += "\n| Mode | Root Recall@5 | Citation precision | Quality gate |\n|---|---:|---:|---|\n"
    baseline = quality(groups["before"])
    for mode in modes:
        metrics = quality(groups[mode])
        regression = [key for key in metrics if metrics[key] is not None and baseline[key] is not None and metrics[key] < baseline[key]]
        missing = any(value is None for value in metrics.values()) or any(value is None for value in baseline.values())
        gate = "REGRESSION: " + ", ".join(regression) if regression else "UNPROVEN: undefined metric" if missing else "No observed loss"
        report += f"| {mode} | " + " | ".join("Undefined" if value is None else f"{value:.4f}" for value in metrics.values()) + f" | {gate} |\n"
    report += ("\nBefore: serial searches, per-root graph calls, caches off. After: concurrent vector I/O, one graph query, bounded analysis/embedding LRU caches. "
               "Cold-start clears caches once before the batch, which then fills them; warm repeats the same questions with retained caches. "
               "All modes use identical per-call SDK timeouts and transient-error backoff; this is an in-process switch comparison, not a historical binary comparison. "
               "Generation remains stochastic. Shared database/server caches, fixed mode order and repeated questions can affect differences. "
               "Freeze the corpus/models and inspect per-query rows before drawing conclusions; absence of observed loss does not establish statistical equivalence.\n\n"
               "Judge skipping: NOT MEASURED and disabled. The flag fails closed until reviewed no-quality-loss evidence exists. "
               "Performance flags remain off by default; regressions above are not accepted as speedups.\n")
    return report


def main() -> None:
    """Gate reviewed data before startup, then persist only complete paired measurements."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("eval/gold.jsonl"))
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=4, choices=range(2, 17))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    pipeline = None
    try:
        items = sample_questions(load_gold(args.gold), args.count, args.seed)
        started = perf_counter()
        pipeline = load_pipeline()
        startup_ms = (perf_counter() - started) * 1000
        rows = run_profiles(items, pipeline, args.workers)
        report = render_report(rows, args.count, args.seed, startup_ms)
        measured = {"gold_sha256": hashlib.sha256(args.gold.read_bytes()).hexdigest(),
                    "seed": args.seed, "workers": args.workers, "startup_ms": startup_ms, "rows": rows}
        atomic_text(args.output_dir / "latency.json", json.dumps(measured, indent=2) + "\n")
        atomic_text(args.output_dir / "latency.md", report)
        print(report)
    except Exception as error:
        path = args.output_dir / "latency.md"
        if not path.exists():
            atomic_text(path, "# Pipeline latency — not run\n\nNo paired measurements or quality claims. Requires 50 reviewed gold questions and restored Qdrant/Neo4j corpus. "
                        "Before/after p50/p95, Recall@5, citation precision and judge-skip quality remain unmeasured. Performance flags and judge skipping remain disabled by default.\n")
        message = str(error) if type(error) is ValueError and pipeline is None else type(error).__name__
        parser.exit(1, f"Profiling failed: {message}. No incomplete sample was scored.\n")
    finally:
        if pipeline is not None:
            pipeline.close()


if __name__ == "__main__":
    main()
