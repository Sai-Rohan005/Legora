"""Judge-validation workflow exercises real CSV, sampling and statistics offline."""

import csv
import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from eval.judge_validation import (
    COLUMNS, Sample, agreement, correlation, export_samples, load_labels,
    load_samples, main, ranks, run_consistency, sample_questions,
    validate_consistency, write_report,
)
from tests.test_answer_eval import gold


def sample(identifier: str = "one", score: float = 90, correctness: int = 4) -> Sample:
    """Create a frozen judge input only for local tests."""
    return Sample(id=identifier, question="Question?", judge_question="Expanded question?",
                  answer='Answer, with "quotes"\nand newline.', context="Full context",
                  context_snippet="Snippet", overall_score=score, correctness=correctness,
                  evaluator_model="test-model", seed=42)


def label_csv(path: Path, samples: list[Sample], labels: list[str]) -> None:
    """Write the exact manual format with intentional CSV quoting."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=COLUMNS)
    writer.writeheader()
    for item, label in zip(samples, labels):
        writer.writerow({**{key: getattr(item, key) for key in COLUMNS[:4]}, "my_label": label, "my_notes": "Manual note"})
    path.write_text(output.getvalue())


def test_sampling_is_reviewed_only_reproducible_and_order_independent() -> None:
    """Selection has no replacement and excludes unreviewed drafts."""
    questions = [gold(str(index)) for index in range(60)] + [gold("draft", reviewed=False)]
    chosen = sample_questions(questions, 50, 42)
    assert len({item.id for item in chosen}) == 50
    assert chosen == sample_questions(list(reversed(questions)), 50, 42)
    assert chosen != sample_questions(questions, 50, 43)
    assert all(item.reviewed for item in chosen)


@pytest.mark.parametrize("count", [0, -1, 51])
def test_sampling_requires_enough_reviewed_items(count: int) -> None:
    """Never silently shrink the requested sample or add fake answers."""
    with pytest.raises(ValueError):
        sample_questions([gold("one")], count, 42)


def test_export_is_blinded_preserves_final_inputs_and_raw_score(tmp_path: Path) -> None:
    """Human CSV hides judge outputs; sidecar retains exact final retry inputs."""
    pipeline = Mock()
    pipeline.evaluator.model = "test-model"
    pipeline.evaluator._build_context.return_value = "X" * 4100
    pipeline.search.return_value = {
        "query": "Expanded query", "answer": "Answer\nwith comma, and quotes\"",
        "retrieval": {"statutory_results": ["statute"], "graph_context": {"root": ["node"]}, "judgments": ["case"]},
        "evaluation": {"overall_score": 30, "llm_overall_score": 90, "correctness": {"score": 3}},
    }
    csv_path, snapshot = tmp_path / "labels.csv", tmp_path / "samples.jsonl"
    samples = export_samples([gold("one")], pipeline, 1, 42, csv_path, snapshot)
    saved = load_samples(snapshot)
    assert saved == samples
    assert saved[0].overall_score == 90 and saved[0].judge_question == "Expanded query"
    assert len(saved[0].context) == 4100 and "TRUNCATED" in saved[0].context_snippet
    pipeline.evaluator._build_context.assert_called_once_with(["statute"], [["node"]], ["case"])
    with csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == list(COLUMNS) and rows[0]["my_label"] == ""
    assert rows[0]["answer"] == saved[0].answer
    with pytest.raises(ValueError, match="already exist"):
        export_samples([gold("one")], pipeline, 1, 42, csv_path, snapshot)
    assert pipeline.search.call_count == 1


def test_labels_allow_blank_rows_and_normalize_manual_case(tmp_path: Path) -> None:
    """Blank labels are excluded rather than scored as incorrect."""
    path = tmp_path / "labels.csv"
    samples = [sample("a"), sample("b")]
    label_csv(path, samples, [" Correct ", ""])
    assert load_labels(path, samples) == {"a": "correct"}


@pytest.mark.parametrize("change", ["invalid", "duplicate", "missing", "unknown", "edited", "blank"])
def test_labels_reject_corrupt_or_unlabeled_exports(tmp_path: Path, change: str) -> None:
    """Metrics cannot silently join the wrong human answers to judge scores."""
    samples = [sample("a"), sample("b")]
    path = tmp_path / "labels.csv"
    altered = samples.copy()
    labels = ["correct", "partially"]
    if change == "invalid":
        labels[0] = "yes"
    elif change == "duplicate":
        altered[1] = altered[0]
    elif change == "missing":
        altered.pop()
    elif change == "unknown":
        altered[1] = sample("unknown")
    elif change == "edited":
        altered[0] = altered[0].model_copy(update={"answer": "Edited answer"})
    else:
        labels = ["", ""]
    label_csv(path, altered, labels)
    with pytest.raises(ValueError):
        load_labels(path, samples)


def test_agreement_known_matrix_kappa_and_correlations() -> None:
    """Compare hand-calculated three-class outcomes, including an off-diagonal error."""
    samples = [sample("a", 10, 0), sample("b", 50, 2), sample("c", 90, 4), sample("d", 60, 2), sample("blank")]
    metrics = agreement(samples, {"a": "incorrect", "b": "partially", "c": "correct", "d": "correct"})
    assert metrics["confusion_matrix"] == [[1, 0, 0], [0, 1, 0], [0, 1, 1]]
    assert metrics["accuracy"] == 0.75
    assert metrics["cohen_kappa"] == pytest.approx((.75 - .3125) / (1 - .3125))
    assert metrics["pearson_score_label"] == pytest.approx(correlation([10, 50, 90, 60], [0, 1, 2, 2]))
    assert metrics["spearman_score_label"] == pytest.approx(0.948683298)
    assert metrics["unlabeled_count"] == 1


@pytest.mark.parametrize("correctness,predicted", [(0, 0), (1, 0), (2, 1), (3, 2), (4, 2)])
def test_correctness_mapping(correctness: int, predicted: int) -> None:
    """The predeclared category boundaries do not depend on human labels."""
    matrix = agreement([sample(correctness=correctness)], {"one": "incorrect"})["confusion_matrix"]
    assert matrix[0][predicted] == 1


def test_degenerate_statistics_are_undefined() -> None:
    """Constant/single-row labels cannot produce meaningful kappa or correlation."""
    result = agreement([sample()], {"one": "correct"})
    assert result["accuracy"] == 1 and result["cohen_kappa"] is None
    assert result["pearson_score_label"] is None and result["spearman_score_label"] is None
    assert correlation([1, 1], [0, 2]) is None
    assert ranks([5, 1, 5, 9]) == [2.5, 1, 2.5, 4]


def test_consistency_three_fresh_calls_and_sample_variance() -> None:
    """Repeated judgments use exact frozen inputs, not regenerated answers or labels."""
    judge = Mock(model="test-model")
    judge.evaluate_context.side_effect = [{"overall_score": score} for score in [80, 90, 100, 42, 42, 42]]
    samples = [sample("a"), sample("b")]
    result = run_consistency(samples, judge)
    assert judge.evaluate_context.call_count == 6
    assert all(call.args == ("Expanded question?", samples[0].answer, "Full context") for call in judge.evaluate_context.call_args_list)
    assert result["details"][0]["score_variance"] == 100
    assert result["details"][1]["score_variance"] == 0
    assert validate_consistency(result, samples) == result["details"]
    with pytest.raises(ValueError):
        validate_consistency(result, [sample("changed")])
    result["details"].pop()
    with pytest.raises(ValueError):
        validate_consistency(result, samples)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1, 101, True, "90"])
def test_consistency_rejects_invalid_upstream_scores(score: object) -> None:
    """Failed or malformed evaluations must not become fabricated variance metrics."""
    judge = Mock(model="test-model")
    judge.evaluate_context.return_value = {"overall_score": score}
    with pytest.raises(ValueError):
        run_consistency([sample()], judge)


def test_report_contains_measured_agreement_and_variance(tmp_path: Path) -> None:
    """A complete report includes full confusion matrix and per-answer stability."""
    samples = [sample()]
    judge = Mock(model="test-model")
    judge.evaluate_context.side_effect = [{"overall_score": score} for score in [80, 90, 100]]
    output = tmp_path / "report.md"
    report = write_report(output, samples, {"one": "correct"}, run_consistency(samples, judge))
    assert "cohen_kappa | Undefined" in report
    assert "max variance: 100.0000" in report and "| correct | 0 | 0 | 1 |" in report
    assert output.read_text() == report


def test_export_gate_does_not_load_models_or_fabricate_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The present incomplete dataset cannot produce a claimed 50-answer sample."""
    factory = Mock(side_effect=AssertionError("No model startup"))
    monkeypatch.setattr("eval.judge_validation.load_pipeline", factory)
    output, csv_path = tmp_path / "report.md", tmp_path / "manual.csv"
    monkeypatch.setattr("sys.argv", ["judge", "export", "--gold", str(tmp_path / "missing.jsonl"), "--output", str(output), "--csv", str(csv_path)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    factory.assert_not_called()
    assert "not run" in output.read_text() and not csv_path.exists()


def test_report_command_is_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Filled labels can be scored without Gemini, Neo4j or pipeline initialization."""
    csv_path, snapshot, output = (tmp_path / name for name in ("manual.csv", "samples.jsonl", "report.md"))
    samples = [sample()]
    snapshot.write_text(samples[0].model_dump_json() + "\n")
    label_csv(csv_path, samples, ["correct"])
    monkeypatch.setattr("sys.argv", ["judge", "report", "--csv", str(csv_path), "--samples", str(snapshot), "--output", str(output), "--consistency", str(tmp_path / "absent.json")])
    main()
    assert "accuracy | 1.0000" in output.read_text()
    assert "Not run: no saved consistency" in output.read_text()


def test_production_judge_uses_same_prompt_and_temperature_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both live evaluation and frozen-context reruns share one real generation path."""
    from evaluator.LLM_evaluator import LegalLLMEvaluator
    from legora.config import EvaluationSettings

    client = Mock()
    client.models.generate_content.return_value.text = json.dumps({"overall_score": 88})
    monkeypatch.setattr("evaluator.LLM_evaluator.genai.Client", Mock(return_value=client))
    judge = LegalLLMEvaluator(settings=EvaluationSettings(_env_file=None, gemini_api_key="test-key"))
    live = judge.evaluate("Question?", "Answer", qdrant_context=[{"text": "Evidence"}])
    first = client.models.generate_content.call_args
    frozen = judge.evaluate_context("Question?", "Answer", judge._build_context([{"text": "Evidence"}], [], []))
    assert live == frozen == {"overall_score": 88}
    assert first.kwargs["contents"] == client.models.generate_content.call_args.kwargs["contents"]
    assert first.kwargs["config"].temperature == 0
