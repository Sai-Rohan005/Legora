"""Run the full pipeline on reviewed gold and report citation/coverage/refusal measures."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from LegalRag.citation_check import check_citations, root_id
from eval.models import GoldItem
from eval.predict import canonical_refusal
from eval.storage import atomic_text, load_gold


class AnswerPipeline(Protocol):
    """Only full-pipeline search and resource cleanup are required by this runner."""

    def search(self, query: str) -> dict:
        """Generate, verify, evaluate and retry one question."""
        ...

    def close(self) -> None:
        """Close the model/service clients after the batch."""
        ...


def load_pipeline() -> AnswerPipeline:
    """Delay expensive imports/initialization until reviewed items are available."""
    from LegalRag.rag_pipeline import RAGPipeline

    return RAGPipeline()


def is_refusal(answer: str) -> bool:
    """Recognize canonical abstention and explicit inability/out-of-scope wording."""
    if canonical_refusal(answer):
        return True
    normalized = " ".join(answer.casefold().split()).replace("’", "\'")
    normalized = normalized.replace("i\'m ", "i am ").replace("we\'re ", "we are ")
    return bool(re.search(
        r"\b(?:i|we) (?:cannot|can't|am unable to|are unable to) (?:answer|help with|provide (?:an answer|advice|guidance))\b"
        r"|\b(?:this (?:question|request|topic)|your (?:question|request)) (?:is|falls) outside (?:the |my |this system's )?(?:legal )?scope\b",
        normalized,
    ))


def contains_expected(item: GoldItem, identifiers: set[str]) -> bool:
    """Require all expected roots; single-source human-approved alternates may substitute."""
    roots = {root_id(identifier) for identifier in identifiers}
    expected = {root_id(identifier) for identifier in item.expected_chunk_ids}
    if len(item.expected_chunk_ids) == 1:
        return bool(roots & (expected | {root_id(identifier) for identifier in item.acceptable_alternates}))
    return expected <= roots


def evaluate_answers(gold: list[GoldItem], pipeline: AnswerPipeline) -> tuple[dict, list[dict]]:
    """Run reviewed questions only and recompute checks from each returned answer/context."""
    reviewed = sorted((item for item in gold if item.reviewed), key=lambda item: item.id)
    if not reviewed:
        raise ValueError("No reviewed gold items")
    details = []
    for item in reviewed:
        result = pipeline.search(item.question)
        check = check_citations(result["answer"], result["retrieval"])
        cited_ids = {citation.chunk_id for citation in check.citations if citation.chunk_id}
        supported_ids = {citation.chunk_id for citation in check.citations if citation.chunk_id and citation.status == "citation_supported"}
        details.append({
            "id": item.id, "question": item.question, "intent": item.intent,
            "answerable": item.answerable, "answer": result["answer"],
            "expected_chunk_ids": item.expected_chunk_ids,
            "citation_check": check.model_dump(),
            "answer_contains_expected_provision": contains_expected(item, cited_ids) if item.answerable else None,
            "supported_expected_provision": contains_expected(item, supported_ids) if item.answerable else None,
            "refused": is_refusal(result["answer"]),
            "attempts": result["attempts"], "status": result["status"],
            "evaluation_score": result["evaluation"].get("overall_score", 0),
        })
        print(f"Evaluated answer {item.id}", flush=True)
    return summarize(details), details


def summarize(details: list[dict]) -> dict:
    """Report explicit denominators; uncited answers cannot inflate citation precision."""
    if not details:
        raise ValueError("No evaluated answers")
    cited = sum(row["citation_check"]["total_citations"] for row in details)
    supported = sum(row["citation_check"]["supported_count"] for row in details)
    unsupported = sum(row["citation_check"]["unsupported_count"] for row in details)
    citation_bearing = [row["citation_check"]["citation_precision"] for row in details if row["citation_check"]["total_citations"]]
    answerable = [row for row in details if row["answerable"]]
    outside = [row for row in details if not row["answerable"]]

    def rate(numerator: float, denominator: int) -> float | None:
        """Undefined categories produce null, not a misleading perfect/zero metric."""
        return numerator / denominator if denominator else None

    return {
        "status": "completed", "reviewed_items": len(details),
        "answerable_items": len(answerable), "out_of_scope_items": len(outside),
        "total_citations": cited, "supported_citations": supported, "unsupported_citations": unsupported,
        "answers_without_citations": len(details) - len(citation_bearing),
        "citation_precision": rate(supported, cited),
        "macro_citation_precision": rate(sum(citation_bearing), len(citation_bearing)),
        "unsupported_citation_rate": rate(unsupported, cited),
        "unsupported_answer_rate": rate(sum(bool(row["citation_check"]["unsupported_citations"]) for row in details), len(details)),
        "answer_contains_expected_provision_rate": rate(sum(row["answer_contains_expected_provision"] for row in answerable), len(answerable)),
        "supported_expected_provision_rate": rate(sum(row["supported_expected_provision"] for row in answerable), len(answerable)),
        "out_of_scope_refusal_rate": rate(sum(row["refused"] for row in outside), len(outside)),
    }


def write_report(directory: Path, summary: dict, details: list[dict]) -> str:
    """Persist measured summaries and answer-level provenance only after a complete run."""
    atomic_text(directory / "answer_eval.json", json.dumps(summary, indent=2) + "\n")
    atomic_text(directory / "answer_eval_details.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in details))
    report = "# Answer evaluation\n\nReviewed items only. Citation support measures source presence, not claim entailment.\n\n| Metric | Value |\n|---|---:|\n"
    for key in ("reviewed_items", "answerable_items", "out_of_scope_items", "total_citations", "answers_without_citations", "citation_precision", "unsupported_citation_rate", "unsupported_answer_rate", "answer_contains_expected_provision_rate", "supported_expected_provision_rate", "out_of_scope_refusal_rate"):
        value = summary[key]
        report += f"| {key} | {'Undefined' if value is None else f'{value:.4f}' if isinstance(value, float) else value} |\n"
    atomic_text(directory / "answer_eval.md", report)
    return report


def main(pipeline_factory: Callable[[], AnswerPipeline] = load_pipeline) -> None:
    """Load one full pipeline and include reviewed out-of-scope questions in the batch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("eval/gold.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    pipeline = None
    try:
        gold = [item for item in load_gold(args.gold) if item.reviewed]
        if not gold:
            path = args.output_dir / "answer_eval.md"
            if not path.exists():
                atomic_text(path, "# Answer evaluation — not run\n\nNo reviewed gold items. No answer metrics have been computed.\n")
            parser.exit(1, "Not run: no reviewed gold items.\n")
        pipeline = pipeline_factory()
        summary, details = evaluate_answers(gold, pipeline)
        summary["gold_sha256"] = hashlib.sha256(args.gold.read_bytes()).hexdigest()
        print(write_report(args.output_dir, summary, details))
    except Exception as error:
        parser.exit(1, f"Answer evaluation failed ({type(error).__name__}); no incomplete batch was scored.\n")
    finally:
        if pipeline is not None:
            pipeline.close()


if __name__ == "__main__":
    main()
