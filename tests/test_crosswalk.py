"""Tests for the SPASE / PROV-JSON crosswalk emitters."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from helios_provenance.crosswalk import (
    SPASE_VERSION,
    dataset_to_spase_xml,
    records_to_prov_json,
)
from helios_provenance.models import (
    HeliosDatasetRecord,
    HeliosFusedOutputRecord,
    HeliosModelOutputRecord,
    HeliosTransformationRecord,
    parse_record,
)

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "schema" / "examples"


@pytest.fixture
def dataset_record() -> HeliosDatasetRecord:
    payload = json.loads((EXAMPLES_DIR / "01-donki-flare-dataset.json").read_text(encoding="utf-8"))
    record = parse_record(payload)
    assert isinstance(record, HeliosDatasetRecord)
    return record


@pytest.fixture
def all_records() -> list[Any]:
    return [
        parse_record(json.loads(p.read_text(encoding="utf-8")))
        for p in sorted(EXAMPLES_DIR.glob("*.json"))
    ]


def test_spase_xml_is_well_formed(dataset_record: HeliosDatasetRecord) -> None:
    xml = dataset_to_spase_xml(dataset_record)
    root = ET.fromstring(xml)
    assert root.tag.endswith("Spase")


def test_spase_xml_pretty_is_well_formed(dataset_record: HeliosDatasetRecord) -> None:
    xml_pretty = dataset_to_spase_xml(dataset_record, pretty=True)
    # Strip prolog before parsing minidom output
    root = ET.fromstring(
        xml_pretty.split("?>", 1)[-1] if xml_pretty.startswith("<?") else xml_pretty
    )
    assert root.tag.endswith("Spase")


def test_spase_xml_contains_version_and_source(dataset_record: HeliosDatasetRecord) -> None:
    xml = dataset_to_spase_xml(dataset_record)
    assert SPASE_VERSION in xml
    assert dataset_record.source in xml
    # Round-trip parse so any XML escaping of '&', '<', etc. doesn't matter.
    root = ET.fromstring(xml)
    found_urls = [el.text for el in root.iter() if el.tag.endswith("URL")]
    assert dataset_record.source_url in found_urls


def test_spase_xml_includes_doi_when_set() -> None:
    payload = json.loads((EXAMPLES_DIR / "01-donki-flare-dataset.json").read_text(encoding="utf-8"))
    payload["doi"] = "10.5067/example/123"
    record = parse_record(payload)
    assert isinstance(record, HeliosDatasetRecord)
    xml = dataset_to_spase_xml(record)
    assert "10.5067/example/123" in xml


def test_spase_xml_synthesises_resource_id_when_missing() -> None:
    payload = json.loads((EXAMPLES_DIR / "01-donki-flare-dataset.json").read_text(encoding="utf-8"))
    payload.pop("spase_resource_id", None)
    record = parse_record(payload)
    assert isinstance(record, HeliosDatasetRecord)
    xml = dataset_to_spase_xml(record)
    assert "spase://HELIOS/NumericalData/" in xml


def test_spase_xml_includes_cadence_when_present() -> None:
    payload = json.loads((EXAMPLES_DIR / "01-donki-flare-dataset.json").read_text(encoding="utf-8"))
    payload["temporal_coverage"] = {
        "start": "2024-05-08T00:00:00Z",
        "stop": "2024-05-08T23:59:59Z",
        "cadence": "PT5M",
    }
    record = parse_record(payload)
    assert isinstance(record, HeliosDatasetRecord)
    xml = dataset_to_spase_xml(record)
    assert "PT5M" in xml


def test_prov_json_emits_entities_for_datasets_and_outputs(all_records: list[Any]) -> None:
    prov = records_to_prov_json(all_records)
    entity_ids = set(prov["entity"].keys())
    # Every dataset/output/fused record should appear under "entity".
    for record in all_records:
        if isinstance(
            record, HeliosDatasetRecord | HeliosModelOutputRecord | HeliosFusedOutputRecord
        ):
            assert record.id in entity_ids


def test_prov_json_emits_activities_for_transformations(all_records: list[Any]) -> None:
    prov = records_to_prov_json(all_records)
    activity_ids = set(prov["activity"].keys())
    for record in all_records:
        if isinstance(record, HeliosTransformationRecord):
            assert record.id in activity_ids


def test_prov_json_emits_used_for_transformation_inputs(all_records: list[Any]) -> None:
    prov = records_to_prov_json(all_records)
    assert len(prov["used"]) > 0
    for edge in prov["used"].values():
        assert edge["prov:activity"] in prov["activity"]


def test_prov_json_emits_was_generated_by(all_records: list[Any]) -> None:
    prov = records_to_prov_json(all_records)
    assert len(prov["wasGeneratedBy"]) > 0


def test_prov_json_emits_was_derived_from_for_fused_records(
    all_records: list[Any],
) -> None:
    prov = records_to_prov_json(all_records)
    fused_records = [r for r in all_records if isinstance(r, HeliosFusedOutputRecord)]
    if fused_records:
        assert len(prov["wasDerivedFrom"]) > 0
        for edge in prov["wasDerivedFrom"].values():
            assert "helios:transformationRef" in edge


def test_prov_json_attributes_records_to_agents(all_records: list[Any]) -> None:
    prov = records_to_prov_json(all_records)
    assert len(prov["wasAttributedTo"]) >= len(all_records)
    for edge in prov["wasAttributedTo"].values():
        assert edge["prov:agent"] in prov["agent"]


def test_prov_json_agent_metadata(all_records: list[Any]) -> None:
    prov = records_to_prov_json(all_records)
    for agent_id, fields in prov["agent"].items():
        assert agent_id.startswith("helios:agent:")
        assert fields["prov:type"] == "helios:Agent"
        assert fields["helios:agentType"] in {"software", "service", "person", "organization"}


def test_prov_json_includes_helios_prefix(all_records: list[Any]) -> None:
    prov = records_to_prov_json(all_records)
    assert "helios" in prov["prefix"]
    assert "prov" in prov["prefix"]
