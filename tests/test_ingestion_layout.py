"""Regression cases for printed layout and conflicting child identities during ingestion."""

from pathlib import Path
from shutil import copyfile
from unittest.mock import Mock

import pytest

from db.graph_builders.bns_graph_builder import BNSGraphBuilder
from db.parsers.constitution.article_parser import ArticleParser
from db.parsers.constitution.constitution_parser import ConstitutionParser
from scripts.ingest import prepare_corpus
from scripts.statute_layout import prepare_source


def corpus_directory(directory: Path, bns: str) -> Path:
    """Combine an isolated synthetic regression with the other small structural fixtures."""
    for name in ("bnss", "bsa", "constitution"):
        copyfile(Path(__file__).parent / "fixtures" / f"{name}.txt", directory / f"{name}.txt")
    (directory / "bns.txt").write_text(bns)
    return directory


AMBIGUOUS_BNS = """CHAPTER I
GENERAL
2. Definitions.—The following test definitions apply.
(1) First definition text.
Explanation 1.—First explanation text.
(2) Second definition text.
Explanation 1.—A differently scoped explanation text.
3. Other provision.—Unaffected complete provision text.
(1) An ordinary subsection.
"""


def test_duplicate_children_keep_complete_parent_in_both_stores(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Never arbitrarily select one explanation or invent a new statutory number."""
    directory = corpus_directory(tmp_path, AMBIGUOUS_BNS)
    bns = prepare_corpus(directory)[0]
    ids = {chunk["chunk_id"] for chunk in bns.chunks}
    assert ids == {"BNS-2", "BNS-3", "BNS-3(1)"}
    parent = next(chunk for chunk in bns.chunks if chunk["chunk_id"] == "BNS-2")
    assert "First explanation text" in parent["text"] and "differently scoped explanation" in parent["text"]
    assert (directory / "bns.txt").read_text() == AMBIGUOUS_BNS
    graph = Mock()
    BNSGraphBuilder(graph).build(bns.document)
    nodes = {call.kwargs["node_id"] for call in graph.merge_node.call_args_list}
    assert "BNS-2" in nodes and "BNS-2(1)" not in nodes and "BNS-2-EXPL-1" not in nodes
    assert "BNS-3(1)" in nodes
    assert "indexing full provision only in both stores" in caplog.text


def test_strict_children_rejects_fallback_with_conflicting_ids(tmp_path: Path) -> None:
    """Strict audits can require fully unambiguous child parsing before any writes."""
    with pytest.raises(ValueError, match="BNS-2-EXP-1"):
        prepare_corpus(corpus_directory(tmp_path, AMBIGUOUS_BNS), strict_children=True)


def test_duplicate_root_provisions_remain_a_hard_failure(tmp_path: Path) -> None:
    """A whole provision is never dropped or chosen arbitrarily to bypass validation."""
    source = "CHAPTER I\nGENERAL\n2. First heading.—First body.\n2. Second heading.—Other body."
    with pytest.raises(ValueError, match="Duplicate root provision BNS-2"):
        prepare_corpus(corpus_directory(tmp_path, source))


@pytest.mark.parametrize("act,heading", [("bnss", "THE FIRST SCHEDULE"), ("bsa", "THE SCHEDULE")])
def test_schedules_cannot_become_clauses_of_the_last_section(act: str, heading: str) -> None:
    """Keep ordinary inline schedule references; exclude the separate unsupported schedule body."""
    body = "2. Last section.—See THE FIRST SCHEDULE for details.\n(1) Genuine subsection.\n"
    source = body + heading + "\n(1) A schedule paragraph, not a subsection."
    assert prepare_source(act, source).strip() == body.strip()


def test_constitution_footer_cleanup_preserves_next_page_and_sources() -> None:
    """Printed editorial numbering must not be mistaken for repeated article identities."""
    source = """PART I
GENERAL
1. First article heading.—Operative text.
______________________________________________
1. Subs. by an amendment (editorial note).
An editorial continuation line.
42
THE CONSTITUTION OF INDIA
2. Second article heading.—Further operative text.
"""
    prepared = prepare_source("constitution", source)
    assert "editorial" not in prepared
    assert "First article heading" in prepared and "Second article heading" in prepared
    assert "editorial" in source


def test_plain_article_after_separator_is_not_removed_as_a_footnote() -> None:
    """The cleanup requires editorial layout instead of removing arbitrary numbered provisions."""
    source = "______________________________________________\n1. First article heading.—Operative text."
    assert "1. First article heading" in prepare_source("constitution", source)


def test_constitution_schedules_and_appendices_are_not_article_1() -> None:
    """Schedule paragraphs stay in their own namespace and amendment appendices are excluded."""
    source = """PART I
GENERAL
1. First article heading.—Operative text.
FIRST SCHEDULE
1. A schedule paragraph with a long heading.
APPENDIX I
PART I
AMENDMENT
1. Amendment provision with a long heading.
"""
    document = ConstitutionParser().parse(source)
    assert len(document.parts) == 1
    assert [article.article_no for article in document.parts[0].articles] == ["1"]
    assert "schedule paragraph" not in document.parts[0].articles[0].text
    assert len(document.schedules) == 1
    assert "Amendment provision" not in document.schedules[0].text


def test_unseparated_editorial_note_is_filtered_before_article_boundaries() -> None:
    """A continuing editorial note neither creates another article nor truncates its parent."""
    source = """1. First article heading.—Operative text.
1. In exercise of editorial powers a historical note follows.
Continuation of the note.
2. Second article heading.—Other operative text.
"""
    articles = ArticleParser().extract_articles(source)
    assert [article["article_no"] for article in articles] == ["1", "2"]
    assert "Continuation of the note" in articles[0]["text"]
