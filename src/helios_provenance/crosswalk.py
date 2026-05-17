"""Crosswalks from HELIOS provenance records to neighbouring standards.

This module emits stubs of:

* **SPASE 2.7.1** (heliophysics dataset metadata) — minimal XML resources.
  Full SPASE conformance is not the goal here; the stubs are starting points
  that a heliophysics adopter can hand-complete and pass through the SPASE
  validator.
* **W3C PROV-JSON** (W3C TR-2013-prov-json) — feature-level lineage relations
  (``wasGeneratedBy``, ``used``, ``wasDerivedFrom``).

See ``schema/crosswalks/`` in the source tree for the field-by-field tables.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from helios_provenance.models import (
    HeliosDatasetRecord,
    HeliosFusedOutputRecord,
    HeliosModelOutputRecord,
    HeliosProvenanceRecord,
    HeliosTransformationRecord,
)

logger = logging.getLogger(__name__)

SPASE_XMLNS = "http://www.spase-group.org/data/schema"
SPASE_VERSION = "2.7.1"


def dataset_to_spase_xml(record: HeliosDatasetRecord, *, pretty: bool = False) -> str:
    """Emit a minimal SPASE 2.7.1 ``NumericalData`` XML stub.

    The stub captures the SPASE elements we can map losslessly from a HELIOS
    dataset record. Domain-specific elements (``InstrumentID``,
    ``MeasurementType``, etc.) are left for a heliophysics SME to fill in.

    Args:
        record: a :class:`HeliosDatasetRecord`.
        pretty: indent the output for readability. Bytes-identical XML
            without this flag.
    """

    spase = Element("Spase", {"xmlns": SPASE_XMLNS})
    version = SubElement(spase, "Version")
    version.text = SPASE_VERSION

    numerical = SubElement(spase, "NumericalData")
    resource_id = SubElement(numerical, "ResourceID")
    resource_id.text = record.spase_resource_id or _synth_spase_id(record)

    header = SubElement(numerical, "ResourceHeader")
    SubElement(header, "ResourceName").text = f"{record.source} — {record.format}"
    description = SubElement(header, "Description")
    description.text = (
        f"HELIOS-ingested {record.source} dataset (format={record.format})."
        + (f" Mission: {record.mission}." if record.mission else "")
        + (f" Instrument: {record.instrument}." if record.instrument else "")
    )
    SubElement(header, "ReleaseDate").text = record.ingestion_timestamp.isoformat()
    if record.doi:
        SubElement(header, "DOI").text = record.doi

    access_info = SubElement(numerical, "AccessInformation")
    repo = SubElement(access_info, "RepositoryID")
    repo.text = record.source
    access_url = SubElement(access_info, "AccessURL")
    SubElement(access_url, "URL").text = record.source_url
    SubElement(access_info, "Format").text = record.format
    if record.license:
        SubElement(access_info, "RightsList").text = record.license

    temporal = SubElement(numerical, "TemporalDescription")
    SubElement(temporal, "TimeSpan").text = _format_timespan(record)
    if record.temporal_coverage.cadence:
        SubElement(temporal, "Cadence").text = record.temporal_coverage.cadence

    if pretty:
        from xml.dom.minidom import parseString

        raw = tostring(spase, encoding="utf-8")
        return parseString(raw).toprettyxml(indent="  ")
    return tostring(spase, encoding="unicode")


def _format_timespan(record: HeliosDatasetRecord) -> str:
    start = record.temporal_coverage.start.isoformat()
    stop = (
        record.temporal_coverage.stop.isoformat()
        if record.temporal_coverage.stop is not None
        else "open"
    )
    return f"{start}/{stop}"


def _synth_spase_id(record: HeliosDatasetRecord) -> str:
    """Synthesise a SPASE-style ResourceID when none is provided."""

    safe_source = record.source.replace("/", "-")
    return f"spase://HELIOS/NumericalData/{safe_source}/{record.id}"


def records_to_prov_json(records: Iterable[HeliosProvenanceRecord]) -> dict[str, Any]:
    """Emit a W3C PROV-JSON document covering the supplied records.

    Mapping:

    * :class:`HeliosDatasetRecord` and :class:`HeliosModelOutputRecord` →
      PROV ``entity``,
    * :class:`HeliosTransformationRecord` → PROV ``activity`` plus a ``used``
      edge for each input and a ``wasGeneratedBy`` edge for each output,
    * :class:`HeliosFusedOutputRecord` → PROV ``entity`` plus a chain of
      ``wasDerivedFrom`` edges, one per lineage step.
    * :class:`helios_provenance.models.Agent` → PROV ``agent`` plus
      ``wasAttributedTo`` edges from every emitting record.
    """

    prov: dict[str, Any] = {
        "prefix": {
            "helios": "https://577-industries.github.io/helios-provenance-spec/ns/",
            "prov": "http://www.w3.org/ns/prov#",
        },
        "entity": {},
        "activity": {},
        "agent": {},
        "used": {},
        "wasGeneratedBy": {},
        "wasDerivedFrom": {},
        "wasAttributedTo": {},
    }

    used_counter = 0
    gen_counter = 0
    derived_counter = 0

    seen_agents: set[str] = set()
    for attr_counter, record in enumerate(records, start=1):
        agent_id = record.agent.id
        if agent_id not in seen_agents:
            prov["agent"][agent_id] = {
                "prov:type": "helios:Agent",
                "helios:name": record.agent.name,
                "helios:agentType": record.agent.type,
            }
            if record.agent.version:
                prov["agent"][agent_id]["helios:version"] = record.agent.version
            seen_agents.add(agent_id)

        prov["wasAttributedTo"][f"_:attr{attr_counter}"] = {
            "prov:entity": record.id,
            "prov:agent": agent_id,
        }

        if isinstance(record, HeliosDatasetRecord | HeliosModelOutputRecord):
            prov["entity"][record.id] = {
                "prov:type": f"helios:{record.record_type}",
                "helios:schemaVersion": record.schema_version,
            }
        elif isinstance(record, HeliosTransformationRecord):
            prov["activity"][record.id] = {
                "prov:type": f"helios:{record.record_type}",
                "helios:transformationType": record.type,
                "helios:codeRef": record.code_ref,
            }
            for input_ref in record.input_refs:
                used_counter += 1
                prov["used"][f"_:u{used_counter}"] = {
                    "prov:activity": record.id,
                    "prov:entity": input_ref,
                }
            for output_ref in record.output_refs:
                gen_counter += 1
                prov["wasGeneratedBy"][f"_:g{gen_counter}"] = {
                    "prov:entity": output_ref,
                    "prov:activity": record.id,
                }
        elif isinstance(record, HeliosFusedOutputRecord):
            prov["entity"][record.id] = {
                "prov:type": "helios:HeliosFusedOutputRecord",
                "helios:provenanceChainHash": record.provenance_chain_hash,
            }
            for step in record.lineage:
                for input_ref in step.input_refs:
                    for output_ref in step.output_refs:
                        derived_counter += 1
                        prov["wasDerivedFrom"][f"_:d{derived_counter}"] = {
                            "prov:generatedEntity": output_ref,
                            "prov:usedEntity": input_ref,
                            "helios:transformationRef": step.transformation_ref,
                        }
        else:  # pragma: no cover — record_type literal narrows above
            logger.warning("skipping unknown record type %s", type(record).__name__)

    return prov


__all__ = ["SPASE_VERSION", "dataset_to_spase_xml", "records_to_prov_json"]
