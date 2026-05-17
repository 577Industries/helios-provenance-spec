"""helios-provenance-spec — feature-level provenance for fused space-weather model outputs.

This package is the reference implementation of the HELIOS Provenance Spec v0.1
(an open RFC). It exports:

* Pydantic v2 models that mirror the JSON Schema 1:1 (see :mod:`helios_provenance.models`).
* A canonical-JSON hashing helper for tamper-evident lineage chains
  (see :mod:`helios_provenance.hashing`).
* A thin :class:`jsonschema` wrapper plus CLI entry point for validating
  arbitrary JSON files (see :mod:`helios_provenance.validator`).
* Crosswalk emitters to SPASE 2.7.1 XML stubs and W3C PROV-JSON
  (see :mod:`helios_provenance.crosswalk`).

The JSON Schema lives at ``schema/helios-provenance-v0.1.json`` in the source
tree and is also shipped inside the wheel at
``helios_provenance/_schema/helios-provenance-v0.1.json``.

See :doc:`../rfc/RFC-0001-feature-lineage` for the design rationale.
"""

from __future__ import annotations

from helios_provenance.hashing import canonicalize, lineage_hash
from helios_provenance.models import (
    SCHEMA_VERSION,
    Agent,
    ConfidenceInterval,
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
from helios_provenance.validator import (
    SCHEMA_PATH,
    HeliosProvenanceValidator,
    load_schema,
)

__version__ = "0.1.0"

__all__ = [
    "SCHEMA_PATH",
    "SCHEMA_VERSION",
    "Agent",
    "ConfidenceInterval",
    "ConformalInterval",
    "HeliosDatasetRecord",
    "HeliosFusedOutputRecord",
    "HeliosModelOutputRecord",
    "HeliosProvenanceRecord",
    "HeliosProvenanceValidator",
    "HeliosTransformationRecord",
    "LineageStep",
    "SpatialCoverage",
    "TemporalCoverage",
    "__version__",
    "canonicalize",
    "lineage_hash",
    "load_schema",
    "parse_record",
]
