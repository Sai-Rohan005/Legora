"""Offline test defaults and reusable structural fixtures."""

import os
import socket
from pathlib import Path

import pytest

# Apply before collection imports can trigger Hugging Face metadata requests.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail immediately if any test attempts an external socket connection."""
    def deny(*args: object, **kwargs: object) -> None:
        """Reject transport use instead of replacing application logic."""
        raise AssertionError("Network connections are disabled in this test suite")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


@pytest.fixture
def statute_text() -> dict[str, str]:
    """Load the four small checked-in structural statute fixtures."""
    directory = Path(__file__).parent / "fixtures"
    return {name: (directory / f"{name}.txt").read_text(encoding="utf-8")
            for name in ("bns", "bnss", "bsa", "constitution")}
