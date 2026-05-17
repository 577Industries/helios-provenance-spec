# Crosswalk: HELIOS Provenance v0.1 ↔ SPASE 2.7.1

[SPASE](https://spase-group.org/) is the heliophysics community's data-model
standard. HELIOS does not replace SPASE; we extend it with the lineage and
fusion-output record types that SPASE does not cover. This document maps every
HELIOS dataset field to its SPASE 2.7.1 equivalent so a HELIOS adopter can
publish HELIOS-ingested datasets in a SPASE registry without information loss.

## Top-level mapping

| HELIOS record type | SPASE resource class | Notes |
|---|---|---|
| `HeliosDatasetRecord` | `NumericalData` (or `Catalog` for event lists like DONKI) | use `Catalog` when the dataset is fundamentally a list of events, `NumericalData` for time-series. |
| `HeliosModelOutputRecord` | (no direct SPASE analogue) | SPASE describes datasets, not individual values. HELIOS adds value-level provenance. |
| `HeliosTransformationRecord` | (no direct SPASE analogue) | Lineage is W3C PROV territory; see `prov.md`. |
| `HeliosFusedOutputRecord` | (no direct SPASE analogue) | Novel HELIOS contribution. |

## `HeliosDatasetRecord` field mapping

| HELIOS field | SPASE element | XPath under `Spase/NumericalData` | Notes |
|---|---|---|---|
| `id` | `ResourceID` (via crosswalk) | `/ResourceID` | When `spase_resource_id` is set we use it directly. Otherwise we synthesise `spase://HELIOS/NumericalData/<source>/<id>`. |
| `spase_resource_id` | `ResourceID` | `/ResourceID` | Native SPASE ID when known. |
| `source` | `RepositoryID`, `ResourceName` (composite) | `/AccessInformation/RepositoryID`, `/ResourceHeader/ResourceName` | |
| `mission` | `ObservedRegion` or `Mission` (via `InstrumentID` lookup) | `/ResourceHeader/InstrumentID` | Full SPASE expansion requires SME knowledge; the stub leaves this for hand-completion. |
| `instrument` | `InstrumentID` | `/ResourceHeader/InstrumentID` | |
| `format` | `Format` | `/AccessInformation/Format` | |
| `temporal_coverage.start` / `.stop` | `TimeSpan/StartDate`, `TimeSpan/StopDate` | `/TemporalDescription/TimeSpan` | HELIOS uses ISO-8601 with explicit timezone. |
| `temporal_coverage.cadence` | `Cadence` | `/TemporalDescription/Cadence` | ISO-8601 duration (e.g. `PT2H`). |
| `spatial_coverage.region` | `ObservedRegion` | `/ResourceHeader/ObservedRegion` | SPASE region taxonomy is fixed (see SPASE dictionary). |
| `spatial_coverage.frame` | `CoordinateSystem` (via `Parameter`) | `/Parameter/CoordinateSystem` | |
| `doi` | `DOI` | `/ResourceHeader/DOI` | |
| `source_url` | `URL` under `AccessURL` | `/AccessInformation/AccessURL/URL` | |
| `license` | `RightsList` (SPASE 2.7+) | `/AccessInformation/RightsList` | Use SPDX identifier where possible. |
| `ingestion_timestamp` | `ReleaseDate` (approximate) | `/ResourceHeader/ReleaseDate` | SPASE has no native ingestion-timestamp; we put the HELIOS ingestion time in ReleaseDate. |
| `agent` | `Contact` (with `Role=DataProducer`) | `/ResourceHeader/Contact` | HELIOS adapter version goes into `Contact/Name`. |
| `created_at` | (no direct mapping) | — | HELIOS-internal record provenance, not SPASE-relevant. |
| `record_type`, `schema_version` | (no direct mapping) | — | HELIOS-internal. |

## SPASE elements not produced by HELIOS

The minimal stub deliberately omits:

* `Parameter` blocks (one per data column) — requires data-model-specific SME knowledge.
* `MeasurementType` — domain-specific (e.g. `EnergeticParticles`, `ThermalPlasma`).
* `Caveats`, `Acknowledgement`, `PublicationInfo` — operator-supplied.

A heliophysics adopter is expected to hand-complete these once before SPASE
registry submission. The HELIOS crosswalk emits everything else mechanically.

## SPASE elements with no HELIOS source

* `Version` — HELIOS emits the SPASE-version string `2.7.1`.
* `PriorID` — not modelled in HELIOS v0.1; could be added in v0.2 to support
  record renames.

## See also

* `prov.md` — W3C PROV-JSON crosswalk for the lineage relations.
* `ro-crate.md` — packaging multiple HELIOS records as an RO-Crate.
