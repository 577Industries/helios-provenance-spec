"""Pydantic model round-trip and JSON-Schema validation tests for all examples."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from helios_provenance.models import (
    Agent,
    ConformalInterval,
    HeliosDatasetRecord,
    HeliosFusedOutputRecord,
    HeliosModelOutputRecord,
    HeliosProvenanceRecord,
    HeliosTransformationRecord,
    LineageStep,
    SpatialCoverage,
    TemporalCoverage,
    parse_record,
)
from helios_provenance.validator import HeliosProvenanceValidator

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "schema" / "examples"
EXAMPLE_PATHS = sorted(EXAMPLES_DIR.glob("*.json"))


@pytest.fixture(scope="module")
def validator() -> HeliosProvenanceValidator:
    return HeliosProvenanceValidator()


def test_examples_directory_has_eleven_files() -> None:
    assert len(EXAMPLE_PATHS) == 11, "expected eleven worked examples"


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=lambda p: p.name)
def test_example_validates_against_schema(path: Path, validator: HeliosProvenanceValidator) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validator.errors(payload)
    assert not errors, [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
    ]


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=lambda p: p.name)
def test_example_pydantic_round_trip(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    record = parse_record(payload)
    dumped = record.model_dump(mode="json")
    # Pydantic emits None for unset optionals; the canonical examples omit
    # those keys. Strip nulls recursively, normalise timestamps, then compare.
    for k, v in payload.items():
        assert k in dumped, f"field {k} lost on round-trip"
        assert _normalise(dumped[k]) == _normalise(v), (
            f"field {k} changed on round-trip: {dumped[k]!r} != {v!r}"
        )


def _normalise(value: Any) -> Any:
    """Best-effort normalisation for round-trip comparison.

    Pydantic may emit datetime strings with a trailing ``+00:00`` instead of
    ``Z``; both are valid RFC-3339 for UTC. Also strip ``None`` values from
    mappings so optional-and-absent vs. optional-and-explicit-null compare
    equal.
    """

    if isinstance(value, str) and value.endswith("+00:00"):
        return value[:-6] + "Z"
    if isinstance(value, list):
        return [_normalise(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalise(v) for k, v in value.items() if v is not None}
    return value


def test_parse_record_rejects_missing_record_type() -> None:
    with pytest.raises(ValueError, match="record_type"):
        parse_record({"id": "x"})


def test_parse_record_rejects_unknown_record_type() -> None:
    with pytest.raises(ValueError, match="unknown record_type"):
        parse_record({"record_type": "Bogus"})


def test_parse_record_rejects_non_string_record_type() -> None:
    with pytest.raises(ValueError, match="record_type"):
        parse_record({"record_type": 42})


def test_extra_fields_are_forbidden_on_dataset() -> None:
    payload = json.loads((EXAMPLES_DIR / "01-donki-flare-dataset.json").read_text(encoding="utf-8"))
    payload["weird_unexpected_field"] = "no thanks"
    with pytest.raises(ValidationError):
        parse_record(payload)


def test_temporal_coverage_stop_after_start() -> None:
    with pytest.raises(ValidationError, match="stop must be >= start"):
        TemporalCoverage(
            start=datetime(2024, 5, 8, 0, 0, tzinfo=UTC),
            stop=datetime(2024, 5, 7, 23, 59, tzinfo=UTC),
        )


def test_temporal_coverage_accepts_open_ended() -> None:
    tc = TemporalCoverage(start=datetime(2024, 5, 8, 0, 0, tzinfo=UTC))
    assert tc.stop is None


def test_confidence_interval_upper_ge_lower() -> None:
    # ConfidenceInterval is tested by importing it indirectly through ConformalInterval;
    # both share the same validator. Exercise CI directly:
    from helios_provenance.models import ConfidenceInterval

    with pytest.raises(ValidationError, match="upper must be >= lower"):
        ConfidenceInterval(lower=0.5, upper=0.3, alpha=0.1)
    ok = ConfidenceInterval(lower=0.3, upper=0.5, alpha=0.1)
    assert ok.lower < ok.upper


def test_conformal_interval_alpha_range() -> None:
    with pytest.raises(ValidationError):
        ConformalInterval(lower=0.1, upper=0.2, alpha=1.0)
    with pytest.raises(ValidationError):
        ConformalInterval(lower=0.1, upper=0.2, alpha=-0.1)
    with pytest.raises(ValidationError, match="upper must be >= lower"):
        ConformalInterval(lower=0.5, upper=0.1, alpha=0.1)


def test_lineage_step_requires_non_empty_refs() -> None:
    with pytest.raises(ValidationError):
        LineageStep(transformation_ref="t1", input_refs=[], output_refs=["o1"])
    with pytest.raises(ValidationError):
        LineageStep(transformation_ref="t1", input_refs=["i1"], output_refs=[])


def test_to_jsonld_emits_context_and_type() -> None:
    payload = json.loads((EXAMPLES_DIR / "11-fused-sep-all-clear.json").read_text(encoding="utf-8"))
    record = parse_record(payload)
    jsonld = record.to_jsonld()
    assert "@context" in jsonld
    assert jsonld["@type"] == "helios:HeliosFusedOutputRecord"
    assert jsonld["@id"] == payload["id"]
    # core fields preserved
    assert jsonld["prediction_target"] == payload["prediction_target"]


def test_all_four_record_types_carry_unique_jsonld_type() -> None:
    types = set()
    for path in EXAMPLE_PATHS:
        rec = parse_record(json.loads(path.read_text(encoding="utf-8")))
        types.add(rec.to_jsonld()["@type"])
    expected = {
        "helios:HeliosDatasetRecord",
        "helios:HeliosModelOutputRecord",
        "helios:HeliosTransformationRecord",
        "helios:HeliosFusedOutputRecord",
    }
    assert expected.issubset(types)


def test_build_with_hash_produces_self_consistent_record() -> None:
    agent = Agent(id="a", name="test", type="software", version="0.0.1")
    lineage = [
        LineageStep(transformation_ref="t1", input_refs=["i1"], output_refs=["o1"]),
        LineageStep(
            transformation_ref="t2",
            input_refs=["o1"],
            output_refs=["final"],
            weight=0.7,
            notes="combine",
        ),
    ]
    record = HeliosFusedOutputRecord.build_with_hash(
        id="final",
        agent=agent,
        created_at=datetime(2024, 5, 8, 22, 14, tzinfo=UTC),
        prediction_target="demo_target",
        timestamp=datetime(2024, 5, 8, 22, 0, tzinfo=UTC),
        value=0.42,
        value_units="1",
        conformal_interval=ConformalInterval(lower=0.3, upper=0.55, alpha=0.1),
        lineage=lineage,
    )
    assert record.verify_hash() is True
    assert len(record.provenance_chain_hash) == 64


def test_fused_record_verify_hash_detects_tampering(
    fused_example_payload: dict[str, Any],
) -> None:
    record = parse_record(fused_example_payload)
    assert isinstance(record, HeliosFusedOutputRecord)
    assert record.verify_hash() is True
    # Mutate the lineage and observe that verify_hash detects it.
    tampered = record.model_copy(deep=True)
    tampered.lineage[0].notes = "I have been tampered with"
    assert tampered.verify_hash() is False


def test_hash_field_rejects_wrong_length(fused_example_payload: dict[str, Any]) -> None:
    payload = dict(fused_example_payload)
    payload["provenance_chain_hash"] = "deadbeef"
    with pytest.raises(ValidationError):
        parse_record(payload)


def test_spatial_coverage_optional_fields() -> None:
    sc = SpatialCoverage(frame="WGS84")
    assert sc.region is None
    assert sc.bbox is None


def test_agent_required_fields() -> None:
    with pytest.raises(ValidationError):
        Agent(id="a", name="x", type="invalid")  # type: ignore[arg-type]


def test_model_output_value_can_be_string() -> None:
    payload = json.loads((EXAMPLES_DIR / "02-donki-flare-output.json").read_text(encoding="utf-8"))
    rec = parse_record(payload)
    assert isinstance(rec, HeliosModelOutputRecord)
    assert rec.value == "X1.0"


def test_dataset_record_optional_fields_default_to_none() -> None:
    payload = {
        "id": "minimal-dataset",
        "record_type": "HeliosDatasetRecord",
        "schema_version": "0.1.0",
        "created_at": "2024-05-08T22:00:00Z",
        "agent": {
            "id": "helios:agent:t",
            "name": "t",
            "type": "software",
        },
        "source": "TEST",
        "format": "application/json",
        "temporal_coverage": {"start": "2024-05-08T00:00:00Z"},
        "source_url": "https://example.invalid/x",
        "ingestion_timestamp": "2024-05-08T22:00:00Z",
    }
    rec = parse_record(payload)
    assert isinstance(rec, HeliosDatasetRecord)
    assert rec.doi is None
    assert rec.license is None


def test_transformation_record_validates_enum() -> None:
    payload = json.loads(
        (EXAMPLES_DIR / "08-transformation-isotonic.json").read_text(encoding="utf-8")
    )
    payload["type"] = "not-a-real-type"
    with pytest.raises(ValidationError):
        parse_record(payload)


def test_base_record_carries_required_fields() -> None:
    # HeliosProvenanceRecord is abstract at the JSON Schema layer (we never
    # instantiate it directly); but exercising the type still confirms the
    # base class is well-formed.
    assert "id" in HeliosProvenanceRecord.model_fields
    assert "agent" in HeliosProvenanceRecord.model_fields


def test_transformation_record_in_isolation_validates() -> None:
    payload = json.loads((EXAMPLES_DIR / "09-transformation-bma.json").read_text(encoding="utf-8"))
    rec = parse_record(payload)
    assert isinstance(rec, HeliosTransformationRecord)
    assert rec.type == "bma"
    assert "weights" in rec.parameters
