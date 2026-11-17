"""Validate and upsert all four statutes using the existing parsers and graph builders."""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from legora.logging import setup_logging
from scripts.statute_layout import prepare_source

logger = logging.getLogger(__name__)
STATUTES = {"bns": "BNS", "bnss": "BNSS", "bsa": "BSA", "constitution": "Constitution"}


@dataclass
class ParsedStatute:
    """One parsed document shared by vector chunking and graph generation."""

    name: str
    document: Any
    chunks: list[dict[str, Any]]


def provision_root(identifier: str) -> str:
    """Identify the owning section/article without assigning new legal child labels."""
    if identifier.startswith("article_"):
        return "_".join(identifier.split("_")[:2])
    return identifier.split("(", 1)[0].split("-EXP", 1)[0].split("-ILL", 1)[0]


def collapse_ambiguous_children(document: Any, chunks: list[dict[str, Any]], name: str,
                                strict: bool = False) -> bool:
    """Retain full parent text when child parsers generate conflicting legal identities."""
    counts = Counter(chunk["chunk_id"] for chunk in chunks)
    duplicates = {identifier for identifier, count in counts.items() if count > 1}
    for identifier in duplicates:
        if identifier == provision_root(identifier):
            raise ValueError(f"Duplicate root provision {identifier}; inspect source headings/footnotes")
    affected = {provision_root(identifier) for identifier in duplicates}
    if not affected:
        return False
    if strict:
        raise ValueError(f"Ambiguous child IDs for {name}: {', '.join(sorted(duplicates))}")
    if name == "constitution":
        provisions = [article for part in document.parts for article in [*part.articles, *(article for chapter in part.chapters for article in chapter.articles)]]
    else:
        provisions = [section for chapter in document.chapters for section in chapter.sections]
    for provision in provisions:
        root = f"article_{provision.article_no}" if name == "constitution" else f"{STATUTES[name]}-{provision.section_no}"
        if root in affected:
            for field in ("clauses", "explanations", "illustrations", "provisos", "roman_clauses", "sub_clauses"):
                children = getattr(provision, field, None)
                if children is not None:
                    children.clear()
            logger.warning("%s: ambiguous child IDs; indexing full provision only in both stores", root)
    return True


def source_text(directory: Path, name: str) -> str:
    """Prefer reviewed UTF-8 text; extract text PDFs without silently applying OCR."""
    text_path, pdf_path = directory / f"{name}.txt", directory / f"{name}.pdf"
    if text_path.is_file():
        text = text_path.read_text(encoding="utf-8")
    elif pdf_path.is_file():
        import pdfplumber

        with pdfplumber.open(pdf_path) as document:
            pages = [page.extract_text() or "" for page in document.pages]
        if any(not page.strip() for page in pages):
            raise ValueError(f"{name}.pdf contains pages without text; supply reviewed OCR text as {name}.txt")
        text = "\n\n".join(pages)
    else:
        raise ValueError(f"Missing {name}.txt or {name}.pdf in the data directory")
    if not text.strip():
        raise ValueError(f"Empty source for {name}")
    return text


def prepare_corpus(directory: Path, strict_children: bool = False) -> list[ParsedStatute]:
    """Parse all inputs and reject empty/duplicate chunks before opening any service client."""
    texts = {name: source_text(directory, name) for name in STATUTES}
    prepared, seen = [], set()
    for name, prefix in STATUTES.items():
        cleaner = getattr(import_module(f"db.parsers.{name}.cleaner"), f"{prefix}TextCleaner")()
        parser = getattr(import_module(f"db.parsers.{name}.{name}_parser"), f"{prefix}Parser")()
        document = parser.parse(cleaner.clean(prepare_source(name, texts[name])))
        module = import_module(f"db.parsers.{name}.chunker")
        chunker = module.LegalChunker()
        chunks = module.chunks_to_dicts(chunker.chunk_constitution(document) if name == "constitution" else chunker.chunk_document(document))
        if collapse_ambiguous_children(document, chunks, name, strict_children):
            chunks = module.chunks_to_dicts(chunker.chunk_constitution(document) if name == "constitution" else chunker.chunk_document(document))
        if not chunks:
            raise ValueError(f"No provisions parsed for {name}; inspect PDF layout or supply reviewed text")
        for chunk in chunks:
            identifier = chunk.get("chunk_id")
            if not identifier:
                raise ValueError(f"Missing chunk ID for {name}")
            if identifier in seen:
                raise ValueError(f"Duplicate chunk ID {identifier}")
            if not chunk.get("text", "").strip():
                raise ValueError(f"Empty text for chunk {identifier}")
            seen.add(identifier)
        prepared.append(ParsedStatute(name, document, chunks))
        logger.info("Validated %s: %s chunks", name, len(chunks))
    return prepared


def ingest_corpus(corpus: list[ParsedStatute], embedder: Any, vectors: Any, graph: Any,
                  batch_size: int = 16) -> None:
    """Upsert bounded embedding batches and hierarchy nodes; never clear existing stores."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    vectors.create_collection(embedder.vector_size())
    graph.create_constraints()
    for statute in corpus:
        builder_name = f"{STATUTES[statute.name]}GraphBuilder"
        builder = getattr(import_module(f"db.graph_builders.{statute.name}_graph_builder"), builder_name)(graph)
        builder.build(statute.document)
        for start in range(0, len(statute.chunks), batch_size):
            batch = statute.chunks[start:start + batch_size]
            embeddings = embedder.embed([chunk.get("enriched_text") or chunk["text"] for chunk in batch])
            if len(embeddings) != len(batch):
                raise ValueError("Embedding count does not match input chunks")
            vectors.upsert_points([
                {"id": str(uuid5(NAMESPACE_URL, "legora:" + chunk["chunk_id"])),
                 "vector": embedding.tolist(), "payload": chunk}
                for chunk, embedding in zip(batch, embeddings)
            ])
        logger.info("Ingested %s: %s chunks", statute.name, len(statute.chunks))


def main() -> None:
    """Offer source validation without models/network and explicit ingestion with client cleanup."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/statutes"))
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--strict-children", action="store_true", help="Reject ambiguous child IDs instead of retaining the full parent only")
    args = parser.parse_args()
    setup_logging()
    vectors = graph = None
    try:
        if args.batch_size < 1:
            raise ValueError("batch_size must be positive")
        corpus = prepare_corpus(args.data_dir, strict_children=args.strict_children)
        if args.check_only:
            return
        from db.embedder import LegalEmbedder
        from db.neo4j_store import Neo4jStore
        from db.vector_store import QdrantStore
        from legora.config import EvaluationSettings

        settings = EvaluationSettings()
        graph = Neo4jStore(settings=settings)
        vectors = QdrantStore(settings=settings)
        ingest_corpus(corpus, LegalEmbedder(), vectors, graph, args.batch_size)
    except Exception as error:
        message = str(error) if type(error) is ValueError and vectors is None and graph is None else type(error).__name__
        parser.exit(1, f"Ingestion failed: {message}. No successful completion is claimed.\n")
    finally:
        if vectors is not None:
            vectors.client.close()
        if graph is not None:
            graph.close()


if __name__ == "__main__":
    main()
