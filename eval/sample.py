"""Read stored payloads and sample distinct provisions evenly across the acts."""

import argparse
import json
import random
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from qdrant_client import QdrantClient

from eval.models import ACTS, Provision
from eval.storage import write_jsonl
from legora.config import EvaluationSettings


def provision_root(identifier: str) -> str | None:
    """Group child chunks under a section/article, excluding chapters and schedules."""
    match = re.match(r"^(BNS|BNSS|BSA|CONST)-(\d+[A-Z]*)(?=$|\(|-)", identifier)
    if match:
        return f"{match[1]}-{match[2]}"
    match = re.match(r"^article_(\d+[A-Z]*)(?=$|_)", identifier)
    return f"CONST-{match[1]}" if match else None


def stored_provisions(payloads: Iterable[dict]) -> list[Provision]:
    """Preserve exact stored IDs and text; infer act only from recognized ID formats."""
    records: dict[str, Provision] = {}
    for entry in payloads:
        payload = entry.get("payload", entry)
        identifier = payload.get("chunk_id")
        text = payload.get("text")
        root = provision_root(identifier) if isinstance(identifier, str) else None
        if not root or not isinstance(text, str) or not text.strip():
            continue
        act = "Constitution" if root.startswith("CONST-") else root.split("-", 1)[0]
        record = Provision(chunk_id=identifier, act=act, text=text)
        if identifier in records and records[identifier] != record:
            raise ValueError(f"Conflicting stored payloads for {identifier}")
        records[identifier] = record
    return sorted(records.values(), key=lambda record: record.chunk_id)


def balanced_sample(records: list[Provision], per_act: int = 30, seed: int = 42) -> list[Provision]:
    """Uniformly sample roots within each act, preferring complete parent provisions."""
    representatives: dict[tuple[str, str], Provision] = {}
    for record in sorted(records, key=lambda entry: entry.chunk_id):
        root = provision_root(record.chunk_id)
        if root is None:
            continue
        key = (record.act, root)
        if key not in representatives or record.chunk_id == root or record.chunk_id == "article_" + root.removeprefix("CONST-"):
            representatives[key] = record
    rng = random.Random(seed)
    selected = []
    for act in ACTS:
        candidates = [record for (name, _), record in sorted(representatives.items()) if name == act]
        if len(candidates) < per_act:
            raise ValueError(f"{act}: need {per_act} distinct provisions, found {len(candidates)}")
        selected.extend(rng.sample(candidates, per_act))
    return selected


def scroll_payloads(client: QdrantClient, collections: list[str]) -> Iterator[dict]:
    """Read every payload page without downloading embedding vectors."""
    for collection in collections:
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=collection, offset=offset, limit=256,
                with_payload=True, with_vectors=False,
            )
            for point in points:
                if point.payload:
                    yield point.payload
            if offset is None:
                break


def exported_payloads(path: Path) -> list[dict]:
    """Accept a JSONL payload export or a JSON array/Qdrant points object."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    return data["points"] if isinstance(data, dict) else data


def main() -> None:
    """Snapshot real chunks from Qdrant or an export, and validate the 30/act quota."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, help="Existing JSON/JSONL stored-chunk export")
    parser.add_argument("--collection", action="append", help="Repeat for separate per-act collections")
    parser.add_argument("--output", type=Path, default=Path("eval/provisions.jsonl"))
    parser.add_argument("--per-act", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.per_act < 1:
        parser.error("--per-act must be positive")
    if args.output.exists():
        parser.error("Output already exists; choose a new snapshot path to preserve provenance")
    try:
        if args.chunks:
            records = stored_provisions(exported_payloads(args.chunks))
        else:
            config = EvaluationSettings()
            if not config.qdrant_url:
                raise ValueError("QDRANT_URL is required, or supply --chunks")
            key = config.qdrant_api_key.get_secret_value() if config.qdrant_api_key else None
            client = QdrantClient(url=config.qdrant_url, api_key=key or None, timeout=config.external_timeout_seconds, check_compatibility=False)
            try:
                records = stored_provisions(scroll_payloads(client, args.collection or ["legal_rag"]))
            finally:
                client.close()
        selected = balanced_sample(records, args.per_act, args.seed)
        write_jsonl(args.output, records)
        print(f"Saved {len(records)} real source chunks; sampled {len(selected)} provisions ({args.per_act}/act).")
    except Exception as error:
        parser.exit(1, f"Sampling failed ({type(error).__name__}); check corpus availability, quotas, and input format.\n")


if __name__ == "__main__":
    main()
