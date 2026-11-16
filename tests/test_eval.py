"""Offline tests for source sampling, human approval, and reviewed-only metrics."""

import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from eval.generate import bind_manifest, checked_item, generate_items
from eval.metrics import reviewed_gold, reviewed_predictions, score_reviewed
from eval.models import ACTS, Draft, GoldItem, Prediction, Provision
from eval.review import approve_item, edit_item
from eval.sample import balanced_sample, exported_payloads, scroll_payloads, stored_provisions
from eval.storage import load_catalog, load_gold, save_item, write_jsonl


@pytest.fixture
def catalog_records() -> list[Provision]:
    """Construct source records only for isolated tests, not the real gold file."""
    return [Provision(
        chunk_id=f"{act if act != 'Constitution' else 'CONST'}-{number}", act=act,
        text=f"Test provision text {act} {number}",
    ) for act in ACTS for number in range(1, 32)]


def gold(identifier: str = "single-bns-001", reviewed: bool = False, **changes: object) -> GoldItem:
    """Build a valid labeled test question with explicit approval state."""
    return GoldItem.model_validate({
        "id": identifier, "question": "Test question?", "intent": "definition", "act": "BNS",
        "expected_chunk_ids": ["BNS-1"], "acceptable_alternates": [],
        "answerable": True, "notes": "test", "reviewed": reviewed, **changes,
    })


def test_sample_has_exact_balanced_distinct_provisions(catalog_records: list[Provision]) -> None:
    """The default sample is 30 distinct roots per act, not 120 arbitrary chunks."""
    selected = balanced_sample(catalog_records)
    assert Counter(item.act for item in selected) == {act: 30 for act in ACTS}
    assert len({item.chunk_id for item in selected}) == 120
    assert selected == balanced_sample(list(reversed(catalog_records)))
    assert selected != balanced_sample(catalog_records, seed=43)


def test_sample_uses_parent_instead_of_duplicate_child(catalog_records: list[Provision]) -> None:
    """Adding child chunks cannot alter quotas or overweight one section."""
    children = [Provision(chunk_id="BNS-1(2)", act="BNS", text="Child"), Provision(chunk_id="BNS-1-EXP-1", act="BNS", text="Explanation")]
    assert balanced_sample(catalog_records + children) == balanced_sample(catalog_records)


def test_sample_requires_every_act(catalog_records: list[Provision]) -> None:
    """Insufficient corpus data fails instead of inventing expected provision IDs."""
    with pytest.raises(ValueError, match="Constitution"):
        balanced_sample([item for item in catalog_records if item.act != "Constitution"])


def test_stored_payloads_preserve_real_ids_and_skip_nonprovisions() -> None:
    """Legacy Constitution IDs and wrapped Qdrant payloads are accepted unchanged."""
    result = stored_provisions([
        {"payload": {"chunk_id": "article_21_clause_1", "text": " Liberty "}},
        {"chunk_id": "BSA-115(2)(a)", "text": "Evidence"},
        {"chunk_id": "BNS-CH-I", "text": "Chapter"}, {"text": "Missing ID"},
        {"chunk_id": "BNSS-45", "text": ""},
    ])
    assert {item.chunk_id: item.act for item in result} == {
        "article_21_clause_1": "Constitution", "BSA-115(2)(a)": "BSA",
    }


def test_conflicting_source_ids_are_rejected() -> None:
    """Conflicting collections must not silently change a supporting provision."""
    with pytest.raises(ValueError, match="Conflicting"):
        stored_provisions([{"chunk_id": "BNS-1", "text": "one"}, {"chunk_id": "BNS-1", "text": "two"}])


def test_scroll_reads_all_pages_without_vectors() -> None:
    """Sampling does not stop after the first Qdrant page."""
    client = Mock()
    client.scroll.side_effect = [([SimpleNamespace(payload={"chunk_id": "BNS-1"})], "offset"), ([SimpleNamespace(payload={"chunk_id": "BSA-1"})], None)]
    assert len(list(scroll_payloads(client, ["legal_rag"]))) == 2
    assert client.scroll.call_args_list[1].kwargs["offset"] == "offset"
    assert all(not entry.kwargs["with_vectors"] for entry in client.scroll.call_args_list)


@pytest.mark.parametrize("suffix,content", [
    (".jsonl", '{"chunk_id":"BNS-1","text":"text"}\n'),
    (".json", '[{"chunk_id":"BNS-1","text":"text"}]'),
    (".json", '{"points":[{"chunk_id":"BNS-1","text":"text"}]}'),
])
def test_export_formats(tmp_path: Path, suffix: str, content: str) -> None:
    """The deleted-container workflow can read a real stored-payload export."""
    path = tmp_path / ("chunks" + suffix)
    path.write_text(content)
    assert exported_payloads(path)[0]["chunk_id"] == "BNS-1"


def test_default_generation_counts_and_no_auto_approval(tmp_path: Path, catalog_records: list[Provision]) -> None:
    """The full plan produces 120 singles + 15 multis + 10 independent refusals."""
    calls = []

    def draft(prompt: str) -> Draft:
        """Replace the Gemini boundary while exercising the real generation plan."""
        calls.append(prompt)
        outside = "Return intent='out_of_scope'" in prompt
        sources = [] if outside else json.loads(prompt.splitlines()[-1])
        ids = [source["chunk_id"] for source in sources[:2 if "Select 2 or 3" in prompt else 1]]
        return Draft(question=f"Test scenario {len(calls)}?", intent="out_of_scope" if outside else "definition", expected_chunk_ids=ids, supported=not outside, notes="test")

    output = tmp_path / "gold.jsonl"
    assert generate_items(output, catalog_records, draft) == 145
    records = load_gold(output)
    assert Counter(item.act for item in records) == {**{act: 30 for act in ACTS}, "MULTI": 15, "OUT_OF_SCOPE": 10}
    assert all(not item.reviewed for item in records)
    assert all(not item.expected_chunk_ids for item in records if not item.answerable)
    assert all(len(item.expected_chunk_ids) >= 2 for item in records if item.act == "MULTI")
    for intent in ("punishment", "definition", "procedure", "evidence", "rights"):
        assert any(f"Prefer {intent} only" in prompt for prompt in calls)
    assert generate_items(output, catalog_records, Mock(side_effect=AssertionError("Should resume without calling Gemini"))) == 0


def test_generation_resume_preserves_reviewed_content(tmp_path: Path) -> None:
    """An existing reviewed OOS question is never replaced by generation."""
    output = tmp_path / "gold.jsonl"
    reviewed = gold("oos-001", reviewed=True, act="OUT_OF_SCOPE", intent="out_of_scope", answerable=False, expected_chunk_ids=[])
    save_item(output, reviewed)
    drafter = Mock(return_value=Draft(question="Another nonlegal question?", intent="out_of_scope", expected_chunk_ids=[], supported=False, notes="nonlegal"))
    assert generate_items(output, [], drafter, out_of_scope_only=True, out_of_scope_count=2) == 1
    assert load_gold(output)[0] == reviewed


@pytest.mark.parametrize("ids,multiple", [(["FAKE-999"], False), (["BNS-1"], True)])
def test_draft_cannot_invent_support(ids: list[str], multiple: bool) -> None:
    """Unknown IDs and one-source multi questions are invalid, even if Gemini approves."""
    source = Provision(chunk_id="BNS-1", act="BNS", text="source")
    draft = Draft(question="Question?", intent="definition", expected_chunk_ids=ids, supported=True, notes="")
    with pytest.raises(ValueError):
        checked_item("item", draft, [source], multiple)


def test_manifest_binds_source_and_plan(tmp_path: Path) -> None:
    """A changed source snapshot cannot silently relabel a resumed dataset."""
    catalog = tmp_path / "provisions.jsonl"
    catalog.write_text("first snapshot")
    output = tmp_path / "gold.jsonl"
    bind_manifest(output, catalog, 30, 15, 10, 42)
    bind_manifest(output, catalog, 30, 15, 10, 42)
    catalog.write_text("different snapshot")
    with pytest.raises(ValueError, match="changed"):
        bind_manifest(output, catalog, 30, 15, 10, 42)


def test_edits_invalidate_review_and_approval_requires_real_ids() -> None:
    """Human review must be repeated after label edits, not inherited silently."""
    changed = edit_item(gold(reviewed=True), expected_chunk_ids=["BNS-2"])
    assert not changed.reviewed
    with pytest.raises(ValueError, match="missing"):
        approve_item(changed, {})
    source = Provision(chunk_id="BNS-2", act="BNS", text="source")
    assert approve_item(changed, {"BNS-2": source}).reviewed


def test_review_checks_alternate_ids_and_act() -> None:
    """An alternate must exist and cannot silently substitute an unrelated act."""
    item = gold(acceptable_alternates=["BSA-1"])
    sources = {"BNS-1": Provision(chunk_id="BNS-1", act="BNS", text="one"), "BSA-1": Provision(chunk_id="BSA-1", act="BSA", text="two")}
    with pytest.raises(ValueError, match="act"):
        approve_item(item, sources)


def test_storage_preserves_other_reviews_on_update(tmp_path: Path) -> None:
    """Each save merges one item instead of erasing unrelated human approvals."""
    path = tmp_path / "gold.jsonl"
    first = gold("one", reviewed=True)
    save_item(path, first)
    save_item(path, gold("two"))
    save_item(path, edit_item(first, question="Replacement question?"))
    assert {item.id: item for item in load_gold(path)}["one"] == first
    assert len(load_gold(path)) == 2


def test_catalog_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    """A source snapshot must have exactly one definition for each stored ID."""
    path = tmp_path / "catalog.jsonl"
    source = Provision(chunk_id="BNS-1", act="BNS", text="one")
    write_jsonl(path, [source, source])
    with pytest.raises(ValueError, match="Duplicate"):
        load_catalog(path)


def test_metrics_refuse_unreviewed_only_gold(tmp_path: Path) -> None:
    """No reviewed labels means no trustworthy metric report."""
    path = tmp_path / "gold.jsonl"
    save_item(path, gold())
    with pytest.raises(ValueError, match="No reviewed"):
        reviewed_gold(path)
    with pytest.raises(ValueError, match="No reviewed"):
        score_reviewed([gold()], {})


def test_metrics_ignore_unreviewed_even_when_predictions_exist(tmp_path: Path) -> None:
    """Adding an unreviewed success cannot inflate a failed reviewed metric."""
    reviewed, draft = gold("reviewed", True), gold("draft")
    predictions = {"draft": Prediction(id="draft", retrieved_chunk_ids=["BNS-1"], score=100)}
    report = score_reviewed([reviewed, draft], predictions)
    assert report["reviewed_items"] == 1
    assert report["missing_predictions"] == 1
    assert report["retrieval_hit_rate"] == 0
    path = tmp_path / "predictions.jsonl"
    path.write_text('{"id":"draft","score":"malformed but unreviewed"}\n')
    assert reviewed_predictions(path, {"reviewed"}) == {}


def test_metrics_multi_requires_all_supporting_provisions() -> None:
    """Partial multi-source retrieval gets partial recall, not full success."""
    item = gold("multi", True, act="MULTI", expected_chunk_ids=["BNS-1", "BSA-2"], acceptable_alternates=["BSA-3"])
    report = score_reviewed([item], {"multi": Prediction(id="multi", retrieved_chunk_ids=["BNS-1", "BSA-3"], score=90)})
    assert report["retrieval_hit_rate"] == 1
    assert report["all_required_provisions_rate"] == 0
    assert report["mean_provision_recall"] == 0.5
    assert report["mean_citation_precision"] == 1


def test_single_provision_alternate_is_accepted() -> None:
    """A human-approved interchangeable source can satisfy a single target."""
    item = gold("one", True, acceptable_alternates=["BNS-1(2)"])
    report = score_reviewed([item], {"one": Prediction(id="one", retrieved_chunk_ids=["BNS-1(2)"], score=90)})
    assert report["all_required_provisions_rate"] == 1
    assert report["mean_provision_recall"] == 1


@pytest.mark.parametrize("score,refused,success", [(79, False, 1), (80, False, 0), (95, True, 1)])
def test_out_of_scope_refusal_or_low_confidence(score: int, refused: bool, success: int) -> None:
    """Refusal and confidence are explicit signals, not inferred answer accuracy."""
    item = gold("outside", True, act="OUT_OF_SCOPE", intent="out_of_scope", answerable=False, expected_chunk_ids=[])
    report = score_reviewed([item], {item.id: Prediction(id=item.id, retrieved_chunk_ids=[], score=score, refused=refused)})
    assert report["out_of_scope_success_rate"] == success
    assert report["retrieval_hit_rate"] is None


def test_prediction_duplicates_cannot_inflate_metrics(tmp_path: Path) -> None:
    """Repeated results for a reviewed question must not bias denominators."""
    path = tmp_path / "predictions.jsonl"
    prediction = Prediction(id="one", retrieved_chunk_ids=[], score=0)
    write_jsonl(path, [prediction, prediction])
    with pytest.raises(ValueError, match="Duplicate"):
        reviewed_predictions(path, {"one"})


def test_prediction_runner_submits_reviewed_questions_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Even prediction collection must not spend calls on unreviewed drafts."""
    from eval.predict import main
    from legora.config import ClientSettings

    path, output = tmp_path / "gold.jsonl", tmp_path / "predictions.jsonl"
    write_jsonl(path, [gold("reviewed", True), gold("draft")])
    response = Mock()
    response.json.return_value = {
        "answer": "The provided legal corpus does not contain sufficient information to answer this question.",
        "citations": [], "retrieval_debug": {"vector_hits": 0, "reranked": 0, "node_ids": []},
        "evaluation": {"score": 90, "stage": None}, "attempts": 1,
        "latency_ms": {key: 0 for key in ("analysis", "retrieval", "rerank", "graph", "generation", "judge")},
    }
    post = Mock(return_value=response)
    monkeypatch.setattr("eval.predict.requests.post", post)
    monkeypatch.setattr("eval.predict.get_client_settings", lambda: ClientSettings(_env_file=None))
    monkeypatch.setattr("sys.argv", ["predict", "--gold", str(path), "--output", str(output)])
    main()
    post.assert_called_once_with("http://127.0.0.1:8000/query", json={"query": "Test question?"}, timeout=180)
    records = reviewed_predictions(output, {"reviewed"})
    assert set(records) == {"reviewed"}
    assert records["reviewed"].refused


def test_metrics_cli_creates_no_report_without_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI exits unsuccessfully instead of reporting metrics for drafts."""
    from eval.metrics import main

    path, output = tmp_path / "gold.jsonl", tmp_path / "metrics.json"
    write_jsonl(path, [gold()])
    monkeypatch.setattr("sys.argv", ["metrics", "--gold", str(path), "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert not output.exists()
