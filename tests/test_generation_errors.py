"""Provider failures remain actionable, paced and safe without changing human review state."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from google.genai.errors import ClientError, ServerError

from eval.generate import DraftGenerationError, GeminiDrafter, generate_items
from eval.models import Draft, Provision
from eval.review import interactive_review
from eval.storage import load_gold, write_jsonl
from tests.test_answer_eval import gold


def outside_draft() -> Draft:
    """Supply only a synthetic unreviewed nonlegal question in temporary files."""
    return Draft(question="How should I water a houseplant?", intent="out_of_scope",
                 expected_chunk_ids=[], supported=False, notes="Nonlegal question")


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429])
def test_client_errors_stop_immediately_preserve_drafts_and_hide_provider_text(tmp_path: Path, code: int) -> None:
    """Permanent/quota failures must not hammer the provider or discard existing approvals."""
    output = tmp_path / "gold.jsonl"
    existing = gold("oos-001", answerable=False)
    write_jsonl(output, [existing])
    drafter = Mock(side_effect=ClientError(code, {"error": {"message": "sensitive provider response"}}))
    with pytest.raises(DraftGenerationError) as failure:
        generate_items(output, [], drafter, out_of_scope_only=True, out_of_scope_count=2)
    assert f"HTTP {code}" in str(failure.value)
    assert "sensitive" not in str(failure.value)
    assert drafter.call_count == 1
    assert load_gold(output) == [existing]


def test_transient_server_errors_back_off_then_save_unreviewed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real retry logic makes bounded attempts and saves only a successful validated draft."""
    sleep = Mock()
    monkeypatch.setattr("eval.generate.time.sleep", sleep)
    drafter = Mock(side_effect=[ServerError(503, {}), ServerError(502, {}), outside_draft()])
    output = tmp_path / "gold.jsonl"
    assert generate_items(output, [], drafter, out_of_scope_only=True, out_of_scope_count=1) == 1
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]
    assert drafter.call_count == 3 and load_gold(output)[0].reviewed is False


def test_exhausted_server_errors_do_not_write_fake_drafts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An exhausted upstream retry budget remains an incomplete generation run."""
    monkeypatch.setattr("eval.generate.time.sleep", Mock())
    drafter = Mock(side_effect=ServerError(503, {}))
    output = tmp_path / "gold.jsonl"
    with pytest.raises(DraftGenerationError, match="HTTP 503"):
        generate_items(output, [], drafter, out_of_scope_only=True, out_of_scope_count=1)
    assert drafter.call_count == 3 and load_gold(output) == []


def test_drafter_paces_request_starts_without_changing_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Five-second spacing waits only the remaining time since the preceding request."""
    drafter = GeminiDrafter.__new__(GeminiDrafter)
    drafter.model, drafter.request_interval, drafter.last_request = "model", 5, 100
    drafter.client = Mock()
    drafter.client.models.generate_content.return_value.parsed = outside_draft()
    sleep = Mock()
    monkeypatch.setattr("eval.generate.time.sleep", sleep)
    monkeypatch.setattr("eval.generate.time.monotonic", Mock(side_effect=[102, 105]))
    assert drafter("test prompt") == outside_draft()
    sleep.assert_called_once_with(3)
    assert drafter.last_request == 105
    assert drafter.client.models.generate_content.call_args.kwargs["contents"] == "test prompt"


def test_review_answerable_only_shows_sources_and_requires_explicit_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Filtering the queue cannot accidentally approve OOS questions or hide legal evidence."""
    path = tmp_path / "gold.jsonl"
    outside = gold("oos-001", answerable=False, reviewed=False)
    legal = gold("single-bns-001", reviewed=False)
    write_jsonl(path, [outside, legal])
    catalog = {"BNS-303": Provision(chunk_id="BNS-303", act="BNS", text="Synthetic supporting source text")}
    commands = iter(["s", "a"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))
    interactive_review(path, catalog, answerable_only=True)
    saved = {item.id: item for item in load_gold(path)}
    assert saved[legal.id].reviewed is True and saved[outside.id].reviewed is False
    output = capsys.readouterr().out
    assert "Synthetic supporting source text" in output and "oos-001 |" not in output


def test_review_exit_does_not_approve_any_question(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exiting the review prompt is deliberately distinct from labeling approval."""
    path = tmp_path / "gold.jsonl"
    write_jsonl(path, [gold("single-bns-001", reviewed=False)])
    monkeypatch.setattr("builtins.input", lambda _: "x")
    interactive_review(path, {}, answerable_only=True)
    assert load_gold(path)[0].reviewed is False
