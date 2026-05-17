# Schema reference

The canonical schema lives at
[`schema/helios-provenance-v0.1.json`](https://github.com/577Industries/helios-provenance-spec/blob/main/schema/helios-provenance-v0.1.json)
and is shipped inside the wheel at
`helios_provenance/_schema/helios-provenance-v0.1.json`.

It is a JSON Schema 2020-12 document with four top-level record types under
a `oneOf` discriminator. All four extend a common
`HeliosProvenanceRecord` base and reject extra properties.

## Common base

Every record carries:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string (1-256 chars) | ✓ | Convention: `helios:<type>:<source>:<localpart>`. |
| `record_type` | enum | ✓ | One of the four type names below. |
| `schema_version` | const `"0.1.0"` | ✓ | Pinned to this spec version. |
| `created_at` | RFC-3339 timestamp | ✓ | When this provenance record was created. |
| `agent` | Agent object | ✓ | Who/what created the record. |

The `Agent` sub-object:

| Field | Type | Required |
|---|---|---|
| `id` | string | ✓ |
| `name` | string | ✓ |
| `type` | `software` \| `service` \| `person` \| `organization` | ✓ |
| `version` | string | optional |

## `HeliosDatasetRecord`

Dataset-level metadata for one upstream space-weather data source.
Crosswalkable to SPASE 2.7.1 `NumericalData` / `Catalog` resources.

| Field | Type | Required | Notes |
|---|---|---|---|
| `source` | string | ✓ | Short label (e.g. `"NASA-DONKI"`, `"CCMC-SEP-Scoreboard-A"`). |
| `mission` | string | optional | Mission/programme. |
| `instrument` | string | optional | Instrument/product. |
| `format` | string | ✓ | MIME or short token (e.g. `"application/json"`, `"IONEX"`). |
| `temporal_coverage` | TemporalCoverage | ✓ | `{start, stop?, cadence?}` |
| `spatial_coverage` | SpatialCoverage | optional | `{frame?, region?, bbox?, point?}` |
| `doi` | string (DOI pattern) | optional | `10.x/y` form. |
| `source_url` | URI | ✓ | Where this dataset was fetched from. |
| `license` | string | optional | SPDX identifier or short label. |
| `ingestion_timestamp` | timestamp | ✓ | When the HELIOS ingestion tier fetched it. |
| `spase_resource_id` | `spase://...` URI | optional | Anchor the SPASE crosswalk. |

## `HeliosModelOutputRecord`

A single output value from an upstream model (or measurement) at one
timestamp and optional location.

| Field | Type | Required | Notes |
|---|---|---|---|
| `model_id` | string | ✓ | Short model/source label. |
| `model_version` | string | ✓ | Or `"unspecified"`. |
| `dataset_refs` | array of IDs (≥1) | ✓ | The `HeliosDatasetRecord`s this output came from. |
| `timestamp` | timestamp | ✓ | Valid time of this value. |
| `location` | SpatialCoverage | optional | For spatially-resolved values. |
| `value` | number/string/bool | ✓ | The output. |
| `value_units` | string | ✓ | UDUNITS-compatible (e.g. `"pfu"`, `"TECU"`, `"1"`). |
| `confidence_interval` | ConfidenceInterval | optional | `{lower, upper, alpha, method?}` |
| `ingestion_timestamp` | timestamp | ✓ | |
| `extra` | object | optional | Source-specific metadata. |

## `HeliosTransformationRecord`

A transformation applied during fusion — calibration, BMA averaging,
conformal interval, scaling, filter. Maps to W3C PROV `Activity`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | enum | ✓ | `calibration` \| `bma` \| `conformal` \| `scaling` \| `filter` \| `other`. |
| `parameters` | object | ✓ | Free-form. Suggested keys: `method`, `fitted_on`, `hyperparameters`. |
| `code_ref` | string | ✓ | URI / git permalink to the implementing code. |
| `input_refs` | array of IDs (≥1) | ✓ | Records consumed. |
| `output_refs` | array of IDs (≥1) | ✓ | Records produced. |

## `HeliosFusedOutputRecord`

The headline contribution: a single fused output value with full
feature-level lineage.

| Field | Type | Required | Notes |
|---|---|---|---|
| `prediction_target` | string | ✓ | E.g. `"sep_all_clear_revocation"`. |
| `timestamp` | timestamp | ✓ | Valid time. |
| `location` | SpatialCoverage | optional | For spatially-resolved fused outputs. |
| `value` | number | ✓ | The fused value. |
| `value_units` | string | ✓ | |
| `conformal_interval` | ConformalInterval | ✓ | `{lower, upper, alpha, method, calibration_set_size?}` |
| `lineage` | array of LineageStep (≥1) | ✓ | Ordered. Order is causally significant. |
| `provenance_chain_hash` | 64-char hex | ✓ | SHA-256 of canonicalised lineage. |

A `LineageStep`:

| Field | Type | Required |
|---|---|---|
| `transformation_ref` | ID | ✓ |
| `input_refs` | array of IDs (≥1) | ✓ |
| `output_refs` | array of IDs (≥1) | ✓ |
| `weight` | float in `[0, 1]` | optional |
| `notes` | string | optional |

## Validation

```bash
helios-provenance-validate path/to/record.json
```

or in code:

```python
from helios_provenance import HeliosProvenanceValidator
v = HeliosProvenanceValidator()
errors = v.errors(record_dict)  # list of jsonschema.ValidationError (empty == valid)
```

The validator uses `jsonschema.FormatChecker` so `format: date-time` and
`format: uri` keywords are enforced, not just annotated.
