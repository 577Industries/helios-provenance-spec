"""Tests for the JSON-Schema validator wrapper and CLI."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from helios_provenance.validator import (
    HeliosProvenanceValidator,
    load_schema,
)
from helios_provenance.validator import (
    main as validator_main,
)


@pytest.fixture(scope="module")
def validator() -> HeliosProvenanceValidator:
    return HeliosProvenanceValidator()


def test_load_schema_returns_draft_2020_12() -> None:
    schema = load_schema()
    assert schema["$schema"].endswith("draft/2020-12/schema")
    assert schema["title"] == "HELIOS Provenance Spec v0.1"


def test_load_schema_is_cached() -> None:
    assert load_schema() is load_schema()


def test_validator_rejects_missing_required_field(
    fused_example_payload: dict[str, Any], validator: HeliosProvenanceValidator
) -> None:
    bad = dict(fused_example_payload)
    bad.pop("provenance_chain_hash")
    errors = validator.errors(bad)
    assert errors, "missing provenance_chain_hash must reject"


def test_validator_rejects_wrong_record_type_field(
    fused_example_payload: dict[str, Any], validator: HeliosProvenanceValidator
) -> None:
    bad = dict(fused_example_payload)
    bad["record_type"] = "HeliosUnknownRecord"
    errors = validator.errors(bad)
    assert errors


def test_validator_rejects_non_iso_timestamp(
    fused_example_payload: dict[str, Any], validator: HeliosProvenanceValidator
) -> None:
    bad = dict(fused_example_payload)
    bad["timestamp"] = "not-a-timestamp"
    errors = validator.errors(bad)
    assert errors


def test_validator_rejects_wrong_hash_pattern(
    fused_example_payload: dict[str, Any], validator: HeliosProvenanceValidator
) -> None:
    bad = dict(fused_example_payload)
    bad["provenance_chain_hash"] = "ZZZZ"
    errors = validator.errors(bad)
    assert errors


def test_validator_rejects_extra_property(
    fused_example_payload: dict[str, Any], validator: HeliosProvenanceValidator
) -> None:
    bad = dict(fused_example_payload)
    bad["completely_unknown_field"] = 1
    errors = validator.errors(bad)
    assert errors


def test_validator_rejects_alpha_out_of_range(
    fused_example_payload: dict[str, Any], validator: HeliosProvenanceValidator
) -> None:
    bad = dict(fused_example_payload)
    bad["conformal_interval"] = dict(bad["conformal_interval"])
    bad["conformal_interval"]["alpha"] = 2.5
    errors = validator.errors(bad)
    assert errors


def test_validator_accepts_all_examples(
    example_payloads: list[dict[str, Any]], validator: HeliosProvenanceValidator
) -> None:
    for payload in example_payloads:
        assert validator.is_valid(payload), payload.get("id")


def test_validator_validate_method_raises_on_invalid(
    fused_example_payload: dict[str, Any], validator: HeliosProvenanceValidator
) -> None:
    bad = dict(fused_example_payload)
    bad["provenance_chain_hash"] = "tooshort"
    with pytest.raises(Exception):  # jsonschema.ValidationError
        validator.validate(bad)


def test_validator_validate_file(examples_dir: Path, validator: HeliosProvenanceValidator) -> None:
    errs = validator.validate_file(examples_dir / "11-fused-sep-all-clear.json")
    assert errs == []


def test_validator_schema_property(validator: HeliosProvenanceValidator) -> None:
    schema = validator.schema
    assert isinstance(schema, dict)
    assert "$defs" in schema


def test_cli_returns_0_for_valid_files(
    examples_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    paths = [str(examples_dir / "11-fused-sep-all-clear.json")]
    with caplog.at_level(logging.INFO):
        rc = validator_main(paths)
    assert rc == 0
    assert any("OK" in m for m in caplog.messages)


def test_cli_returns_1_for_invalid_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, fused_example_payload: dict[str, Any]
) -> None:
    invalid_payload = dict(fused_example_payload)
    invalid_payload["provenance_chain_hash"] = "deadbeef"
    target = tmp_path / "bad.json"
    target.write_text(json.dumps(invalid_payload), encoding="utf-8")
    with caplog.at_level(logging.INFO):
        rc = validator_main([str(target)])
    assert rc == 1
    assert any("INVALID" in m for m in caplog.messages)


def test_cli_handles_unreadable_file(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    bad = tmp_path / "not-json.json"
    bad.write_text("not valid json {", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        rc = validator_main([str(bad)])
    assert rc == 1
    assert any("could not read JSON" in m for m in caplog.messages)


def test_cli_handles_missing_file(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    missing = tmp_path / "no-such-file.json"
    with caplog.at_level(logging.ERROR):
        rc = validator_main([str(missing)])
    assert rc == 1


def test_cli_verbose_flag(examples_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        rc = validator_main(["-v", str(examples_dir / "01-donki-flare-dataset.json")])
    assert rc == 0


def test_cli_reads_stdin(
    monkeypatch: pytest.MonkeyPatch, fused_example_payload: dict[str, Any]
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(fused_example_payload)))
    rc = validator_main(["-"])
    assert rc == 0


def test_validator_custom_schema() -> None:
    custom = {
        "type": "object",
        "required": ["x"],
        "$schema": "https://json-schema.org/draft/2020-12/schema",
    }
    v = HeliosProvenanceValidator(schema=custom)
    assert v.is_valid({"x": 1}) is True
    assert v.is_valid({}) is False
