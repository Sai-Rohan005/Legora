"""Export blinded manual labels, rerun the production judge, and measure agreement."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from eval.models import GoldItem
from eval.run_answer_eval import load_pipeline
from eval.storage import atomic_text, load_gold, read_jsonl

LABELS = ("incorrect", "partially", "correct")
COLUMNS = ("id", "question", "answer", "context_snippet", "my_label", "my_notes")


class Sample(BaseModel):
    """Retain the final attempt's judge inputs and raw outputs separately from labels."""

    model_config = ConfigDict(extra="forbid")
    id: str
    question: str
    judge_question: str
    answer: str
    context: str
    context_snippet: str
    overall_score: float = Field(ge=0, le=100, allow_inf_nan=False)
    correctness: int = Field(ge=0, le=4, strict=True)
    evaluator_model: str
    seed: int


class Judge(Protocol):
    """Production judge boundary; persistence and statistics remain ordinary code."""

    model: str

    def evaluate_context(self, question: str, answer: str, context: str) -> dict:
        """Judge the exact saved context at temperature zero."""
        ...


def sample_questions(gold: list[GoldItem], count: int, seed: int) -> list[GoldItem]:
    """Select without replacement from reviewed items, independent of input ordering."""
    eligible = sorted((item for item in gold if item.reviewed), key=lambda item: item.id)
    if count < 1 or len(eligible) < count:
        raise ValueError(f"Need {count} reviewed questions; found {len(eligible)}")
    return random.Random(seed).sample(eligible, count)


def export_samples(gold: list[GoldItem], pipeline: Any, count: int, seed: int,
                   csv_path: Path, samples_path: Path) -> list[Sample]:
    """Generate full answers and export blank labels without exposing judge predictions."""
    if csv_path.exists() or samples_path.exists():
        raise ValueError("Export paths already exist; use new paths to preserve manual labels")
    samples = []
    for item in sample_questions(gold, count, seed):
        result = pipeline.search(item.question)
        retrieval, evaluation = result["retrieval"], result["evaluation"]
        # Use the identical source formatter and final retry question used by RAGPipeline.evaluate.
        context = pipeline.evaluator._build_context(
            retrieval.get("statutory_results", []),
            list(retrieval.get("graph_context", {}).values()),
            retrieval.get("judgments", []),
        )
        snippet = "Retrieved context:\n" + context[:4000] + ("\n[TRUNCATED: full context in sample snapshot]" if len(context) > 4000 else "")
        samples.append(Sample(
            id=item.id, question=item.question, judge_question=result["query"],
            answer=result["answer"], context=context, context_snippet=snippet,
            overall_score=evaluation.get("llm_overall_score", evaluation["overall_score"]),
            correctness=evaluation["correctness"]["score"],
            evaluator_model=pipeline.evaluator.model, seed=seed,
        ))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=COLUMNS)
    writer.writeheader()
    for sample in samples:
        writer.writerow({**{key: getattr(sample, key) for key in COLUMNS[:4]}, "my_label": "", "my_notes": ""})
    atomic_text(samples_path, "".join(sample.model_dump_json() + "\n" for sample in samples))
    atomic_text(csv_path, output.getvalue())
    return samples


def load_samples(path: Path) -> list[Sample]:
    """Require a nonempty, unique sample snapshot before scoring or model loading."""
    samples = read_jsonl(path, Sample)
    if not samples or len({sample.id for sample in samples}) != len(samples):
        raise ValueError("Sample snapshot must contain unique, nonempty records")
    return samples


def load_labels(path: Path, samples: list[Sample]) -> dict[str, str]:
    """Accept only label/note edits; reject stale, duplicate, missing or unknown rows."""
    expected = {sample.id: sample for sample in samples}
    seen, labels = set(), {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError("Manual CSV columns must match the exported columns")
        for row in reader:
            identifier = row["id"]
            if identifier not in expected or identifier in seen or None in row:
                raise ValueError("Manual CSV contains unknown, duplicate or malformed rows")
            seen.add(identifier)
            if any(row[key] != getattr(expected[identifier], key) for key in COLUMNS[:4]):
                raise ValueError("Question, answer or context changed; export a new sample")
            label = (row["my_label"] or "").strip().lower()
            if label and label not in LABELS:
                raise ValueError("my_label must be correct, partially or incorrect")
            if label:
                labels[identifier] = label
    if seen != set(expected):
        raise ValueError("Manual CSV is missing sample rows")
    if not labels:
        raise ValueError("No manual labels yet")
    return labels


def correlation(left: list[float], right: list[float]) -> float | None:
    """Pearson correlation, undefined for constant inputs or fewer than two pairs."""
    if len(left) != len(right):
        raise ValueError("Correlation requires paired observations")
    if len(left) < 2:
        return None
    centered_x = [value - statistics.mean(left) for value in left]
    centered_y = [value - statistics.mean(right) for value in right]
    denominator = math.sqrt(sum(value ** 2 for value in centered_x) * sum(value ** 2 for value in centered_y))
    return sum(x * y for x, y in zip(centered_x, centered_y)) / denominator if denominator else None


def ranks(values: list[float]) -> list[float]:
    """Assign average one-based ranks to ties for Spearman correlation."""
    return [1 + sum(other < value for other in values) + (values.count(value) - 1) / 2 for value in values]


def agreement(samples: list[Sample], labels: dict[str, str]) -> dict:
    """Unweighted Cohen kappa and raw-score Pearson/Spearman on labeled rows only."""
    paired = [sample for sample in samples if sample.id in labels]
    if not paired or set(labels) - {sample.id for sample in samples}:
        raise ValueError("Agreement requires labels belonging to the sample")
    matrix = [[0] * 3 for _ in LABELS]
    human, scores = [], []
    for sample in paired:
        actual = LABELS.index(labels[sample.id])
        predicted = 2 if sample.correctness >= 3 else 1 if sample.correctness == 2 else 0
        matrix[actual][predicted] += 1
        human.append(actual)
        scores.append(sample.overall_score)
    n = len(paired)
    accuracy = sum(matrix[index][index] for index in range(3)) / n
    expected = sum(sum(matrix[index]) * sum(row[index] for row in matrix) for index in range(3)) / n ** 2
    return {
        "sample_count": len(samples), "labeled_count": n, "unlabeled_count": len(samples) - n,
        "accuracy": accuracy, "cohen_kappa": (accuracy - expected) / (1 - expected) if expected < 1 else None,
        "labels": LABELS, "confusion_matrix": matrix,
        "pearson_score_label": correlation(scores, human),
        "spearman_score_label": correlation(ranks(scores), ranks(human)),
    }


def sample_hash(samples: list[Sample]) -> str:
    """Bind consistency results to all saved judge inputs and original outputs."""
    serialized = "\n".join(sample.model_dump_json() for sample in sorted(samples, key=lambda sample: sample.id))
    return hashlib.sha256(serialized.encode()).hexdigest()


def run_consistency(samples: list[Sample], judge: Judge) -> dict:
    """Make three independent temperature-zero calls per frozen answer/context."""
    details = []
    for sample in samples:
        scores = []
        for _ in range(3):
            result = judge.evaluate_context(sample.judge_question, sample.answer, sample.context)
            score = result["overall_score"]
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
                raise ValueError("Judge overall_score must be finite and between 0 and 100")
            scores.append(score)
        details.append({"id": sample.id, "scores": scores, "score_variance": statistics.variance(scores)})
    return {"sample_sha256": sample_hash(samples), "model": judge.model, "temperature": 0,
            "runs_per_answer": 3, "variance_ddof": 1, "details": details}


def validate_consistency(result: dict, samples: list[Sample]) -> list[dict]:
    """Reject stale/incomplete reruns and recompute variance from recorded scores."""
    if (result.get("sample_sha256") != sample_hash(samples) or result.get("temperature") != 0
            or result.get("runs_per_answer") != 3 or result.get("variance_ddof") != 1):
        raise ValueError("Consistency results do not match this sample or protocol")
    rows = result["details"]
    if len(rows) != len(samples) or {row["id"] for row in rows} != {sample.id for sample in samples}:
        raise ValueError("Consistency results must cover each sampled answer exactly once")
    for row in rows:
        scores = row["scores"]
        if len(scores) != 3 or any(isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100 for score in scores):
            raise ValueError("Consistency requires three valid scores per answer")
    return [{**row, "score_variance": statistics.variance(row["scores"])} for row in rows]


def write_report(path: Path, samples: list[Sample], labels: dict[str, str], consistency: dict | None) -> str:
    """Write measured agreement and optional full-sample consistency as Markdown."""
    metrics = agreement(samples, labels)

    def display(value: float | None) -> str:
        """Make undefined statistics explicit rather than substituting zeros."""
        return "Undefined" if value is None else f"{value:.4f}"

    report = ("# Judge validation\n\n"
              "Human labels: incorrect=0, partially=1, correct=2. Judge correctness: 0–1=incorrect, 2=partially, 3–4=correct. "
              "Correlations use original raw overall_score (before citation penalties).\n\n"
              f"Sampled: {len(samples)}; labeled: {metrics['labeled_count']}; unlabeled excluded: {metrics['unlabeled_count']}.\n\n"
              "| Metric | Value |\n|---|---:|\n")
    for key in ("accuracy", "cohen_kappa", "pearson_score_label", "spearman_score_label"):
        report += f"| {key} | {display(metrics[key])} |\n"
    report += "\nConfusion matrix: rows = human, columns = judge.\n\n| Human \\ Judge | incorrect | partially | correct |\n|---|---:|---:|---:|\n"
    for label, row in zip(LABELS, metrics["confusion_matrix"]):
        report += f"| {label} | " + " | ".join(map(str, row)) + " |\n"
    report += "\nOriginal evaluator models: " + ", ".join(sorted({sample.evaluator_model for sample in samples})) + ".\n"
    report += "\nConsistency uses three fresh calls per answer at temperature 0, with sample variance (ddof=1).\n\n"
    if consistency is None:
        report += "Not run: no saved consistency measurements.\n"
    else:
        rows = validate_consistency(consistency, samples)
        report += f"Model: `{consistency['model']}`; answers: {len(rows)}; mean score variance: {statistics.mean(row['score_variance'] for row in rows):.4f}; max variance: {max(row['score_variance'] for row in rows):.4f}.\n\n"
        report += "| ID | Run 1 | Run 2 | Run 3 | Variance |\n|---|---:|---:|---:|---:|\n"
        for row in rows:
            report += f"| {row['id']} | " + " | ".join(map(str, row["scores"])) + f" | {row['score_variance']:.4f} |\n"
    report += "\nAgreement describes the labeled subset and is not independent ground truth. Temperature zero does not guarantee identical judge outputs. Full context is retained in the sample snapshot; CSV snippets may be truncated.\n"
    atomic_text(path, report)
    return report


def main() -> None:
    """Run export, consistency and offline report as separate resumable steps."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("export", "consistency", "report"))
    parser.add_argument("--gold", type=Path, default=Path("eval/gold.jsonl"))
    parser.add_argument("--csv", type=Path, default=Path("results/judge_validation.csv"))
    parser.add_argument("--samples", type=Path, default=Path("results/judge_validation_samples.jsonl"))
    parser.add_argument("--consistency", type=Path, default=Path("results/judge_consistency.json"))
    parser.add_argument("--output", type=Path, default=Path("results/judge_validation.md"))
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    resource = None
    try:
        if args.command == "export":
            gold = load_gold(args.gold)
            sample_questions(gold, args.count, args.seed)  # Gate before loading models/clients.
            if args.csv.exists() or args.samples.exists():
                raise ValueError("Export paths already exist; use new paths")
            resource = load_pipeline()
            export_samples(gold, resource, args.count, args.seed, args.csv, args.samples)
            print(f"Exported {args.count} answers; fill my_label and my_notes in {args.csv}")
        elif args.command == "consistency":
            from evaluator.LLM_evaluator import LegalLLMEvaluator
            from legora.config import EvaluationSettings

            samples = load_samples(args.samples)
            resource = LegalLLMEvaluator(settings=EvaluationSettings())
            result = run_consistency(samples, resource)
            atomic_text(args.consistency, json.dumps(result, indent=2) + "\n")
            print(f"Saved three-run consistency measurements to {args.consistency}")
        else:
            samples = load_samples(args.samples)
            labels = load_labels(args.csv, samples)
            consistency = json.loads(args.consistency.read_text()) if args.consistency.exists() else None
            print(write_report(args.output, samples, labels, consistency))
    except Exception as error:
        if not args.output.exists():
            atomic_text(args.output, "# Judge validation — not run\n\nNo completed manual agreement/consistency report. Export real pipeline answers and fill manual labels before reporting.\n")
        # Safe validation errors are useful, but upstream failures may contain secrets/prompts.
        message = str(error) if type(error) is ValueError and args.command == "export" and resource is None else type(error).__name__
        parser.exit(1, f"Judge validation failed: {message}. No incomplete run was scored.\n")
    finally:
        if resource is not None:
            if args.command == "export":
                resource.close()
            else:
                resource.client.close()


if __name__ == "__main__":
    main()
