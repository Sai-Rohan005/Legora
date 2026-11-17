"""Deterministic statutory citation presence checks, not legal-claim entailment."""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from html import unescape
from typing import Literal

from pydantic import BaseModel, Field

ACT_NAMES = {
    "bns": "BNS", "bharatiya nyaya sanhita": "BNS",
    "bnss": "BNSS", "bharatiya nagarik suraksha sanhita": "BNSS",
    "bsa": "BSA", "bharatiya sakshya adhiniyam": "BSA",
    "constitution": "CONST", "constitution of india": "CONST", "const": "CONST",
    "ipc": "IPC", "indian penal code": "IPC",
    "crpc": "CRPC", "code of criminal procedure": "CRPC",
    "iea": "IEA", "indian evidence act": "IEA",
}
ACT_PATTERN = "|".join(re.escape(name).replace(r"\ ", r"\s+") for name in sorted(ACT_NAMES, key=len, reverse=True))
ACT_RE = re.compile(rf"\b(?P<act>{ACT_PATTERN})\b(?:,?\s+(?:18|19|20)\d{{2}})?", re.I)
NUMBER = r"\d+[A-Za-z]?(?:\s*\(\s*[A-Za-z0-9]+\s*\))*"
REFERENCE_RE = re.compile(rf"(?<!\w)(?P<label>sections?|secs?\.?|s\.|u/s|articles?|arts?\.?|§{{1,2}})\s*(?P<numbers>{NUMBER}(?:\s*(?:,|and|&|to|[-–—])\s*{NUMBER})*)(?!\w)", re.I)
SHORTHAND_RE = re.compile(rf"\b(?P<act>{ACT_PATTERN})[-\s]*(?P<number>\d{{1,3}}[A-Za-z]?(?:\s*\(\s*[A-Za-z0-9]+\s*\))*)(?!\w)", re.I)
LINK_RE = re.compile(r"^[\s,.:—()\-]*(?:(?:of|the|under|in)\s*)*$", re.I)


def canonical_id(identifier: str) -> str:
    """Normalize supported stored IDs, retaining exact subsection specificity."""
    legacy = re.fullmatch(r"article_(\d+[A-Z]*)((?:_(?:clause|sub|roman|proviso|explanation)_[A-Za-z0-9]+)*)", identifier, re.I)
    if legacy:
        result = "CONST-" + legacy[1].upper()
        for label, value in re.findall(r"_(clause|sub|roman|proviso|explanation)_([A-Za-z0-9]+)", legacy[2], re.I):
            if label.lower() == "proviso":
                result += f"(PROVISO-{value})"
            elif label.lower() == "explanation":
                result += f"-EXP-{value}"
            else:
                result += "(" + (value.upper() if value[0].isdigit() else value.lower()) + ")"
        return result
    canonical = re.fullmatch(r"([A-Z]+)-(\d+[A-Z]*(?:\([^)]*\))*)(.*)", identifier, re.I)
    if canonical:
        return canonical[1].upper() + "-" + normalized_number(canonical[2]) + canonical[3]
    return identifier


def root_id(identifier: str) -> str:
    """Remove subsection/explanation/illustration suffixes from canonical IDs."""
    identifier = canonical_id(identifier)
    match = re.match(r"^([A-Z]+-\d+[A-Z]*)(?=$|\(|-)", identifier)
    return match[1] if match else identifier


def normalized_number(number: str) -> str:
    """Normalize whitespace/case while preserving numeric clause-letter suffixes."""
    number = re.sub(r"\s+", "", number)
    base = number.split("(", 1)[0].upper()
    suffix = re.sub(r"\(([^)]+)\)", lambda match: "(" + (match[1].upper() if match[1][0].isdigit() else match[1].lower()) + ")", number[len(base):])
    return base + suffix


@dataclass(frozen=True)
class CitationReference:
    """One citation occurrence, including unresolved statutory identities."""

    text: str
    number: str
    act: str | None
    chunk_id: str | None
    root_id: str | None


class CheckedCitation(BaseModel):
    """A normalized citation and its deterministic retrieved-context status."""

    text: str
    number: str
    act: str | None
    chunk_id: str | None
    root_id: str | None
    status: Literal["citation_supported", "citation_unsupported"]


class CitationReport(BaseModel):
    """Occurrence precision is undefined when the answer contains no citations."""

    citations: list[CheckedCitation]
    unsupported_citations: list[str]
    citation_precision: float | None = Field(ge=0, le=1)
    total_citations: int = Field(ge=0)
    supported_count: int = Field(ge=0)
    unsupported_count: int = Field(ge=0)


def extract_citations(answer: str, known_ids: Collection[str] = ()) -> list[CitationReference]:
    """Extract section/article lists and act-first shorthand, retaining ambiguous references."""
    answer = answer.replace("*", "").replace("`", "").replace("__", "")
    acts = list(ACT_RE.finditer(answer))
    codes = {ACT_NAMES[" ".join(match["act"].lower().split())] for match in acts}
    covered: list[tuple[int, int]] = []
    occurrences: list[tuple[int, CitationReference]] = []
    for reference in REFERENCE_RE.finditer(answer):
        adjacent = []
        for act in acts:
            between = answer[reference.end():act.start()] if act.start() >= reference.end() else answer[act.end():reference.start()] if act.end() <= reference.start() else None
            if between is not None and LINK_RE.fullmatch(between):
                adjacent.append(act)
        adjacent_codes = {ACT_NAMES[" ".join(match["act"].lower().split())] for match in adjacent}
        code = next(iter(adjacent_codes)) if len(adjacent_codes) == 1 else None
        start = min([reference.start(), *(match.start() for match in adjacent)])
        end = max([reference.end(), *(match.end() for match in adjacent)])
        unknown = None
        if not adjacent:
            tail = answer[reference.end():]
            unknown = re.match(r"\s+(?:of|under)\s+(?:the\s+)?([A-Za-z][A-Za-z '\-]{2,80}?\b(?:Act|Code|Treaty|Regulation))\b", tail, re.I)
            unknown = unknown or re.match(r"\s*([A-Z][A-Za-z '\-]{2,80}?\b(?:Act|Code|Treaty|Regulation))\b", tail)
        if unknown:
            end = reference.end() + unknown.end()
        if code is None and not adjacent_codes and not unknown:
            if reference["label"].lower().startswith("art"):
                code = "CONST"
            elif len(codes) == 1:
                code = next(iter(codes))
        number_matches = list(re.finditer(NUMBER, reference["numbers"]))
        numbers: list[tuple[int, str]] = []
        for index, match in enumerate(number_matches):
            number = normalized_number(match[0])
            if index:
                previous = number_matches[index - 1]
                separator = reference["numbers"][previous.end():match.start()].strip().lower()
                if separator in {"to", "-", "–", "—"}:
                    prior = normalized_number(previous[0])
                    if prior.isdigit() and number.isdigit() and 0 <= int(number) - int(prior) <= 100:
                        numbers.extend((match.start(), str(value)) for value in range(int(prior) + 1, int(number)))
                    else:
                        occurrences.append((reference.start(), CitationReference(answer[start:end], prior + "-" + number, code, None, None)))
            numbers.append((match.start(), number))
        for offset, number in numbers:
            resolved = code
            if resolved is None and not unknown and not adjacent_codes:
                roots = {root_id(value) for value in known_ids}
                possible = {value.split("-", 1)[0] for value in roots if value.endswith("-" + number.split("(", 1)[0])}
                if len(possible) == 1:
                    resolved = next(iter(possible))
            kind_valid = resolved is not None and (reference["label"].lower().startswith("art") == (resolved == "CONST"))
            identifier = f"{resolved}-{number}" if kind_valid else None
            occurrences.append((reference.start() + offset, CitationReference(answer[start:end], number, resolved, identifier, root_id(identifier) if identifier else None)))
        covered.append((start, end))
    for match in SHORTHAND_RE.finditer(answer):
        if any(start <= match.start() < end for start, end in covered):
            continue
        code = ACT_NAMES[" ".join(match["act"].lower().split())]
        number = normalized_number(match["number"])
        identifier = f"{code}-{number}"
        occurrences.append((match.start(), CitationReference(match[0], number, code, identifier, root_id(identifier))))
    for match in re.finditer(r"\barticle_\d+[A-Z]*(?:_(?:clause|sub|roman|proviso|explanation)_[A-Za-z0-9]+)*(?!\w)", answer, re.I):
        identifier = canonical_id(match[0])
        occurrences.append((match.start(), CitationReference(match[0], identifier.split("-", 1)[1], "CONST", identifier, root_id(identifier))))
    return [reference for _, reference in sorted(occurrences, key=lambda pair: pair[0])]


def _source_records(value: object) -> list[tuple[str, str]]:
    """Read actual returned source properties, ignoring lookup keys and query metadata."""
    records = []
    if hasattr(value, "payload"):
        return _source_records(value.payload)
    if hasattr(value, "nodes"):
        return _source_records(value.nodes)
    if isinstance(value, Mapping):
        identifier = value.get("chunk_id") or value.get("id")
        if isinstance(identifier, str) and re.match(r"^(?:[A-Z]+-\d|article_\d)", identifier, re.I):
            records.append((canonical_id(identifier), str(value.get("text") or value.get("source_text") or "")))
        for child in value.values():
            if not isinstance(child, (str, int, float, bool)) and child is not None:
                records.extend(_source_records(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            records.extend(_source_records(child))
    return records


def _subsection_present(text: str, suffix: str) -> bool:
    """Require each requested marker inside its parent's block, not elsewhere in the section."""
    block = text
    for token in re.findall(r"\(([^)]+)\)", suffix):
        siblings = r"\d+[A-Za-z]?" if token[0].isdigit() else r"[a-z]" if len(token) == 1 else r"[ivxlcdm]+"
        pattern = re.compile(rf"(?:^|\n|[;:—])\s*\((?P<token>{siblings})\)", re.I)
        matches = list(pattern.finditer(block))
        chosen = next((index for index, match in enumerate(matches) if match["token"].lower() == token.lower()), None)
        if chosen is None:
            return False
        start = matches[chosen].end()
        end = matches[chosen + 1].start() if chosen + 1 < len(matches) else len(block)
        block = block[start:end]
    return True


def _text_records(text: str) -> list[tuple[str, str]]:
    """Support plain-context callers with explicit citations/IDs actually written in that text."""
    text = text.replace("*", "").replace("`", "").replace("__", "")
    anchors = {(match.start(), canonical_id(match[0])) for match in re.finditer(
        r"\b(?:BNS|BNSS|BSA|CONST|IPC|CRPC|IEA)-\d+[A-Z]*(?:\([^)]*\))*|\barticle_\d+[A-Z]*(?:_(?:clause|sub|roman|proviso|explanation)_[A-Za-z0-9]+)*", text, re.I
    )}
    for reference in extract_citations(text):
        if reference.chunk_id:
            for match in re.finditer(re.escape(reference.text), text):
                anchors.add((match.start(), reference.chunk_id))
    ordered = sorted(anchors)
    records = []
    for index, (start, identifier) in enumerate(ordered):
        end = next((position for position, following in ordered[index + 1:] if position > start and following != identifier), len(text))
        records.append((identifier, text[start:end]))
    return records


def check_citations(answer: str, context: Mapping | str) -> CitationReport:
    """Verify citation identity against retained passages/graph nodes, without an LLM call."""
    if isinstance(context, str):
        sources = _text_records(context)
    else:
        sources = _source_records(context.get("statutory_results", [])) + _source_records(context.get("graph_context", {}))
        for judgment in context.get("judgments", []):
            if isinstance(judgment, Mapping):
                text = judgment.get("doc") or judgment.get("text") or judgment.get("content") or ""
                if isinstance(text, str):
                    sources.extend(_text_records(unescape(re.sub(r"<[^>]+>", " ", text))))
        # Some callers supply only the final prompt context. Never inspect the query,
        # unretrieved vector hits, or requested graph root labels as evidence.
        if not sources and not context.get("statutory_results") and not context.get("graph_context"):
            sources = _text_records(str(context.get("final_context", "")))
    identifiers = {identifier for identifier, _ in sources}
    checked = []
    for reference in extract_citations(answer, identifiers):
        supported = False
        if reference.chunk_id:
            for identifier, text in sources:
                if identifier == reference.chunk_id or identifier.startswith(reference.chunk_id + "(") or (reference.chunk_id == root_id(identifier)):
                    supported = True
                elif reference.chunk_id.startswith(identifier + "("):
                    supported = _subsection_present(text, reference.chunk_id[len(identifier):])
                if supported:
                    break
        checked.append(CheckedCitation(**reference.__dict__, status="citation_supported" if supported else "citation_unsupported"))
    unsupported = list(dict.fromkeys(citation.chunk_id or citation.text for citation in checked if citation.status == "citation_unsupported"))
    supported_count = sum(citation.status == "citation_supported" for citation in checked)
    return CitationReport(
        citations=checked, unsupported_citations=unsupported,
        citation_precision=supported_count / len(checked) if checked else None,
        total_citations=len(checked), supported_count=supported_count,
        unsupported_count=len(checked) - supported_count,
    )
