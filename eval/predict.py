"""Collect API retrieval/confidence predictions for reviewed questions only."""

import argparse
from pathlib import Path

import requests

from api.models import QueryResponse
from eval.metrics import reviewed_gold
from eval.models import Prediction
from eval.storage import write_jsonl
from legora.config import get_client_settings


def canonical_refusal(answer: str) -> bool:
    """Recognize only the pipeline's documented abstention sentence."""
    normalized = " ".join(answer.lower().split()).strip('"').rstrip(".")
    return normalized == "the provided legal corpus does not contain sufficient information to answer this question"


def main() -> None:
    """Call the running API with a timeout; do not score drafts or fabricate errors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=Path("eval/gold.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("eval/predictions.jsonl"))
    args = parser.parse_args()
    try:
        gold = reviewed_gold(args.gold)
        settings = get_client_settings()
        predictions = []
        for item in gold:
            response = requests.post(
                settings.api_base_url.rstrip("/") + "/query", json={"query": item.question},
                timeout=settings.api_timeout_seconds,
            )
            response.raise_for_status()
            result = QueryResponse.model_validate(response.json())
            predictions.append(Prediction(
                id=item.id, retrieved_chunk_ids=[citation.id for citation in result.citations],
                score=result.evaluation.score,
                # Other refusal wording needs an explicit human label.
                refused=canonical_refusal(result.answer),
            ))
        write_jsonl(args.output, predictions)
        print(f"Saved {len(predictions)} predictions for reviewed items only.")
    except Exception as error:
        parser.exit(1, f"Prediction collection failed ({type(error).__name__}); no scores were fabricated.\n")


if __name__ == "__main__":
    main()
