"""Compute retrieval and refusal metrics exclusively on reviewed gold items."""

import argparse
import json
from pathlib import Path

from eval.models import GoldItem, Prediction
from eval.storage import atomic_text, load_gold
from legora.config import EvaluationSettings


def reviewed_gold(path: Path) -> list[GoldItem]:
    """Never treat generated drafts as evaluation labels."""
    items = [item for item in load_gold(path) if item.reviewed]
    if not items:
        raise ValueError("No reviewed gold items; approve labels before computing metrics")
    return items


def reviewed_predictions(path: Path, reviewed_ids: set[str]) -> dict[str, Prediction]:
    """Ignore nonreviewed predictions before validating or using their contents."""
    predictions = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        entry = json.loads(line)
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid prediction object at line {number}")
        if entry.get("id") not in reviewed_ids:
            continue
        prediction = Prediction.model_validate(entry)
        if prediction.id in predictions:
            raise ValueError(f"Duplicate reviewed prediction at line {number}")
        predictions[prediction.id] = prediction
    return predictions


def score_reviewed(items: list[GoldItem], predictions: dict[str, Prediction], threshold: float = 80) -> dict:
    """Score reviewed labels only; missing predictions count as unsuccessful cases."""
    reviewed = [item for item in items if item.reviewed]
    if not reviewed:
        raise ValueError("No reviewed items")
    answerable = [item for item in reviewed if item.answerable]
    unanswerable = [item for item in reviewed if not item.answerable]
    hits = complete = scope_successes = 0
    recall = precision = 0.0
    for item in reviewed:
        prediction = predictions.get(item.id)
        if prediction is None:
            continue
        if not item.answerable:
            scope_successes += int(prediction.refused or prediction.score < threshold)
            continue
        retrieved = set(prediction.retrieved_chunk_ids)
        expected = set(item.expected_chunk_ids)
        allowed = expected | set(item.acceptable_alternates)
        hits += int(bool(retrieved & allowed))
        # Flat alternates cannot express complete alternative multi-provision sets.
        if len(expected) == 1:
            success = bool(retrieved & allowed)
            complete += int(success)
            recall += float(success)
        else:
            complete += int(expected <= retrieved)
            recall += len(expected & retrieved) / len(expected)
        precision += len(retrieved & allowed) / len(retrieved) if retrieved else 0.0

    def rate(value: float, count: int) -> float | None:
        """Use null for an absent category, not a fabricated zero-valued result."""
        return round(value / count, 6) if count else None

    return {
        "reviewed_items": len(reviewed), "answerable_items": len(answerable),
        "out_of_scope_items": len(unanswerable),
        "missing_predictions": sum(item.id not in predictions for item in reviewed),
        "retrieval_hit_rate": rate(hits, len(answerable)),
        "all_required_provisions_rate": rate(complete, len(answerable)),
        "mean_provision_recall": rate(recall, len(answerable)),
        "mean_citation_precision": rate(precision, len(answerable)),
        "out_of_scope_success_rate": rate(scope_successes, len(unanswerable)),
        "low_confidence_threshold": threshold,
    }


def main() -> None:
    """Evaluate existing predictions without making API, database, or Gemini calls."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("eval/gold.jsonl"))
    parser.add_argument("--predictions", type=Path, default=Path("eval/predictions.jsonl"))
    parser.add_argument("--threshold", type=float, help="Defaults to PASS_THRESHOLD")
    parser.add_argument("--output", type=Path, help="Optional path for the measured JSON report")
    args = parser.parse_args()
    threshold = args.threshold if args.threshold is not None else EvaluationSettings().pass_threshold
    if not 0 <= threshold <= 100:
        parser.error("--threshold must be between 0 and 100")
    try:
        gold = reviewed_gold(args.gold)
        predictions = reviewed_predictions(args.predictions, {item.id for item in gold})
        report = json.dumps(score_reviewed(gold, predictions, threshold), indent=2) + "\n"
        if args.output:
            atomic_text(args.output, report)
        print(report, end="")
    except (ValueError, OSError):
        parser.exit(1, "Metrics unavailable: require reviewed labels and valid, uniquely identified predictions.\n")


if __name__ == "__main__":
    main()
