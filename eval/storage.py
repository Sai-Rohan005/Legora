"""Atomic, validated JSONL storage that preserves human reviews on resume."""

import json
import os
import tempfile
from pathlib import Path
from typing import TypeVar

from filelock import FileLock
from pydantic import BaseModel

from eval.models import GoldItem, Provision

Record = TypeVar("Record", bound=BaseModel)


def read_jsonl(path: Path, model: type[Record]) -> list[Record]:
    """Validate records and report line numbers without echoing source contents."""
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(model.model_validate_json(line))
        except ValueError:
            raise ValueError(f"Invalid {model.__name__} at {path.name}:{number}") from None
    return records


def atomic_text(path: Path, text: str) -> None:
    """Replace a file only after a complete UTF-8 write in the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_jsonl(path: Path, records: list[BaseModel]) -> None:
    """Write actual records, with no placeholder or silently invalid rows."""
    atomic_text(path, "".join(record.model_dump_json() + "\n" for record in records))


def load_gold(path: Path) -> list[GoldItem]:
    """Load unique gold IDs; an absent file is an empty, incomplete dataset."""
    items = read_jsonl(path, GoldItem) if path.exists() else []
    if len({item.id for item in items}) != len(items):
        raise ValueError("Duplicate gold IDs")
    return items


def save_item(path: Path, item: GoldItem, replace: bool = False) -> None:
    """Merge under a lock; generation cannot overwrite an existing reviewed draft."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + ".lock", timeout=10):
        items = {entry.id: entry for entry in load_gold(path)}
        if item.id not in items or replace:
            items[item.id] = item
        write_jsonl(path, [items[key] for key in sorted(items)])


def load_catalog(path: Path) -> dict[str, Provision]:
    """Require unique stored source IDs before drafting or approving answers."""
    records = read_jsonl(path, Provision)
    catalog = {record.chunk_id: record for record in records}
    if len(catalog) != len(records):
        raise ValueError("Duplicate source IDs in provision snapshot")
    return catalog
