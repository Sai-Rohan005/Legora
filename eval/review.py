"""Review gold questions, edit supporting IDs, and explicitly approve labels."""

import argparse
from pathlib import Path

from eval.models import GoldItem, Provision
from eval.storage import load_catalog, load_gold, save_item


def edit_item(item: GoldItem, **changes: object) -> GoldItem:
    """Validate edits and invalidate earlier approval whenever content changes."""
    return GoldItem.model_validate({**item.model_dump(), **changes, "reviewed": False})


def approve_item(item: GoldItem, catalog: dict[str, Provision]) -> GoldItem:
    """Require all supporting IDs to exist in the captured corpus before approval."""
    identifiers = item.expected_chunk_ids + item.acceptable_alternates
    if set(identifiers) - catalog.keys():
        raise ValueError("Supporting IDs are missing from the provision snapshot")
    if item.answerable and item.act != "MULTI":
        if any(catalog[value].act != item.act for value in identifiers):
            raise ValueError("Supporting IDs do not belong to the item's act")
    return GoldItem.model_validate({**item.model_dump(), "reviewed": True})


def show_item(item: GoldItem) -> None:
    """Show the reviewable record without changing its approval status."""
    print(f"\n{item.id} | {item.act} | {item.intent} | reviewed={item.reviewed}")
    print(item.question)
    print("Expected:", ", ".join(item.expected_chunk_ids) or "(none)")
    print("Alternates:", ", ".join(item.acceptable_alternates) or "(none)")
    print("Notes:", item.notes)


def interactive_review(path: Path, catalog: dict[str, Provision], answerable_only: bool = False) -> None:
    """Review pending records one at a time; every edit is saved atomically."""
    skipped: set[str] = set()
    while True:
        pending = [item for item in load_gold(path) if not item.reviewed and item.id not in skipped
                   and (not answerable_only or item.answerable)]
        if not pending:
            print("No more pending items in this session.")
            return
        item = pending[0]
        show_item(item)
        command = input("[a]pprove [e]xpected [t]alternates [q]uestion [n]otes [i]ntent [s]ources [k]skip [x]exit: ").strip().lower()
        if command == "x":
            return
        if command == "k":
            skipped.add(item.id)
            continue
        if command == "s":
            for identifier in item.expected_chunk_ids + item.acceptable_alternates:
                source = catalog.get(identifier)
                print(f"\n{identifier}\n{source.text if source else '(source snapshot unavailable)'}")
            continue
        try:
            if command == "a":
                item = approve_item(item, catalog)
            elif command in {"e", "t"}:
                field = "expected_chunk_ids" if command == "e" else "acceptable_alternates"
                values = [value.strip() for value in input("Comma-separated exact stored IDs: ").split(",") if value.strip()]
                item = edit_item(item, **{field: values})
            elif command in {"q", "n", "i"}:
                field = {"q": "question", "n": "notes", "i": "intent"}[command]
                item = edit_item(item, **{field: input(f"New {field}: ").strip()})
            else:
                continue
            save_item(path, item, replace=True)
        except ValueError:
            print("Invalid edit or missing supporting IDs; the item was not approved.")


def main() -> None:
    """Offer interactive review plus explicit noninteractive edits and approval."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("eval/gold.jsonl"))
    parser.add_argument("--catalog", type=Path, default=Path("eval/provisions.jsonl"))
    parser.add_argument("--list", action="store_true", help="List IDs and approval state")
    parser.add_argument("--answerable-only", action="store_true", help="Review only legal questions; leave out-of-scope records unchanged")
    parser.add_argument("--id", help="Inspect/edit one item instead of entering interactive mode")
    parser.add_argument("--expected", nargs="+", help="Replace expected supporting IDs")
    parser.add_argument("--alternates", nargs="*", help="Replace acceptable alternate IDs")
    parser.add_argument("--question")
    parser.add_argument("--notes")
    parser.add_argument("--intent")
    parser.add_argument("--approve", action="store_true", help="Explicitly mark the selected item reviewed=true")
    args = parser.parse_args()
    try:
        items = load_gold(args.gold)
        if args.answerable_only:
            items = [item for item in items if item.answerable]
        catalog = load_catalog(args.catalog) if args.catalog.exists() else {}
        if args.list:
            for item in items:
                print(f"{item.id}\t{item.act}\treviewed={item.reviewed}")
            print(f"{sum(item.reviewed for item in items)}/{len(items)} reviewed")
            return
        if args.id:
            selected = next((entry for entry in items if entry.id == args.id), None)
            if selected is None:
                raise ValueError("Unknown item ID")
            item = selected
            changes = {field: value for field, value in {
                "expected_chunk_ids": args.expected, "acceptable_alternates": args.alternates,
                "question": args.question, "notes": args.notes, "intent": args.intent,
            }.items() if value is not None}
            if changes:
                item = edit_item(item, **changes)
            if args.approve:
                item = approve_item(item, catalog)
            if changes or args.approve:
                save_item(args.gold, item, replace=True)
            show_item(item)
        else:
            if args.approve or args.expected or args.alternates is not None or args.question or args.notes or args.intent:
                parser.error("Noninteractive edits require --id")
            interactive_review(args.gold, catalog, answerable_only=args.answerable_only)
    except (ValueError, OSError):
        parser.exit(1, "Review failed: check the file, item ID, label schema, and source snapshot.\n")


if __name__ == "__main__":
    main()
