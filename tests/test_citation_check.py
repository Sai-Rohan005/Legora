"""Crafted statutory answers exercise real extraction and context matching."""

from types import SimpleNamespace

import pytest

from LegalRag.citation_check import canonical_id, check_citations, extract_citations


@pytest.mark.parametrize("answer,expected", [
    ("Section 303 BNS applies.", ["BNS-303"]),
    ("BNSS 45(2) governs the procedure.", ["BNSS-45(2)"]),
    ("Article 21 protects liberty.", ["CONST-21"]),
    ("BNS Section 303(2) and Article 19(1)(a).", ["BNS-303(2)", "CONST-19(1)(a)"]),
    ("Sections 303, 304 and 305 BNS.", ["BNS-303", "BNS-304", "BNS-305"]),
    ("Section 35 of the Bharatiya Nagarik Suraksha Sanhita.", ["BNSS-35"]),
    ("**Section 303** BNS; Article **21**.", ["BNS-303", "CONST-21"]),
    ("[BSA-115(2)(a)] and [article_21_clause_1].", ["BSA-115(2)(a)", "CONST-21(1)"]),
    ("Section 303 IPC and section 303 BNS.", ["IPC-303", "BNS-303"]),
    ("The BNS 2023 is a statute; 303 people applied.", []),
    ("Sec.303 BNS and Art.21.", ["BNS-303", "CONST-21"]),
    ("§ 303 BNS", ["BNS-303"]),
    ("BNSS45(2)", ["BNSS-45(2)"]),
    ("u/s 303 BNS", ["BNS-303"]),
])
def test_extract_citation_forms(answer: str, expected: list[str]) -> None:
    """Normalize supported prose/list/shorthand forms without counting act years."""
    assert [citation.chunk_id for citation in extract_citations(answer)] == expected


def test_repeated_occurrences_count_and_unsupported_ids_are_unique() -> None:
    """Occurrence precision counts every citation while the warning list deduplicates IDs."""
    result = check_citations("Section 303 BNS. Section 999 BNS. Section 999 BNS.", "BNS-303")
    assert result.total_citations == 3
    assert result.supported_count == 1 and result.unsupported_count == 2
    assert result.citation_precision == pytest.approx(1 / 3)
    assert result.unsupported_citations == ["BNS-999"]


def test_uncited_answer_has_undefined_precision() -> None:
    """No citations cannot earn a fabricated perfect citation score."""
    result = check_citations("The provided context is insufficient.", "BNS-303")
    assert result.citation_precision is None
    assert result.total_citations == 0 and result.unsupported_citations == []


def test_root_citation_is_supported_by_retrieved_subsection() -> None:
    """A retained subsection establishes the identity of its parent provision."""
    context = {"statutory_results": [SimpleNamespace(payload={"chunk_id": "BNS-303(2)", "text": "punishment"})]}
    result = check_citations("Section 303 BNS", context)
    assert result.citations[0].status == "citation_supported"


@pytest.mark.parametrize("number,supported", [("303(2)", True), ("303(2)(a)", True), ("303(2)(b)", False), ("303(99)", False)])
def test_specific_subsection_needs_actual_marker(number: str, supported: bool) -> None:
    """A root alone cannot validate invented clause numbers or misplaced alpha clauses."""
    text = "303. Theft.\n(1) Definition.\n(b) Only in clause one.\n(2) Punishment.\n(a) First condition.\n(3) Other provision."
    result = check_citations(f"Section {number} BNS", {"statutory_results": [{"chunk_id": "BNS-303", "text": text}]})
    assert (result.citations[0].status == "citation_supported") is supported


def test_bare_section_inference_requires_unique_context_act() -> None:
    """A bare section is resolved only when returned source IDs disambiguate it."""
    assert check_citations("Section 303 applies", "BNS-303").citations[0].chunk_id == "BNS-303"
    ambiguous = check_citations("Section 303 applies", "BNS-303 BNSS-303")
    assert ambiguous.citations[0].chunk_id is None
    assert ambiguous.citations[0].status == "citation_unsupported"


def test_unknown_statute_and_wrong_provision_kind_are_unsupported() -> None:
    """Do not silently map an unknown Act or a BNS 'Article' to an existing section."""
    result = check_citations("Section 10 of the Companies Act. Article 303 BNS.", "BNS-10 BNS-303")
    assert result.unsupported_count == 2
    assert all(citation.chunk_id is None for citation in result.citations)
    assert check_citations("Section 10 of the companies act", "BNS-10").unsupported_count == 1


def test_only_retained_sources_and_actual_graph_nodes_count() -> None:
    """Query text, unused dense hits and requested graph labels are not evidence."""
    context = {
        "query": "Section 999 BNS", "vector_results": [{"chunk_id": "BNS-999"}],
        "node_ids": ["BNS-999"], "statutory_results": [{"chunk_id": "BNS-303"}],
        "graph_context": {"BNS-999": {"children": [], "ancestors": [{"p": [{"id": "BNSS-45(2)", "text": "procedure"}]}]}},
    }
    result = check_citations("Section 999 BNS; BNSS 45(2).", context)
    assert result.unsupported_citations == ["BNS-999"]
    assert result.supported_count == 1


def test_retrieved_judgment_explicit_statute_reference_counts_as_presence() -> None:
    """An explicit citation present in an actual judgment body can be matched."""
    context = {"judgments": [{"doc": "The court considered <b>Section 303 BNS</b>."}]}
    assert check_citations("Section 303 BNS", context).citation_precision == 1


def test_legacy_constitution_proviso_root_and_clause_aliases() -> None:
    """Normalize existing stored article/proviso IDs without changing the corpus."""
    assert canonical_id("article_19_clause_1_sub_a") == "CONST-19(1)(a)"
    assert check_citations("Article 19", {"statutory_results": [{"chunk_id": "article_19_proviso_1"}]}).citation_precision == 1
    assert check_citations("Article 19(1)(a)", {"statutory_results": [{"chunk_id": "article_19_clause_1_sub_a"}]}).citation_precision == 1


def test_no_implicit_support_for_uncited_legacy_act() -> None:
    """The same number in IPC and BNS is not the same statutory citation."""
    assert check_citations("Section 303 IPC", "BNS-303").unsupported_citations == ["IPC-303"]


def test_plain_context_subsection_checks_respect_provision_boundaries() -> None:
    """A marker under a different provision cannot validate an invented subsection."""
    text = "Section 303 BNS\n(1) Definition.\n(2) Punishment.\nSection 304 BNS\n(99) Other material."
    assert check_citations("Section 303(2) BNS", text).citation_precision == 1
    assert check_citations("Section 303(99) BNS", text).citation_precision == 0


def test_plain_context_child_chunks_do_not_share_markers() -> None:
    """A marker in sibling subsection (2) cannot validate subsection (1)(a)."""
    context = "BNS-303(1)\nDefinition.\nBNS-303(2)\n(a) A condition only in subsection two."
    assert check_citations("Section 303(1)(a) BNS", context).citation_precision == 0


def test_numeric_ranges_are_checked_per_provision() -> None:
    """Range syntax cannot hide an unsupported middle provision."""
    result = check_citations("Sections 303–305 BNS", "BNS-303 BNS-305")
    assert [citation.chunk_id for citation in result.citations] == ["BNS-303", "BNS-304", "BNS-305"]
    assert result.unsupported_citations == ["BNS-304"]
    assert result.citation_precision == pytest.approx(2 / 3)


def test_unbounded_ranges_fail_closed() -> None:
    """Huge or nonnumeric ranges cannot cause unbounded expansion or a false PASS."""
    result = check_citations("Sections 1–99999 BNS", "BNS-1 BNS-99999")
    assert result.unsupported_count >= 1
    assert len(result.citations) <= 3
