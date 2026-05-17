"""Canonical-JSON hashing for tamper-evident HELIOS lineage chains.

A :class:`helios_provenance.models.HeliosFusedOutputRecord` carries a
``provenance_chain_hash`` field — a lowercase hex SHA-256 over the
canonicalised ``lineage`` plus the value/timestamp pinning. This module
implements the canonicalisation and the hash.

Why canonicalisation? Two semantically identical JSON documents can differ
byte-for-byte (key order, whitespace, number formatting). A naive
``hashlib.sha256(json.dumps(...))`` would produce different digests for the
same logical lineage, defeating tamper detection.

The hash inputs are:

* ``lineage`` — the ordered list of lineage steps as JSON-mode dicts,
* ``prediction_target`` — string label,
* ``timestamp`` — canonical RFC-3339 string (trailing ``Z`` for UTC),
* ``value`` — numeric output value,
* ``value_units`` — UDUNITS string.

Canonicalisation prefers RFC-8785 JSON Canonicalization Scheme (JCS, via the
``rfc8785`` package). If JCS is unavailable, we fall back to a documented
stable serialisation: ``json.dumps(..., sort_keys=True, separators=(",", ":"),
allow_nan=False, ensure_ascii=False)``. The fallback is deterministic for all
JSON values HELIOS lineage steps need (strings, numbers, booleans, nulls,
arrays, and objects with string keys). Both paths produce equivalent SHA-256
digests as long as input value types are JCS-safe (no NaN/Infinity, no
distinct-but-equal floats like 0.0 vs -0.0; the spec disallows these).
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any, Final

try:
    import rfc8785

    _HAVE_RFC8785: Final[bool] = True
except ImportError:  # pragma: no cover — covered indirectly by fallback test
    _HAVE_RFC8785 = False

logger = logging.getLogger(__name__)


def canonicalize(payload: Any) -> bytes:
    """Return the canonical-JSON byte serialisation of ``payload``.

    Uses RFC-8785 JCS if available, otherwise a documented stable
    serialisation. Both produce the same bytes for JCS-safe inputs (no NaN /
    Infinity / -0.0 corner cases).

    Raises:
        ValueError: if ``payload`` contains non-finite floats.
    """

    _reject_non_finite(payload)
    if _HAVE_RFC8785:
        result = rfc8785.dumps(payload)
        if isinstance(result, str):  # pragma: no cover — older rfc8785 returns str
            return result.encode("utf-8")
        return result
    # Stable fallback. allow_nan=False rejects NaN/Inf explicitly.
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        ensure_ascii=False,
    ).encode("utf-8")


def strip_nulls(payload: Any) -> Any:
    """Recursively drop ``None`` values from mappings.

    Used before hashing so optional-and-absent vs. optional-and-explicit-null
    produce the same digest. The hashing contract therefore treats
    ``{"a": null}`` and ``{}`` as equivalent — consistent with JSON Schema's
    treatment of optional fields and with how pydantic dumps unset optionals
    (it emits ``null`` whereas raw JSON typically omits the key).

    Note: list elements equal to ``None`` are preserved (their position is
    significant). Only object keys are stripped.
    """

    if isinstance(payload, Mapping):
        return {k: strip_nulls(v) for k, v in payload.items() if v is not None}
    if isinstance(payload, list):
        return [strip_nulls(v) for v in payload]
    return payload


def _reject_non_finite(payload: Any) -> None:
    """Walk ``payload`` and raise if any float is NaN or +/-Infinity.

    JCS does not allow non-finite floats. We reject them up-front for a
    consistent error regardless of which canonicalisation backend is used.
    """

    if isinstance(payload, float):
        if not _is_finite(payload):
            raise ValueError(f"non-finite float {payload!r} cannot be canonicalised")
        return
    if isinstance(payload, str | bool | int) or payload is None:
        return
    if isinstance(payload, Mapping):
        for value in payload.values():
            _reject_non_finite(value)
        return
    if isinstance(payload, Sequence):
        for value in payload:
            _reject_non_finite(value)
        return


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def lineage_hash(
    *,
    lineage: list[dict[str, Any]],
    prediction_target: str,
    timestamp: str,
    value: float | int,
    value_units: str,
) -> str:
    """Compute the tamper-evident SHA-256 of a fused output's lineage.

    Arguments are keyword-only to make calls unambiguous.

    Args:
        lineage: ordered list of lineage-step dicts. Order is significant —
            HELIOS lineage is causal, so reordering must produce a different
            hash. (Hence we do NOT sort the list; only object-key order is
            normalised within each step.)
        prediction_target: target label (e.g. ``"sep_all_clear_revocation"``).
        timestamp: canonical RFC-3339 string of the fused output's valid time.
        value: fused output value.
        value_units: UDUNITS string.

    Returns:
        Lowercase 64-character hex SHA-256 digest.
    """

    payload = {
        "schema_version": "0.1.0",
        "prediction_target": prediction_target,
        "timestamp": timestamp,
        "value": value,
        "value_units": value_units,
        "lineage": strip_nulls(lineage),
    }
    canonical = canonicalize(payload)
    digest = hashlib.sha256(canonical).hexdigest()
    logger.debug(
        "lineage_hash: target=%s len(lineage)=%d digest=%s",
        prediction_target,
        len(lineage),
        digest,
    )
    return digest


__all__ = ["canonicalize", "lineage_hash", "strip_nulls"]
