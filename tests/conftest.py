"""Shared pytest fixtures."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "schema" / "examples"


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES_DIR


@pytest.fixture
def example_paths() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*.json"))


@pytest.fixture
def example_payloads(example_paths: list[Path]) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in example_paths]


@pytest.fixture
def fused_example_payload() -> dict[str, Any]:
    return json.loads((EXAMPLES_DIR / "11-fused-sep-all-clear.json").read_text(encoding="utf-8"))


def iter_examples() -> Iterator[Path]:
    yield from sorted(EXAMPLES_DIR.glob("*.json"))
