"""Run seeded retrieval ablations on reviewed, answerable gold questions only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import random
from collections.abc import Callable, Iterator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from filelock import FileLock

from LegalRag.query_analyser import Analyser, LegalQueryAnalysis
from eval.models import GoldItem
from eval.sample import provision_root
from eval.storage import atomic_text, load_gold
from legora.config import EvaluationSettings

if TYPE_CHECKING:
    from retrieval.hybrid_retrieval import HybridRetriever


@dataclass(frozen=True)
class Configuration:
    """One engine's feature switches; A–F are cumulative presets."""

    name: str
    act_filter: bool = False
    multi_query: bool = False
    rerank: bool = False
    legal_boost: bool = False
    graph: bool = False


CONFIGURATIONS = {
    "A": Configuration("A"),
    "B": Configuration("B", act_filter=True),
    "C": Configuration("C", act_filter=True, multi_query=True),
    "D": Configuration("D", act_filter=True, multi_query=True, rerank=True),
    "E": Configuration("E", act_filter=True, multi_query=True, rerank=True, legal_boost=True),
    "F": Configuration("F", act_filter=True, multi_query=True, rerank=True, legal_boost=True, graph=True),
}
METRICS = ("recall_at_1", "recall_at_5", "recall_at_10", "mrr", "ndcg_at_10", "context_recall", "combined_context_recall")


def eligible_gold(path: Path) -> list[GoldItem]:
    """Exclude drafts and refusal questions before constructing any live clients."""
    return sorted((item for item in load_gold(path) if item.reviewed and item.answerable), key=lambda item: item.id)


def analysis_signature() -> str:
    """Invalidate cached analyses when the analyser prompt/code/schema changes."""
    source = Path(__file__).resolve().parents[1] / "LegalRag/query_analyser.py"
    return hashlib.sha256(source.read_bytes() + json.dumps(LegalQueryAnalysis.model_json_schema(), sort_keys=True).encode()).hexdigest()


class AnalysisCache:
    """Freeze query-only LLM analysis by query, model, seed, and analyser signature."""

    def __init__(
        self, directory: Path, model: str, seed: int, analyse: Callable[[str], LegalQueryAnalysis],
        offline: bool = False, refresh: bool = False,
    ) -> None:
        """Keep credentials and gold act/support labels out of cache keys and prompts."""
        self.directory, self.model, self.seed = directory, model, seed
        self.analyse, self.offline, self.refresh = analyse, offline, refresh
        self.signature = analysis_signature()
        self.memory: dict[str, LegalQueryAnalysis] = {}
        self.hits = self.misses = 0

    def get(self, question: str) -> LegalQueryAnalysis:
        """Validate disk hits; fail on corrupt/missing offline data instead of inventing analysis."""
        key = {"question": question, "model": self.model, "seed": self.seed, "signature": self.signature}
        digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
        if digest in self.memory:
            self.hits += 1
            return self.memory[digest]
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{digest}.json"
        with FileLock(str(path) + ".lock", timeout=30):
            if path.exists() and not self.refresh:
                cached = json.loads(path.read_text(encoding="utf-8"))
                if cached["key"] != key:
                    raise ValueError("Analysis cache key mismatch")
                analysis = LegalQueryAnalysis.model_validate(cached["analysis"])
                self.hits += 1
            else:
                if self.offline:
                    raise ValueError("Analysis cache miss in --offline-analysis mode")
                analysis = LegalQueryAnalysis.model_validate(self.analyse(question))
                atomic_text(path, json.dumps({"key": key, "analysis": analysis.model_dump()}, ensure_ascii=False, sort_keys=True) + "\n")
                self.misses += 1
        self.memory[digest] = analysis
        return analysis


def seed_everything(seed: int) -> None:
    """Seed Python, NumPy, Torch, CUDA and require deterministic Torch operations."""
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def graph_node_ids(value: object) -> set[str]:
    """Read actual node/record ID properties, never IDs mentioned only in legal text or map keys."""
    found: set[str] = set()
    if hasattr(value, "nodes"):
        for node in value.nodes:
            found.update(graph_node_ids(node))
    elif isinstance(value, Mapping):
        for key, child in value.items():
            if key in {"id", "chunk_id"} and isinstance(child, str):
                found.add(child)
            elif not isinstance(child, str):
                found.update(graph_node_ids(child))
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            found.update(graph_node_ids(child))
    return found


def run_configuration(
    question: str, configuration: Configuration, retriever: HybridRetriever,
    cache: AnalysisCache, candidates: int,
) -> dict[str, Any]:
    """Run one shared retrieval path; switches control analysis/filter/expansion/scoring/graph."""
    analysis = cache.get(question) if configuration.act_filter or configuration.multi_query or configuration.rerank else None
    document = retriever.get_document_filter(analysis) if configuration.act_filter else None
    queries = [question]
    if configuration.multi_query:
        queries.extend(retriever.build_retrieval_queries(analysis))
    seen = set()
    unique_queries = []
    for query in queries:
        key = " ".join(query.casefold().split())
        if key and key not in seen:
            seen.add(key)
            unique_queries.append(query)
    points = []
    for query in unique_queries:
        points.extend(retriever.vector_search_filtered(query, document=document, k=candidates))
    # Same merged budget for every configuration, and an explicit tie breaker.
    points = sorted(retriever.dedupe_points(points), key=lambda point: (-float(point.score), point.payload["chunk_id"]))[:candidates]
    if configuration.rerank:
        points = retriever.reranker.rerank(
            query=question, points=points, top_k=candidates, analysis=analysis,
            apply_legal_boost=configuration.legal_boost,
        )
    ranked = [point.payload["chunk_id"] for point in points]
    graph_ids = None
    if configuration.graph:
        roots = sorted(retriever.extract_ids(points[:10]))
        graph_ids = sorted(graph_node_ids(retriever.expand_graph(roots)))
    return {"ranked_ids": ranked, "graph_ids": graph_ids, "candidate_count": len(points), "query_count": len(unique_queries)}


def target_groups(item: GoldItem, match: str) -> list[set[str]]:
    """Collapse root targets, allowing flat alternates only for a single expected provision."""
    if match not in {"exact", "root"}:
        raise ValueError("Match mode must be exact or root")
    def normalize(identifier: str) -> str:
        """Unknown formats remain literal instead of receiving a guessed legal identity."""
        return (provision_root(identifier) or identifier) if match == "root" else identifier

    groups = [set([normalize(item.expected_chunk_ids[0]), *(normalize(value) for value in item.acceptable_alternates)])] if len(item.expected_chunk_ids) == 1 else [{normalize(value)} for value in item.expected_chunk_ids]
    return [set(group) for group in sorted({tuple(sorted(group)) for group in groups})]


def ranking_metrics(item: GoldItem, ranked_ids: list[str], match: str, graph_ids: list[str] | None = None) -> dict[str, float | None]:
    """Compute fraction-of-target recall, reciprocal rank, and binary nDCG without duplicate credit."""
    groups = target_groups(item, match)
    normalized = [(provision_root(value) or value) if match == "root" else value for value in ranked_ids]
    matched = set()
    positions = []
    for rank, identifier in enumerate(normalized, 1):
        for index, group in enumerate(groups):
            if index not in matched and identifier in group:
                matched.add(index)
                positions.append(rank)
                break
    count = len(groups)
    values = {f"recall_at_{k}": sum(rank <= k for rank in positions) / count for k in (1, 5, 10)}
    values["mrr"] = 1 / min(positions) if positions else 0.0
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(count, 10) + 1))
    values["ndcg_at_10"] = sum(1 / math.log2(rank + 1) for rank in positions if rank <= 10) / ideal
    values["context_recall"] = values["combined_context_recall"] = None
    if graph_ids is not None:
        graph = {(provision_root(value) or value) if match == "root" else value for value in graph_ids}
        values["context_recall"] = sum(bool(group & graph) for group in groups) / count
        combined = graph | set(normalized[:10])
        values["combined_context_recall"] = sum(bool(group & combined) for group in groups) / count
    return values


def bootstrap_mean(values: list[float], seed: int, samples: int) -> tuple[float, float, float]:
    """Return the macro mean and query-level percentile bootstrap 95% interval."""
    data = np.asarray(values, dtype=float)
    if not len(data):
        raise ValueError("Cannot bootstrap an empty category")
    indices = np.random.default_rng(seed).integers(0, len(data), size=(samples, len(data)))
    low, high = np.quantile(data[indices].mean(axis=1), [0.025, 0.975])
    return float(data.mean()), float(low), float(high)


def aggregate(rows: list[dict], seed: int, samples: int, by_intent: bool = False) -> list[dict]:
    """Use identical seeded resample indices for equal-size configuration/match groups."""
    keys = sorted({(row["configuration"], row["match"], row["intent"] if by_intent else "all") for row in rows})
    summaries = []
    for configuration, match, intent in keys:
        group = sorted((row for row in rows if row["configuration"] == configuration and row["match"] == match and (not by_intent or row["intent"] == intent)), key=lambda row: row["id"])
        summary = {"configuration": configuration, "match": match, "intent": intent, "n": len(group)}
        for metric in METRICS:
            values = [row[metric] for row in group if row[metric] is not None]
            mean, low, high = bootstrap_mean(values, seed, samples) if values else (None, None, None)
            summary.update({metric: mean, metric + "_ci_low": low, metric + "_ci_high": high})
        summaries.append(summary)
    return summaries


def csv_report(summaries: list[dict]) -> str:
    """Write machine-readable point estimates and separate interval bounds."""
    buffer = io.StringIO(newline="")
    fields = ["configuration", "match", "intent", "n"] + [name for metric in METRICS for name in (metric, metric + "_ci_low", metric + "_ci_high")]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(summaries)
    return buffer.getvalue()


def markdown_table(summaries: list[dict]) -> str:
    """Present estimates with their intervals; a dash means graph was not evaluated."""
    lines = ["| Config | Match | Intent | n | Recall@1 | Recall@5 | Recall@10 | MRR | nDCG@10 | Graph context recall | Combined context recall |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summaries:
        cells = [str(row[name]) for name in ("configuration", "match", "intent", "n")]
        for metric in METRICS:
            value = row[metric]
            cells.append("—" if value is None else f"{value:.3f} [{row[metric + '_ci_low']:.3f}, {row[metric + '_ci_high']:.3f}]")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def worst_failures(rows: list[dict], details: list[dict], limit: int = 10) -> list[dict]:
    """Rank the worst query/configuration pairs by root recall/nDCG, then exact scores."""
    scores = {(row["configuration"], row["id"], row["match"]): row for row in rows}
    candidates = []
    for detail in details:
        root = scores[(detail["configuration"], detail["id"], "root")]
        exact = scores[(detail["configuration"], detail["id"], "exact")]
        if root["recall_at_10"] < 1 or exact["recall_at_10"] < 1 or root["ndcg_at_10"] < 1 or exact["ndcg_at_10"] < 1:
            candidates.append({**detail, "root_recall_at_10": root["recall_at_10"], "root_ndcg_at_10": root["ndcg_at_10"], "exact_recall_at_10": exact["recall_at_10"], "exact_ndcg_at_10": exact["ndcg_at_10"]})
    return sorted(candidates, key=lambda row: (row["root_recall_at_10"], row["root_ndcg_at_10"], row["exact_recall_at_10"], row["exact_ndcg_at_10"], row["configuration"], row["id"]))[:limit]


def evaluate(
    gold: list[GoldItem], configurations: list[Configuration], retriever: HybridRetriever,
    cache: AnalysisCache, candidates: int,
) -> tuple[list[dict], list[dict]]:
    """Collect per-question observations without using gold labels to construct retrieval queries."""
    rows, details = [], []
    eligible = sorted((item for item in gold if item.reviewed and item.answerable), key=lambda item: item.id)
    for item in eligible:
        for configuration in configurations:
            outcome = run_configuration(item.question, configuration, retriever, cache, candidates)
            for match in ("exact", "root"):
                rows.append({"configuration": configuration.name, "id": item.id, "intent": item.intent, "match": match, **ranking_metrics(item, outcome["ranked_ids"], match, outcome["graph_ids"])})
            details.append({"configuration": configuration.name, "id": item.id, "intent": item.intent, "question": item.question, "expected_chunk_ids": item.expected_chunk_ids, "acceptable_alternates": item.acceptable_alternates, **outcome})
            print(f"Evaluated {item.id}: {configuration.name}", flush=True)
    return rows, details


@contextmanager
def live_retriever(
    configurations: list[Configuration], settings: EvaluationSettings,
    collection: str, embedder_model: str, reranker_model: str, exact_search: bool = True,
) -> Iterator[HybridRetriever]:
    """Load each needed model once and skip Gemini/Neo4j/reranker when not requested."""
    from db.embedder import LegalEmbedder
    from db.neo4j_store import Neo4jStore
    from db.vector_store import QdrantStore
    from retrieval.cross_encoder import LegalReranker
    from retrieval.hybrid_retrieval import HybridRetriever

    with ExitStack() as resources:
        retriever = HybridRetriever.__new__(HybridRetriever)
        if any(configuration.graph for configuration in configurations):
            retriever.graph = Neo4jStore(settings=settings)
            resources.callback(retriever.graph.close)
        retriever.vector_db = QdrantStore(collection_name=collection, settings=settings, exact_search=exact_search)
        resources.callback(retriever.vector_db.client.close)
        # Check connectivity before loading gigabytes of model weights.
        retriever.vector_db.client.get_collection(collection)
        retriever.embedder = LegalEmbedder(model_name=embedder_model)
        retriever.embedder.model.eval()
        if any(configuration.rerank for configuration in configurations):
            retriever.reranker = LegalReranker(model_name=reranker_model)
            retriever.reranker.model.model.eval()
        yield retriever


def write_reports(directory: Path, summaries: list[dict], intents: list[dict], failures: list[dict], details: list[dict], metadata: dict) -> str:
    """Publish actual results only after every query/configuration has completed."""
    atomic_text(directory / "retrieval_ablation.csv", csv_report(summaries))
    atomic_text(directory / "retrieval_ablation_by_intent.csv", csv_report(intents))
    atomic_text(directory / "retrieval_ablation_worst10.json", json.dumps(failures, indent=2, ensure_ascii=False) + "\n")
    atomic_text(directory / "retrieval_ablation_details.jsonl", "".join(json.dumps(detail, ensure_ascii=False) + "\n" for detail in details))
    atomic_text(directory / "retrieval_ablation_run.json", json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    report = "# Retrieval ablation\n\nValues are macro query means with percentile bootstrap 95% confidence intervals.\n\n"
    if metadata.get("configurations"):
        report += "| Config | Act filter | Multi-query | Rerank | Legal boost | Graph |\n|---|---|---|---|---|---|\n"
        for configuration in metadata["configurations"]:
            report += "| " + " | ".join(str(configuration[key]) for key in ("name", "act_filter", "multi_query", "rerank", "legal_boost", "graph")) + " |\n"
        report += "\n"
    report += markdown_table(summaries)
    report += "\n## Per-intent breakdown\n\n" + markdown_table(intents)
    report += "\n## Worst 10 query/configuration failures\n\n"
    for failure in failures:
        report += f"- **{failure['configuration']} / {failure['id']}** ({failure['intent']}): {failure['question']}\n"
        report += f"  Expected: `{json.dumps(failure['expected_chunk_ids'])}`; retrieved top 10: `{json.dumps(failure['ranked_ids'][:10])}`; root Recall@10={failure['root_recall_at_10']:.3f}, exact Recall@10={failure['exact_recall_at_10']:.3f}.\n"
    if not failures:
        report += "No imperfect Recall@10/nDCG@10 rankings in this evaluated sample.\n"
    atomic_text(directory / "retrieval_ablation.md", report)
    return report


def main() -> None:
    """Compare presets or override their feature flags without duplicating retrieval code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("eval/gold.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--configs", nargs="+", choices=CONFIGURATIONS, default=list(CONFIGURATIONS))
    for flag in ("act-filter", "multi-query", "rerank", "legal-boost", "graph"):
        parser.add_argument("--" + flag, action=argparse.BooleanOptionalAction, default=None, help="Override this feature in every selected preset")
    parser.add_argument("--candidates", type=int, default=50, help="Per-query and merged candidate budget, at least 10")
    parser.add_argument("--collection", default="legal_rag")
    parser.add_argument("--approximate-search", action="store_true", help="Use production ANN search instead of reproducible exact dense search")
    parser.add_argument("--embedder-model", default="BAAI/bge-large-en-v1.5")
    parser.add_argument("--reranker-model", default="BAAI/bge-reranker-large")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--analysis-cache", type=Path, default=Path("results/analysis_cache"))
    cache_mode = parser.add_mutually_exclusive_group()
    cache_mode.add_argument("--offline-analysis", action="store_true", help="Require cache hits; never call Gemini")
    cache_mode.add_argument("--refresh-analysis", action="store_true", help="Explicitly replace existing cached analyses")
    args = parser.parse_args()
    if args.candidates < 10 or args.bootstrap_samples < 1 or not 0 <= args.seed < 2**32:
        parser.error("Require candidates >= 10, bootstrap-samples >= 1, and a 32-bit unsigned seed")
    overrides = {name: getattr(args, name) for name in ("act_filter", "multi_query", "rerank", "legal_boost", "graph") if getattr(args, name) is not None}
    configurations = [Configuration(**{**asdict(CONFIGURATIONS[name]), **overrides}) for name in dict.fromkeys(args.configs)]
    if any(configuration.legal_boost and not configuration.rerank for configuration in configurations):
        parser.error("Legal boost requires --rerank; choose a reranking preset or disable legal boost")
    analyser = None
    try:
        gold = eligible_gold(args.gold)
        if not gold:
            # A header-only artifact explicitly means not run, never a zero-valued benchmark.
            args.output_dir.mkdir(parents=True, exist_ok=True)
            for filename, content in (
                ("retrieval_ablation.csv", csv_report([])),
                ("retrieval_ablation.md", "# Retrieval ablation — not run\n\nNo reviewed, answerable gold items are available. No retrieval scores or confidence intervals have been computed.\n"),
            ):
                path = args.output_dir / filename
                if not path.exists():
                    atomic_text(path, content)
            parser.exit(1, "Not run: no reviewed, answerable gold items. Review labels and restore the corpus first.\n")
        settings = EvaluationSettings()

        def analyse(question: str) -> LegalQueryAnalysis:
            """Construct Gemini only on the first uncached analysis request."""
            nonlocal analyser
            if analyser is None:
                analyser = Analyser(settings=settings)
            return analyser.analyze_query(question, seed=args.seed)

        cache = AnalysisCache(args.analysis_cache, settings.gemini_model, args.seed, analyse, args.offline_analysis, args.refresh_analysis)
        seed_everything(args.seed)
        with live_retriever(configurations, settings, args.collection, args.embedder_model, args.reranker_model, not args.approximate_search) as retriever:
            rows, details = evaluate(gold, configurations, retriever, cache, args.candidates)
            embedding_config = getattr(getattr(retriever.embedder.model[0], "auto_model", None), "config", None)
            model_revisions = {"embedder": getattr(embedding_config, "_commit_hash", None)}
            if any(configuration.rerank for configuration in configurations):
                model_revisions["reranker"] = getattr(retriever.reranker.model.model.config, "_commit_hash", None)
        metadata = {
            "status": "completed", "eligible_questions": len(gold), "gold_sha256": hashlib.sha256(args.gold.read_bytes()).hexdigest(),
            "seed": args.seed, "bootstrap_samples": args.bootstrap_samples, "confidence_level": 0.95,
            "bootstrap_unit": "query", "interval_method": "percentile", "candidate_budget": args.candidates,
            "mrr_depth": args.candidates, "graph_seed_depth": 10, "collection": args.collection,
            "exact_dense_search": not args.approximate_search, "model_revisions": model_revisions,
            "embedder_model": args.embedder_model, "reranker_model": args.reranker_model,
            "analysis_model": settings.gemini_model, "analysis_signature": cache.signature,
            "analysis_cache_hits": cache.hits, "analysis_cache_misses": cache.misses,
            "configurations": [asdict(configuration) for configuration in configurations],
            "packages": {name: version(name) for name in ("torch", "sentence-transformers", "qdrant-client", "google-genai", "numpy")},
        }
        report = write_reports(args.output_dir, aggregate(rows, args.seed, args.bootstrap_samples), aggregate(rows, args.seed, args.bootstrap_samples, by_intent=True), worst_failures(rows, details), details, metadata)
        print(report)
    except Exception as error:
        parser.exit(1, f"Evaluation failed ({type(error).__name__}); check corpus availability, configuration, and analysis cache.\n")
    finally:
        if analyser is not None:
            analyser.client.close()


if __name__ == "__main__":
    main()
