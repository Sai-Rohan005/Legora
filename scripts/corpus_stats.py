"""Measure stored corpus counts without loading models or fabricating unavailable totals."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Any

from eval.storage import atomic_text
from legora.config import EvaluationSettings
from legora.performance import call_external
from retrieval.lexical import document_name

ACTS = ("BNS", "BNSS", "BSA", "Constitution", "Unmapped")


def act_name(value: object) -> str:
    """Map stored act metadata to report rows, preserving unknown data in its own row."""
    return {"BNS": "BNS", "BNSS": "BNSS", "BSA": "BSA", "CONST": "Constitution",
            "CONSTITUTION": "Constitution"}.get(str(value).strip().upper(), "Unmapped")


def vector_counts(client: Any, collection: str) -> dict:
    """Scroll all stored points; count distinct chunk IDs and expose duplicate/missing IDs."""
    buckets: dict[str, set[str]] = {act: set() for act in ACTS}
    owners: dict[str, str] = {}
    points = missing = 0
    offset = None
    while True:
        records, offset = call_external(
            client.scroll, collection_name=collection, offset=offset, limit=256,
            with_payload=True, with_vectors=False,
        )
        for record in records:
            points += 1
            payload = record.payload or {}
            identifier = payload.get("chunk_id")
            if not isinstance(identifier, str) or not identifier.strip():
                missing += 1
                continue
            act = act_name(document_name(payload))
            if identifier in owners and owners[identifier] != act:
                raise ValueError("Conflicting act metadata for a stored chunk ID")
            owners[identifier] = act
            buckets[act].add(identifier)
        if offset is None:
            break
    return {"chunks_by_act": {act: len(values) for act, values in buckets.items()},
            "stored_points": points, "unique_chunks": len(owners),
            "points_without_chunk_id": missing, "duplicate_chunk_points": points - missing - len(owners)}


def graph_counts(graph: Any) -> dict:
    """Count all stored nodes and directed edges, assigning each edge to its source act."""
    results = {}
    for field, query in (
        ("nodes_by_act", "MATCH (n) RETURN n.document AS document, count(n) AS count"),
        ("edges_by_act", "MATCH (a)-[r]->() RETURN a.document AS document, count(r) AS count"),
    ):
        counts = dict.fromkeys(ACTS, 0)
        for row in graph.run_query(query):
            count = row["count"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("Invalid graph count")
            counts[act_name(row["document"])] += count
        results[field] = counts
    return results


def collect_stats(
    vector_factory: Callable[[], Any], graph_factory: Callable[[], Any], collection: str,
) -> dict:
    """Measure dependencies independently; failures produce null counts, never zero estimates."""
    dependencies = {}
    for name, factory, measure, close in (
        ("qdrant", vector_factory, lambda client: vector_counts(client, collection), lambda client: client.close()),
        ("neo4j", graph_factory, graph_counts, lambda graph: graph.close()),
    ):
        resource = None
        try:
            resource = factory()
            dependencies[name] = {"status": "ok", **measure(resource)}
        except Exception as error:
            dependencies[name] = {"status": "unavailable", "error_type": type(error).__name__}
        finally:
            if resource is not None:
                try:
                    close(resource)
                except Exception as error:
                    dependencies[name]["close_error_type"] = type(error).__name__
    available = sum(dependency["status"] == "ok" for dependency in dependencies.values())
    rows = [{"act": act,
             "chunks": dependencies["qdrant"].get("chunks_by_act", {}).get(act),
             "graph_nodes": dependencies["neo4j"].get("nodes_by_act", {}).get(act),
             "graph_edges": dependencies["neo4j"].get("edges_by_act", {}).get(act)} for act in ACTS]
    totals = {key: sum(row[key] for row in rows) if all(row[key] is not None for row in rows) else None
              for key in ("chunks", "graph_nodes", "graph_edges")}
    return {"measured_at_utc": datetime.now(timezone.utc).isoformat(), "collection": collection,
            "status": "completed" if available == 2 else "partial" if available else "unavailable",
            "dependencies": dependencies, "acts": rows, "totals": totals}


def write_report(directory: Path, result: dict) -> str:
    """Persist real counts or explicit failure provenance, without endpoint URLs or credentials."""
    report = (f"# Corpus statistics — {result['status']}\n\n"
              f"Attempted at {result['measured_at_utc']}; Qdrant collection `{result['collection']}`.\n\n"
              "| Act | Unique stored chunks | Graph nodes | Directed graph edges |\n|---|---:|---:|---:|\n")
    for row in [*result["acts"], {"act": "Total", **result["totals"]}]:
        values = ["Not measured" if row[key] is None else str(row[key]) for key in ("chunks", "graph_nodes", "graph_edges")]
        report += f"| {row['act']} | " + " | ".join(values) + " |\n"
    report += "\nUnavailable counts are not zeros. Chunk counts use distinct stored chunk_id values; graph edges include every stored relationship, including inverse hierarchy edges, and are grouped by their source node's act. Unmapped metadata is retained. Freeze ingestion while collecting these independent read-only counts.\n"
    for name, dependency in result["dependencies"].items():
        report += f"\n- {name}: {dependency['status']}" + (f" ({dependency['error_type']})" if "error_type" in dependency else "") + ".\n"
    if result["dependencies"]["qdrant"]["status"] == "ok":
        vector = result["dependencies"]["qdrant"]
        report += f"\nStored points: {vector['stored_points']}; unique chunk IDs: {vector['unique_chunks']}; duplicate chunk points: {vector['duplicate_chunk_points']}; points without chunk IDs: {vector['points_without_chunk_id']}.\n"
    atomic_text(directory / "corpus_stats.json", json.dumps(result, indent=2) + "\n")
    atomic_text(directory / "corpus_stats.md", report)
    return report


def main() -> None:
    """Load only service clients, measure live storage and exit nonzero on incomplete counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", default="legal_rag")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    settings = EvaluationSettings()

    def vector_factory() -> Any:
        """Create a bounded Qdrant connection without requiring model or generation keys."""
        from qdrant_client import QdrantClient

        if not settings.qdrant_url or not settings.qdrant_url.strip():
            raise ValueError("QDRANT_URL is required")
        return QdrantClient(url=settings.qdrant_url,
                            api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
                            timeout=ceil(settings.external_timeout_seconds), check_compatibility=False)

    def graph_factory() -> Any:
        """Create only the graph client, validating its required connection configuration."""
        from db.neo4j_store import Neo4jStore

        return Neo4jStore(settings=settings)

    result = collect_stats(vector_factory, graph_factory, args.collection)
    print(write_report(args.output_dir, result))
    if result["status"] != "completed":
        parser.exit(1, "Corpus statistics incomplete; unavailable counts were left null.\n")


if __name__ == "__main__":
    main()
