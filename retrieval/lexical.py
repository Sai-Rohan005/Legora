"""BM25 ranking, reciprocal rank fusion, and explicitly qualified provision lookup."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from rank_bm25 import BM25Okapi


@dataclass(frozen=True)
class RetrievalHit:
    """A payload-compatible hit; fusion never mutates a dense result's score."""

    payload: dict[str, Any]
    score: float = 0.0
    id: str | int | None = None


def tokenize(text: str) -> list[str]:
    """Case-fold Unicode words and numbers, preserving legal section-number terms."""
    return re.findall(r"\w+", text.casefold())


def document_name(payload: dict[str, Any]) -> str | None:
    """Recognize act metadata, with ID fallback for legacy Constitution payloads."""
    name = str(payload.get("document", "")).strip().lower()
    if name in {"bns", "bnss", "bsa", "constitution"}:
        return name
    identifier = str(payload.get("chunk_id", ""))
    for prefix, document in (("BNSS-", "bnss"), ("BNS-", "bns"), ("BSA-", "bsa"), ("CONST-", "constitution"), ("article_", "constitution")):
        if identifier.startswith(prefix):
            return document
    return None


class BM25Retriever:
    """Build one in-memory BM25 index from the same Qdrant collection payloads."""

    def __init__(self, hits: Iterable[RetrievalHit]) -> None:
        """Index text plus stored IDs, excluding empty or unidentified chunks."""
        unique = {}
        for hit in hits:
            identifier = hit.payload.get("chunk_id")
            text = hit.payload.get("enriched_text") or hit.payload.get("text")
            if not isinstance(identifier, str) or not identifier or not isinstance(text, str) or not text.strip():
                continue
            if identifier in unique and unique[identifier].payload != hit.payload:
                raise ValueError(f"Conflicting payloads for BM25 chunk {identifier}")
            unique.setdefault(identifier, hit)
        self.hits = [unique[key] for key in sorted(unique)]
        corpus = [tokenize(hit.payload["chunk_id"] + " " + (hit.payload.get("enriched_text") or hit.payload["text"])) for hit in self.hits]
        self.tokens = [set(tokens) for tokens in corpus]
        self.index = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, document: str | None = None, k: int = 10) -> list[RetrievalHit]:
        """Rank matching chunks only; zero-overlap records cannot pad sparse results."""
        tokens = tokenize(query)
        if self.index is None or not tokens or k <= 0:
            return []
        scores = self.index.get_scores(tokens)
        query_terms = set(tokens)
        matches = [
            RetrievalHit(payload=hit.payload, score=float(scores[index]), id=hit.id)
            for index, hit in enumerate(self.hits)
            if query_terms & self.tokens[index] and (document is None or document_name(hit.payload) == document.strip().lower())
        ]
        return sorted(matches, key=lambda hit: (-hit.score, hit.payload["chunk_id"]))[:k]


def reciprocal_rank_fusion(rankings: Sequence[Sequence[Any]], k: int = 60, limit: int | None = None) -> list[RetrievalHit]:
    """Sum 1/(k+rank) per distinct chunk per ranking, with deterministic ties."""
    if k < 1:
        raise ValueError("RRF k must be positive")
    scores: dict[str, float] = {}
    sources = {}
    for ranking in rankings:
        seen = set()
        for rank, point in enumerate(ranking, 1):
            identifier = (point.payload or {}).get("chunk_id")
            if not identifier or identifier in seen:
                continue
            seen.add(identifier)
            sources.setdefault(identifier, point)
            scores[identifier] = scores.get(identifier, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores, key=lambda identifier: (-scores[identifier], identifier))
    if limit is not None:
        ordered = ordered[:max(0, limit)]
    return [RetrievalHit(payload=sources[key].payload, score=scores[key], id=getattr(sources[key], "id", None)) for key in ordered]


ACT_PATTERN = r"BNSS|BNS|BSA|Constitution(?:\s+of\s+India)?|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|Bharatiya\s+Nyaya\s+Sanhita|Bharatiya\s+Sakshya\s+Adhiniyam"
NUMBER_PATTERN = r"\d+[A-Za-z]?(?:\(\d+[A-Za-z]?\))?(?:\([a-zivxlcdm]+\))*"
PROVISION_PATTERN = r"(?:sections?|sec\.?|articles?)\s+"


def act_code(text: str) -> str:
    """Convert an explicitly written act name to its canonical stored-ID prefix."""
    text = text.casefold()
    if "nagarik" in text or text == "bnss":
        return "BNSS"
    if "nyaya" in text or text == "bns":
        return "BNS"
    if "sakshya" in text or text == "bsa":
        return "BSA"
    return "CONST"


def explicit_provisions(query: str) -> list[list[str]]:
    """Parse qualified section/article references; never guess an act from a bare number."""
    acts = list(re.finditer(rf"\b({ACT_PATTERN})\b", query, re.I))
    references = list(re.finditer(rf"\b{PROVISION_PATTERN}({NUMBER_PATTERN})(?!\w)", query, re.I))
    unique_acts = {act_code(match[1]) for match in acts}
    qualified = []
    for reference in references:
        number = reference[1]
        code = None
        # In multi-act queries, require an adjacent act with only linking words.
        for match in acts:
            between = query[reference.end():match.start()] if match.start() >= reference.end() else query[match.end():reference.start()] if match.end() <= reference.start() else None
            if between is not None and re.fullmatch(r"[\s,.:—-]*(?:(?:of|the|under|in)\s*)*", between, re.I):
                code = act_code(match[1])
                break
        if code is None and len(unique_acts) == 1:
            code = next(iter(unique_acts))
        if code is None:
            continue
        base = number.split("(", 1)[0].upper()
        suffix = re.sub(r"\(([^)]+)\)", lambda match: "(" + (match[1].upper() if match[1][0].isdigit() else match[1].lower()) + ")", number[len(base):])
        aliases = [f"{code}-{base}{suffix}"]
        if code == "CONST":
            parts = re.findall(r"\(([^)]+)\)", suffix)
            legacy = f"article_{base}"
            for label, value in zip(("clause", "sub", "roman"), parts):
                legacy += f"_{label}_{value}"
            aliases.append(legacy)
        if aliases not in qualified:
            qualified.append(aliases)
    return qualified


def prepend_exact(points: Sequence[Any], exact: Sequence[Any], limit: int) -> list[Any]:
    """Pin actual exact-lookup hits in mention order without duplicates or budget growth."""
    result, seen = [], set()
    for point in [*exact, *points]:
        identifier = (point.payload or {}).get("chunk_id")
        if identifier and identifier not in seen:
            seen.add(identifier)
            result.append(point)
    return result[:max(0, limit)]
