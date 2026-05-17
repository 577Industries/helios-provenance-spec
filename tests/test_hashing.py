"""Tests for the canonical-JSON hashing module.

The hashing contract has two important invariants:

1. **Object-key order is irrelevant** — shuffling keys in a lineage step
   MUST produce the same hash.
2. **List-element order is significant** — reordering lineage steps MUST
   produce a different hash (causal order matters).
3. **Tamper detection** — any payload mutation MUST flip the hash.
4. **Null-stripping** — optional-and-absent vs optional-and-explicit-null
   produce the same hash.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from helios_provenance.hashing import canonicalize, lineage_hash, strip_nulls

_LINEAGE: list[dict[str, Any]] = [
    {
        "transformation_ref": "t1",
        "input_refs": ["i1", "i2"],
        "output_refs": ["o1"],
    },
    {
        "transformation_ref": "t2",
        "input_refs": ["o1"],
        "output_refs": ["final"],
        "weight": 0.7,
    },
]

_COMMON = {
    "prediction_target": "demo",
    "timestamp": "2024-05-08T22:00:00Z",
    "value": 0.42,
    "value_units": "1",
}


def test_hash_is_deterministic() -> None:
    h1 = lineage_hash(lineage=_LINEAGE, **_COMMON)
    h2 = lineage_hash(lineage=_LINEAGE, **_COMMON)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_is_invariant_to_object_key_order() -> None:
    h1 = lineage_hash(lineage=_LINEAGE, **_COMMON)
    shuffled = [
        {
            "output_refs": step["output_refs"],
            "transformation_ref": step["transformation_ref"],
            "input_refs": step["input_refs"],
            **({"weight": step["weight"]} if "weight" in step else {}),
        }
        for step in _LINEAGE
    ]
    h2 = lineage_hash(lineage=shuffled, **_COMMON)
    assert h1 == h2


def test_hash_detects_lineage_step_reordering() -> None:
    h_original = lineage_hash(lineage=_LINEAGE, **_COMMON)
    h_reversed = lineage_hash(lineage=list(reversed(_LINEAGE)), **_COMMON)
    assert h_original != h_reversed, "lineage list order must be load-bearing (causal direction)"


def test_hash_detects_value_mutation() -> None:
    h1 = lineage_hash(lineage=_LINEAGE, **_COMMON)
    bumped = dict(_COMMON)
    bumped["value"] = 0.43
    h2 = lineage_hash(lineage=_LINEAGE, **bumped)
    assert h1 != h2


def test_hash_detects_timestamp_mutation() -> None:
    h1 = lineage_hash(lineage=_LINEAGE, **_COMMON)
    bumped = dict(_COMMON)
    bumped["timestamp"] = "2024-05-08T22:00:01Z"
    h2 = lineage_hash(lineage=_LINEAGE, **bumped)
    assert h1 != h2


def test_hash_detects_input_ref_swap() -> None:
    h_original = lineage_hash(lineage=_LINEAGE, **_COMMON)
    mutated = [dict(step) for step in _LINEAGE]
    mutated[0]["input_refs"] = ["i1", "i3"]  # swap i2 -> i3
    h_mutated = lineage_hash(lineage=mutated, **_COMMON)
    assert h_original != h_mutated


def test_explicit_null_equals_absent() -> None:
    # A lineage step with `weight: None` (e.g. emitted by pydantic) must hash
    # identically to one where the `weight` key is absent.
    lineage_with_null = [dict(_LINEAGE[0], weight=None), dict(_LINEAGE[1])]
    h_null = lineage_hash(lineage=lineage_with_null, **_COMMON)
    h_absent = lineage_hash(lineage=_LINEAGE, **_COMMON)
    assert h_null == h_absent


def test_strip_nulls_recursive() -> None:
    payload = {
        "a": None,
        "b": 1,
        "c": {"d": None, "e": 2, "f": {"g": None}},
        "h": [{"i": None, "j": 3}, None, 4],
    }
    stripped = strip_nulls(payload)
    assert stripped == {
        "b": 1,
        "c": {"e": 2, "f": {}},
        "h": [{"j": 3}, None, 4],
    }


def test_canonicalize_rejects_nan() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize({"x": float("nan")})


def test_canonicalize_rejects_inf() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize({"x": float("inf")})
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize({"x": float("-inf")})


def test_canonicalize_rejects_nan_nested() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize([1, 2, {"nested": float("nan")}])


def test_canonicalize_accepts_basic_jcs_inputs() -> None:
    out = canonicalize({"b": 2, "a": 1, "c": [True, False, None, "x"]})
    text = out.decode("utf-8")
    # Whatever the backend, sort_keys-equivalent output:
    assert text.startswith('{"a":1')
    assert '[true,false,null,"x"]' in text


def test_canonicalize_returns_bytes() -> None:
    out = canonicalize({"x": 1})
    assert isinstance(out, bytes)


def test_strip_nulls_passes_through_scalars() -> None:
    assert strip_nulls(42) == 42
    assert strip_nulls("x") == "x"
    assert strip_nulls(True) is True
    assert strip_nulls(None) is None


def test_lineage_hash_matches_published_example(fused_example_payload: dict[str, Any]) -> None:
    # The headline assertion: the hash bundled in the canonical example is
    # exactly what this implementation produces.
    expected_hash = fused_example_payload["provenance_chain_hash"]
    lineage = fused_example_payload["lineage"]
    common = {
        "prediction_target": fused_example_payload["prediction_target"],
        "timestamp": fused_example_payload["timestamp"],
        "value": fused_example_payload["value"],
        "value_units": fused_example_payload["value_units"],
    }
    assert lineage_hash(lineage=lineage, **common) == expected_hash


def test_hash_changes_when_step_order_swapped(
    fused_example_payload: dict[str, Any],
) -> None:
    base_lineage = fused_example_payload["lineage"]
    common = {
        "prediction_target": fused_example_payload["prediction_target"],
        "timestamp": fused_example_payload["timestamp"],
        "value": fused_example_payload["value"],
        "value_units": fused_example_payload["value_units"],
    }
    original = lineage_hash(lineage=base_lineage, **common)
    reordered = lineage_hash(lineage=[base_lineage[2], base_lineage[1], base_lineage[0]], **common)
    assert original != reordered


def test_strip_nulls_idempotent() -> None:
    payload = {"a": {"b": None, "c": 1}}
    once = strip_nulls(payload)
    twice = strip_nulls(once)
    assert once == twice


def test_canonicalize_uses_jcs_when_available() -> None:
    # Smoke-test that some sort of canonical-bytes is returned;
    # also serves as a placeholder for fallback-vs-JCS parity verification.
    a = canonicalize({"a": 1, "b": 2})
    b = canonicalize({"b": 2, "a": 1})
    assert a == b
    parsed = json.loads(a.decode("utf-8"))
    assert parsed == {"a": 1, "b": 2}
