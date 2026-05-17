"""Pydantic v2 models mirroring the HELIOS provenance JSON Schema v0.1.

Every record type carries a ``record_type`` discriminator so untyped JSON can be
parsed via :func:`parse_record`. All models forbid extra fields (``extra="forbid"``)
because provenance records must be unambiguous: silent acceptance of unknown
keys would mask schema drift between producers and consumers.

The :meth:`to_jsonld` method on each model emits an RO-Crate 1.2 JSON-LD
fragment (the ``@context`` is a sibling of the HELIOS namespace, not a globally
hosted ontology — adopters are encouraged to mint a stable IRI once the spec
stabilises at v1.0).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)

logger = logging.getLogger(__name__)

SCHEMA_VERSION: Literal["0.1.0"] = "0.1.0"
"""Pinned semantic version of the HELIOS provenance schema this module implements."""

JSONLD_CONTEXT_URI: str = (
    "https://577-industries.github.io/helios-provenance-spec/context/v0.1.jsonld"
)
"""IRI for the HELIOS RO-Crate-compatible JSON-LD context.

The IRI is a placeholder until the spec stabilises at v1.0 and a permanent
context document is published. Adopters MAY substitute their own context
during the RFC period; downstream tools should accept either.
"""


def _datetime_to_iso(value: datetime) -> str:
    """Serialise a timezone-aware datetime to RFC-3339 with trailing 'Z' for UTC."""

    iso = value.isoformat()
    if iso.endswith("+00:00"):
        return iso[:-6] + "Z"
    return iso


class _HeliosBaseModel(BaseModel):
    """Common pydantic config for every HELIOS record type."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class Agent(_HeliosBaseModel):
    """The who/what (software, service, person, organisation) that created a record.

    Maps to W3C PROV ``Agent``.
    """

    id: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1)
    type: Literal["software", "service", "person", "organization"]
    version: str | None = None


class TemporalCoverage(_HeliosBaseModel):
    """SPASE-style temporal coverage.

    ``start`` is required; ``stop`` MAY be omitted to represent open-ended coverage.
    ``cadence`` is an ISO-8601 duration string (e.g. ``"PT2H"``).
    """

    start: AwareDatetime
    stop: AwareDatetime | None = None
    cadence: str | None = None

    @field_validator("stop")
    @classmethod
    def _stop_after_start(
        cls, v: AwareDatetime | None, info: ValidationInfo
    ) -> AwareDatetime | None:
        if v is not None and "start" in info.data and v < info.data["start"]:
            raise ValueError("stop must be >= start")
        return v


class _Point(_HeliosBaseModel):
    lon: float | None = None
    lat: float | None = None
    alt: float | None = None


class SpatialCoverage(_HeliosBaseModel):
    """SPASE-style spatial coverage. Free-form to accommodate heliophysics location semantics."""

    frame: str | None = None
    region: str | None = None
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=6)
    point: _Point | None = None


class ConfidenceInterval(_HeliosBaseModel):
    """Source-provided uncertainty around an upstream model output value."""

    lower: float
    upper: float
    alpha: float = Field(gt=0.0, lt=1.0)
    method: str | None = None

    @field_validator("upper")
    @classmethod
    def _upper_ge_lower(cls, v: float, info: ValidationInfo) -> float:
        if "lower" in info.data and v < info.data["lower"]:
            raise ValueError("upper must be >= lower")
        return v


class ConformalInterval(_HeliosBaseModel):
    """Conformal prediction interval attached to a fused output."""

    lower: float
    upper: float
    alpha: float = Field(gt=0.0, lt=1.0)
    method: Literal[
        "conformal-split",
        "conformal-mondrian",
        "conformal-cv-plus",
        "other",
    ] = "conformal-split"
    calibration_set_size: int | None = Field(default=None, ge=1)

    @field_validator("upper")
    @classmethod
    def _upper_ge_lower(cls, v: float, info: ValidationInfo) -> float:
        if "lower" in info.data and v < info.data["lower"]:
            raise ValueError("upper must be >= lower")
        return v


class LineageStep(_HeliosBaseModel):
    """One step of feature-level lineage on a :class:`HeliosFusedOutputRecord`.

    Each step references the :class:`HeliosTransformationRecord` that
    instantiated it plus the input/output record IDs incident to it.
    """

    transformation_ref: str = Field(min_length=1, max_length=256)
    input_refs: list[str] = Field(min_length=1)
    output_refs: list[str] = Field(min_length=1)
    weight: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None


class HeliosProvenanceRecord(_HeliosBaseModel):
    """Abstract base type carrying fields common to every record."""

    id: str = Field(min_length=1, max_length=256)
    record_type: Literal[
        "HeliosDatasetRecord",
        "HeliosModelOutputRecord",
        "HeliosTransformationRecord",
        "HeliosFusedOutputRecord",
    ]
    schema_version: Literal["0.1.0"] = SCHEMA_VERSION
    created_at: AwareDatetime
    agent: Agent

    # subclass-set JSON-LD type IRI
    _jsonld_type: ClassVar[str] = "helios:HeliosProvenanceRecord"

    def to_jsonld(self) -> dict[str, Any]:
        """Emit an RO-Crate 1.2-compatible JSON-LD fragment for this record.

        The shape is intentionally flat (no nested ``@graph``); callers
        assembling a full RO-Crate are expected to wrap the fragments
        themselves.
        """

        # mode='json' coerces datetimes to ISO strings, etc.
        payload: dict[str, Any] = self.model_dump(mode="json", by_alias=True)
        return {
            "@context": JSONLD_CONTEXT_URI,
            "@type": self._jsonld_type,
            "@id": self.id,
            **payload,
        }


class HeliosDatasetRecord(HeliosProvenanceRecord):
    """Dataset-level metadata for one upstream space-weather data source.

    Crosswalkable to SPASE 2.7.1 ``NumericalData`` / ``Catalog`` resources via
    :func:`helios_provenance.crosswalk.dataset_to_spase`.
    """

    record_type: Literal["HeliosDatasetRecord"] = "HeliosDatasetRecord"
    source: str = Field(min_length=1)
    mission: str | None = None
    instrument: str | None = None
    format: str = Field(min_length=1)
    temporal_coverage: TemporalCoverage
    spatial_coverage: SpatialCoverage | None = None
    doi: Annotated[str | None, Field(pattern=r"^(doi:)?10\..+/.+")] = None
    source_url: str
    license: str | None = None
    ingestion_timestamp: AwareDatetime
    spase_resource_id: Annotated[str | None, Field(pattern=r"^spase://")] = None

    _jsonld_type: ClassVar[str] = "helios:HeliosDatasetRecord"


class HeliosModelOutputRecord(HeliosProvenanceRecord):
    """A single output value from an upstream model (or measurement) at one timestamp.

    Examples (one record each):

    * a DONKI flare-notification ``activityID``,
    * a single SEP Scoreboard A onset-probability value at a given timestamp,
    * a NOAA SWPC Kp index sample,
    * a CDDIS GIM TEC value at a specific gridpoint and epoch,
    * a GOES proton-flux sample,
    * a DSCOVR solar-wind sample.
    """

    record_type: Literal["HeliosModelOutputRecord"] = "HeliosModelOutputRecord"
    model_id: str = Field(min_length=1)
    model_version: str
    dataset_refs: list[str] = Field(min_length=1)
    timestamp: AwareDatetime
    location: SpatialCoverage | None = None
    value: float | int | str | bool
    value_units: str
    confidence_interval: ConfidenceInterval | None = None
    ingestion_timestamp: AwareDatetime
    extra: dict[str, Any] | None = None

    _jsonld_type: ClassVar[str] = "helios:HeliosModelOutputRecord"


class HeliosTransformationRecord(HeliosProvenanceRecord):
    """A transformation applied during fusion. Maps to W3C PROV ``Activity``."""

    record_type: Literal["HeliosTransformationRecord"] = "HeliosTransformationRecord"
    type: Literal["calibration", "bma", "conformal", "scaling", "filter", "other"]
    parameters: dict[str, Any]
    code_ref: str = Field(min_length=1)
    input_refs: list[str] = Field(min_length=1)
    output_refs: list[str] = Field(min_length=1)

    _jsonld_type: ClassVar[str] = "helios:HeliosTransformationRecord"


class HeliosFusedOutputRecord(HeliosProvenanceRecord):
    """The headline HELIOS contribution.

    A single fused output value with **full feature-level lineage**: which
    upstream model outputs contributed, at what BMA weights, with what
    calibration, with what conformal interval. ``provenance_chain_hash`` is a
    SHA-256 of the canonicalised :attr:`lineage` plus the value/timestamp
    pinning so any downstream mutation is detectable.

    Hash invariants are enforced by :func:`helios_provenance.hashing.lineage_hash`.
    """

    record_type: Literal["HeliosFusedOutputRecord"] = "HeliosFusedOutputRecord"
    prediction_target: str = Field(min_length=1)
    timestamp: AwareDatetime
    location: SpatialCoverage | None = None
    value: float | int
    value_units: str
    conformal_interval: ConformalInterval
    lineage: list[LineageStep] = Field(min_length=1)
    provenance_chain_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    _jsonld_type: ClassVar[str] = "helios:HeliosFusedOutputRecord"

    def verify_hash(self) -> bool:
        """Recompute the chain hash and compare against the stored value.

        Returns ``True`` iff the lineage has not been tampered with after
        record creation.
        """

        # Local import to keep modules.py free of circular imports.
        from helios_provenance.hashing import lineage_hash

        recomputed = lineage_hash(
            lineage=[step.model_dump(mode="json") for step in self.lineage],
            prediction_target=self.prediction_target,
            timestamp=_datetime_to_iso(self.timestamp),
            value=self.value,
            value_units=self.value_units,
        )
        return recomputed == self.provenance_chain_hash

    @classmethod
    def build_with_hash(
        cls,
        *,
        id: str,
        agent: Agent,
        created_at: datetime,
        prediction_target: str,
        timestamp: datetime,
        value: float,
        value_units: str,
        conformal_interval: ConformalInterval,
        lineage: list[LineageStep],
        location: SpatialCoverage | None = None,
    ) -> Self:
        """Construct a :class:`HeliosFusedOutputRecord` with the chain hash computed.

        Convenience constructor for application code that builds fused outputs
        programmatically rather than parsing them from JSON.
        """

        from helios_provenance.hashing import lineage_hash

        canonical_timestamp = _datetime_to_iso(timestamp)
        chain_hash = lineage_hash(
            lineage=[step.model_dump(mode="json") for step in lineage],
            prediction_target=prediction_target,
            timestamp=canonical_timestamp,
            value=value,
            value_units=value_units,
        )
        return cls(
            id=id,
            agent=agent,
            created_at=created_at,
            prediction_target=prediction_target,
            timestamp=timestamp,
            value=value,
            value_units=value_units,
            conformal_interval=conformal_interval,
            lineage=lineage,
            provenance_chain_hash=chain_hash,
            location=location,
        )


_RECORD_TYPES: dict[
    str,
    type[HeliosProvenanceRecord],
] = {
    "HeliosDatasetRecord": HeliosDatasetRecord,
    "HeliosModelOutputRecord": HeliosModelOutputRecord,
    "HeliosTransformationRecord": HeliosTransformationRecord,
    "HeliosFusedOutputRecord": HeliosFusedOutputRecord,
}


def parse_record(payload: Mapping[str, Any]) -> HeliosProvenanceRecord:
    """Parse an arbitrary HELIOS provenance record by inspecting ``record_type``.

    Raises :class:`ValueError` if ``record_type`` is missing or unknown, and
    :class:`pydantic.ValidationError` for any field-level failures.
    """

    rt = payload.get("record_type")
    if not isinstance(rt, str):
        raise ValueError("record_type field is required and must be a string")
    model_cls = _RECORD_TYPES.get(rt)
    if model_cls is None:
        raise ValueError(
            f"unknown record_type {rt!r}; expected one of {sorted(_RECORD_TYPES)}"
        )
    logger.debug("parsing %s record", rt)
    return model_cls.model_validate(payload)
