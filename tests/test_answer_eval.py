"""Crafted full-pipeline outputs test reviewed-only answer metrics without network calls."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from eval.models import GoldItem
from eval.run_answer_eval import evaluate_answers, is_refusal, main, write_report
from eval.storage import write_jsonl


def gold(identifier: str, answerable: bool = True, reviewed: bool = True, expected: list[str] | None = None) -> GoldItem:
    """Create labels only in tests, with explicit approval state."""
    ids = expected or ["BNS-303"]
    return GoldItem(
        id=identifier, question=f"Question {identifier}?",
        intent="punishment" if answerable else "out_of_scope",
        act=("MULTI" if len(ids) > 1 else "BNS") if answerable else "OUT_OF_SCOPE",
        expected_chunk_ids=ids if answerable else [], answerable=answerable, reviewed=reviewed,
    )


def result(answer: str, sources: str = "BNS-303") -> dict:
    """Return a lightweight full-pipeline-shaped answer with actual supplied context."""
    return {"answer": answer, "retrieval": {"final_context": sources},
            "evaluation": {"overall_score": 90}, "attempts": 1, "status": "PASS"}


def test_answer_metrics_use_real_citations_and_separate_denominators() -> None:
    """Micro precision, unsupported rates, expected-root coverage and refusal are distinct."""
    pipeline = Mock()
    pipeline.search.side_effect = [
        result("Section 303 BNS and section 999 BNS."),
        result("The punishment is described in the context."),
        result("I cannot answer this question because it is outside legal scope.", ""),
    ]
    labels = [gold("a"), gold("b"), gold("c", answerable=False), gold("draft", reviewed=False)]
    summary, details = evaluate_answers(labels, pipeline)
    assert pipeline.search.call_count == 3
    assert summary["reviewed_items"] == 3 and summary["answerable_items"] == 2
    assert summary["total_citations"] == 2
    assert summary["citation_precision"] == 0.5
    assert summary["unsupported_citation_rate"] == 0.5
    assert summary["unsupported_answer_rate"] == pytest.approx(1 / 3)
    assert summary["answer_contains_expected_provision_rate"] == 0.5
    assert summary["out_of_scope_refusal_rate"] == 1
    assert summary["answers_without_citations"] == 2
    assert details[0]["citation_check"]["unsupported_citations"] == ["BNS-999"]


def test_expected_mention_does_not_imply_context_support() -> None:
    """A hallucinated expected ID may be mentioned but must not earn supported coverage."""
    pipeline = Mock()
    pipeline.search.return_value = result("Section 303 BNS applies.", "BNS-1")
    summary, _ = evaluate_answers([gold("one")], pipeline)
    assert summary["answer_contains_expected_provision_rate"] == 1
    assert summary["supported_expected_provision_rate"] == 0
    assert summary["citation_precision"] == 0


def test_multi_provision_answer_requires_all_expected_roots() -> None:
    """Mentioning one target in a multi-provision gold question is incomplete."""
    pipeline = Mock()
    pipeline.search.return_value = result("Section 303 BNS.", "BNS-303 BSA-115")
    summary, _ = evaluate_answers([gold("multi", expected=["BNS-303", "BSA-115(2)"])], pipeline)
    assert summary["answer_contains_expected_provision_rate"] == 0


def test_no_citation_scores_are_undefined_and_low_score_is_not_refusal() -> None:
    """An uncited answer cannot inflate precision, and confidence alone is not refusal."""
    pipeline = Mock()
    pipeline.search.return_value = result("Here is a recipe.")
    pipeline.search.return_value["evaluation"]["overall_score"] = 0
    summary, _ = evaluate_answers([gold("outside", answerable=False)], pipeline)
    assert summary["citation_precision"] is None
    assert summary["unsupported_citation_rate"] is None
    assert summary["answer_contains_expected_provision_rate"] is None
    assert summary["out_of_scope_refusal_rate"] == 0


@pytest.mark.parametrize("answer,refused", [
    ("The provided legal corpus does not contain sufficient information to answer this question.", True),
    ("I can't answer a cooking question.", True),
    ("I'm unable to answer that request.", True),
    ("I can’t provide advice on that topic.", True),
    ("Your question is outside the legal scope.", True),
    ("The offender cannot escape punishment under Section 303 BNS.", False),
    ("The police may answer questions under the applicable procedure.", False),
])
def test_refusal_wording(answer: str, refused: bool) -> None:
    """Recognize explicit refusals without treating every legal negation as a refusal."""
    assert is_refusal(answer) is refused


def test_answer_report_contains_measured_values_and_per_answer_details(tmp_path: Path) -> None:
    """The report is computed from crafted outputs, never invented as live benchmark data."""
    pipeline = Mock()
    pipeline.search.return_value = result("Section 303 BNS.")
    summary, details = evaluate_answers([gold("one")], pipeline)
    report = write_report(tmp_path, summary, details)
    assert json.loads((tmp_path / "answer_eval.json").read_text())["citation_precision"] == 1
    assert "unsupported_citation_rate" in report
    saved = json.loads((tmp_path / "answer_eval_details.jsonl").read_text())
    assert saved["citation_check"]["citations"][0]["chunk_id"] == "BNS-303"


def test_answer_runner_rejects_drafts_before_model_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unreviewed gold cannot trigger external calls or create numerical reports."""
    path, directory = tmp_path / "gold.jsonl", tmp_path / "results"
    write_jsonl(path, [gold("draft", reviewed=False)])
    factory = Mock(side_effect=AssertionError("No live startup expected"))
    monkeypatch.setattr("sys.argv", ["eval", "--gold", str(path), "--output-dir", str(directory)])
    with pytest.raises(SystemExit) as error:
        main(factory)
    assert error.value.code == 1
    factory.assert_not_called()
    assert "not run" in (directory / "answer_eval.md").read_text()
    assert not (directory / "answer_eval.json").exists()


def test_answer_runner_uses_one_pipeline_and_closes_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Full generation is performed once per reviewed question with one startup/cleanup."""
    path, directory = tmp_path / "gold.jsonl", tmp_path / "results"
    write_jsonl(path, [gold("one"), gold("two"), gold("draft", reviewed=False)])
    pipeline = Mock()
    pipeline.search.return_value = result("Section 303 BNS.")
    factory = Mock(return_value=pipeline)
    monkeypatch.setattr("sys.argv", ["eval", "--gold", str(path), "--output-dir", str(directory)])
    main(factory)
    factory.assert_called_once_with()
    assert pipeline.search.call_count == 2
    pipeline.close.assert_called_once_with()
