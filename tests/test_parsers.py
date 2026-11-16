"""Parse small statute texts through real parsers, reference extractors, and chunkers."""

from importlib import import_module
from typing import Any

import pytest

from db.parsers.constitution.constitution_parser import ConstitutionParser
from db.parsers.constitution.chunker import LegalChunker as ConstitutionChunker

STATUTES = (("bns", "BNSParser", "303", "304"),
            ("bnss", "BNSSParser", "35", "36"),
            ("bsa", "BSAParser", "2", "3"))


def parse_statute(name: str, class_name: str, text: str) -> Any:
    """Invoke a statute's public document parser without substituting its stages."""
    module = import_module(f"db.parsers.{name}.{name}_parser")
    return getattr(module, class_name)().parse(text)


@pytest.mark.parametrize("name,class_name,first,second", STATUTES)
def test_section_hierarchy_and_boundaries(name: str, class_name: str, first: str, second: str, statute_text: dict[str, str]) -> None:
    """Each section belongs to its chapter and cannot absorb the next section."""
    document = parse_statute(name, class_name, statute_text[name])
    assert len(document.chapters) == 1
    chapter = document.chapters[0]
    assert [section.section_no for section in chapter.sections] == [first, second]
    section = chapter.sections[0]
    assert [clause.clause_no for clause in section.clauses] == ["1", "2"]
    assert f"{second}." not in section.text
    assert "Provided that" in section.text
    assert "reference-extraction fixture" not in section.text


@pytest.mark.parametrize("name,class_name,first,second", STATUTES)
def test_chunks_keep_section_and_clause_parent_ids(name: str, class_name: str, first: str, second: str, statute_text: dict[str, str]) -> None:
    """A parsed subsection produces a stable chunk ID with its actual parent."""
    document = parse_statute(name, class_name, statute_text[name])
    chunker = import_module(f"db.parsers.{name}.chunker").LegalChunker()
    chunks = chunker.chunk_document(document)
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    root = f"{name.upper()}-{first}"
    assert by_id[root].parent_id is None
    assert by_id[f"{root}(2)"].parent_id == root
    assert by_id[f"{root}(2)"].level == "clause"
    assert by_id[f"{root}(2)"].text.startswith("(2)")
    assert by_id[f"{root}(2)"].text in by_id[f"{root}(2)"].enriched_text
    assert f"{name.upper()}-{second}" in by_id
    assert len(by_id) == len(chunks), "Chunk identifiers must be unique"


@pytest.mark.parametrize("name,class_name,first,second", STATUTES)
def test_document_reference_has_correct_source_and_target(name: str, class_name: str, first: str, second: str, statute_text: dict[str, str]) -> None:
    """Cross-references are attached to the referencing section, not its neighbor."""
    sections = parse_statute(name, class_name, statute_text[name]).chapters[0].sections
    assert sections[0].references == []
    assert sections[1].references == [{
        "source_section": second, "target_section": first, "reference_type": "section",
    }]


@pytest.mark.parametrize("name,class_name,first,second", STATUTES)
def test_explanation_is_separate_from_following_section(name: str, class_name: str, first: str, second: str, statute_text: dict[str, str]) -> None:
    """Explanations stop before illustrations and the next section header."""
    sections = parse_statute(name, class_name, statute_text[name]).chapters[0].sections
    assert len(sections[0].explanations) == 1
    explanation = sections[0].explanations[0]
    assert explanation.explanation_no == "1"
    assert explanation.text.startswith("Explanation 1")
    assert "Illustrations." not in explanation.text
    assert f"{second}." not in explanation.text
    assert sections[1].explanations == []


@pytest.mark.parametrize("name,class_name", (("bnss", "BNSSParser"), ("bsa", "BSAParser")))
def test_alpha_subclauses_survive_parse_and_chunking(name: str, class_name: str, statute_text: dict[str, str]) -> None:
    """Numeric-to-alpha hierarchy produces distinct sibling chunks."""
    document = parse_statute(name, class_name, statute_text[name])
    section = document.chapters[0].sections[0]
    assert [sub.sub_clause_no for sub in section.clauses[0].sub_clauses] == ["a", "b"]
    chunks = import_module(f"db.parsers.{name}.chunker").LegalChunker().chunk_document(document)
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    parent = f"{name.upper()}-{section.section_no}(1)"
    for letter in ("a", "b"):
        assert by_id[f"{parent}({letter})"].parent_id == parent
        assert by_id[f"{parent}({letter})"].text.startswith(f"({letter})")
    assert "(b)" not in by_id[f"{parent}(a)"].text


def test_bns_illustrations_are_not_subclauses(statute_text: dict[str, str]) -> None:
    """Alphabetic illustration labels must not become legal subclause chunks."""
    document = parse_statute("bns", "BNSParser", statute_text["bns"])
    section = document.chapters[0].sections[0]
    assert "Illustrations." in section.text
    assert "Z's dog" in section.text
    assert all(not clause.sub_clauses for clause in section.clauses)


def test_bsa_part_chapter_and_illustration_hierarchy(statute_text: dict[str, str]) -> None:
    """BSA parts contain chapters and illustration labels retain their own IDs."""
    document = parse_statute("bsa", "BSAParser", statute_text["bsa"])
    assert document.parts[0].part_no == "I"
    assert document.parts[0].chapters[0] is document.chapters[0]
    section = document.chapters[0].sections[0]
    assert [item.illustration_no for item in section.illustrations] == ["a", "b"]
    assert "map" not in section.illustrations[0].text
    chunks = import_module("db.parsers.bsa.chunker").LegalChunker().chunk_document(document)
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    assert by_id["BSA-2-ILL-a"].parent_id == "BSA-2"
    assert by_id["BSA-2-ILL-b"].level == "illustration"
    assert by_id["BSA-2-EXP-1"].level == "explanation"


def test_bsa_without_part_header_still_parses_chapters(statute_text: dict[str, str]) -> None:
    """The documented part-free BSA path still populates sections."""
    text = statute_text["bsa"].split("CHAPTER", 1)[1]
    document = parse_statute("bsa", "BSAParser", "CHAPTER" + text)
    assert document.parts == []
    assert [section.section_no for section in document.chapters[0].sections] == ["2", "3"]


def test_constitution_part_article_clause_and_proviso_hierarchy(statute_text: dict[str, str]) -> None:
    """Article clauses, provisos, explanations, and references remain distinct."""
    parser = ConstitutionParser()
    document = parser.parse(statute_text["constitution"])
    assert "WE, THE PEOPLE" in document.preamble.text
    assert document.parts[0].part_no == "III"
    first, second = document.parts[0].articles
    assert (first.article_no, second.article_no) == ("19", "21")
    assert [clause.clause_no for clause in first.clauses] == ["1", "2"]
    assert [sub.sub_clause_no for sub in first.clauses[0].sub_clauses] == ["a", "b"]
    assert len(first.provisos) == 1
    assert "Explanation" not in first.provisos[0].text
    assert first.explanations[0].explanation_no == "I"
    assert first.references[0].reference_value == "a"
    assert [(ref.reference_type, ref.reference_value) for ref in second.references] == [("ARTICLE", "19")]
    assert parser.validate(document) == []


def test_constitution_chunk_ids_and_metadata(statute_text: dict[str, str]) -> None:
    """The legacy Constitution ID format retains article/clause provenance."""
    document = ConstitutionParser().parse(statute_text["constitution"])
    chunks = ConstitutionChunker().chunk_constitution(document)
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    assert set(by_id) == {
        "article_19", "article_19_clause_1", "article_19_clause_1_sub_a",
        "article_19_clause_1_sub_b", "article_19_clause_2", "article_19_proviso_1",
        "article_19_explanation_1", "article_21",
    }
    sub = by_id["article_19_clause_1_sub_a"]
    assert sub.metadata["part_no"] == "III"
    assert sub.metadata["article_no"] == "19"
    assert sub.metadata["clause_no"] == "1"
    assert sub.metadata["sub_clause_no"] == "a"
    assert "freedom of speech" in sub.text
    assert by_id["article_19_proviso_1"].chunk_type == "proviso"
    assert by_id["article_21"].references


def test_constitution_chapter_and_schedule_boundaries() -> None:
    """Schedules must not be parsed as articles in the preceding Part."""
    text = "PART V\nTHE UNION\nCHAPTER I—THE EXECUTIVE\n52. The President of India.\nThere shall be a President of India.\nFIRST SCHEDULE\nTHE STATES\n1. Andhra Pradesh.\n2. Assam.\n"
    document = ConstitutionParser().parse(text)
    assert document.parts[0].articles == []
    assert [article.article_no for article in document.parts[0].chapters[0].articles] == ["52"]
    assert document.schedules[0].schedule_no == "FIRST"
    assert [paragraph.paragraph_no for paragraph in document.schedules[0].paragraphs] == ["1", "2"]
    chunks = ConstitutionChunker().chunk_constitution(document)
    assert {chunk.chunk_id for chunk in chunks} == {"article_52", "schedule_FIRST"}


@pytest.mark.parametrize("name,class_name", [(name, cls) for name, cls, _, _ in STATUTES])
def test_empty_statute_does_not_invent_sections(name: str, class_name: str) -> None:
    """Unstructured or empty input cannot produce a fictitious hierarchy."""
    assert parse_statute(name, class_name, "").chapters == []


@pytest.mark.parametrize("name", ("bns", "bnss", "bsa"))
def test_reference_lists_deduplicate_without_losing_source(name: str) -> None:
    """Singular/plural references preserve targets and deduplicate repetitions."""
    module = "reference_parser" if name == "bsa" else "reference_extractor"
    extractor = import_module(f"db.parsers.{name}.{module}").ReferenceExtractor()
    references = extractor.extract_references("Sections 303, 304 and 305; section 303.", "35")
    assert [ref["target_section"] for ref in references] == ["303", "304", "305", "303"]
    unique = extractor.unique_references(references)
    assert [ref["target_section"] for ref in unique] == ["303", "304", "305"]
    assert {ref["source_section"] for ref in unique} == {"35"}
    assert extractor.validate_references(unique) == []


@pytest.mark.parametrize("name", ("bns", "bnss", "bsa"))
@pytest.mark.parametrize("marker,number", (("", None), ("II", "2"), ("3", "3")))
def test_explanation_numbers_and_stop_markers(name: str, marker: str, number: str | None) -> None:
    """Roman, numeric, and unnumbered explanations stop at illustrations."""
    module = "explaination_parser" if name == "bsa" else "explanation_parser"
    parser = import_module(f"db.parsers.{name}.{module}").ExplanationParser()
    text = f"Explanation {marker}.— Meaning of the preceding provision.\nIllustrations.\n(a) Separate illustrative material."
    explanation = parser.extract_explanations(text)[0]
    assert explanation.explanation_no == number
    assert "Illustrations" not in explanation.text


@pytest.mark.parametrize("name", ("bns", "bnss", "bsa"))
def test_inline_numeric_and_alpha_markers(name: str) -> None:
    """Inline OCR layout is normalized without losing sibling subclauses."""
    parser = import_module(f"db.parsers.{name}.clause_parser").ClauseParser()
    clauses = parser.parse_clauses("(2) The conditions are—(a) first condition;(b) second condition.")
    assert [clause.clause_no for clause in clauses] == ["2"]
    assert [sub.sub_clause_no for sub in clauses[0].sub_clauses] == ["a", "b"]


def test_constitution_nested_roman_clauses() -> None:
    """Roman clauses stay under their alpha parent instead of becoming siblings."""
    from db.parsers.constitution.clause_parser import ClauseParser

    clauses = ClauseParser().parse_clauses("(1) Conditions—\n(a) first category—\n(i) first detail;\n(ii) second detail.\n(b) second category.")
    assert [sub.sub_clause_no for sub in clauses[0].sub_clauses] == ["a", "b"]
    assert [roman.roman_no for roman in clauses[0].sub_clauses[0].roman_clauses] == ["i", "ii"]
