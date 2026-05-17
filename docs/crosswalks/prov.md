# Crosswalk: HELIOS Provenance v0.1 ↔ W3C PROV-JSON

[W3C PROV-JSON](https://www.w3.org/Submission/prov-json/) is the JSON
serialisation of the W3C PROV data model. HELIOS adopts PROV-JSON's
relation graph (`used`, `wasGeneratedBy`, `wasDerivedFrom`, `wasAttributedTo`)
for lineage. This document maps HELIOS record types onto PROV concepts.

## Concept mapping

| HELIOS record type | PROV concept |
|---|---|
| `HeliosDatasetRecord` | `Entity` (immutable) |
| `HeliosModelOutputRecord` | `Entity` (immutable; one value at one timestamp) |
| `HeliosTransformationRecord` | `Activity` (the act of calibrating / averaging / wrapping) |
| `HeliosFusedOutputRecord` | `Entity` (derived through a chain of activities) |
| `Agent` | `Agent` (software, service, person, or organisation) |

## Relation mapping

| HELIOS field / structure | PROV relation | Edge from → to |
|---|---|---|
| `HeliosTransformationRecord.input_refs` | `used` | `Activity` → `Entity` |
| `HeliosTransformationRecord.output_refs` | `wasGeneratedBy` | `Entity` → `Activity` |
| `HeliosFusedOutputRecord.lineage[*]` (each step) | `wasDerivedFrom` | output_ref → input_ref (Cartesian product within a step) |
| `HeliosProvenanceRecord.agent` | `wasAttributedTo` | `Entity` or `Activity` → `Agent` |
| `Agent.type = "person" \| "organization"` | PROV agent `prov:type` `prov:Person` / `prov:Organization` | — |
| `Agent.type = "software" \| "service"` | PROV agent `prov:type` `prov:SoftwareAgent` | — |

## Bundle layout

The HELIOS-to-PROV emitter (see
`helios_provenance.crosswalk.records_to_prov_json`) produces a single PROV
document covering the records passed in:

```json
{
  "prefix": {
    "helios": "https://577-industries.github.io/helios-provenance-spec/ns/",
    "prov":   "http://www.w3.org/ns/prov#"
  },
  "entity":         { "<dataset-id>": {...}, "<output-id>": {...}, "<fused-id>": {...} },
  "activity":       { "<transform-id>": {...} },
  "agent":          { "<agent-id>": {...} },
  "used":           { "_:u1": {"prov:activity": "<transform-id>", "prov:entity": "<input-id>"}, ... },
  "wasGeneratedBy": { "_:g1": {"prov:entity": "<output-id>", "prov:activity": "<transform-id>"}, ... },
  "wasDerivedFrom": { "_:d1": {"prov:generatedEntity": "<fused-id>", "prov:usedEntity": "<input-id>", "helios:transformationRef": "<transform-id>"}, ... },
  "wasAttributedTo": { "_:attr1": {"prov:entity": "<record-id>", "prov:agent": "<agent-id>"}, ... }
}
```

The blank-node IDs (`_:u1`, `_:g1`, `_:d1`, `_:attr1`) are allocated
sequentially within the emit call. They are stable within a single emit call
but NOT stable across calls — they are not intended to be persisted.

## What HELIOS adds beyond PROV

PROV gives us the lineage graph; HELIOS extends it with:

1. **A canonical hash** of the lineage chain
   (`HeliosFusedOutputRecord.provenance_chain_hash`) — PROV alone has no
   tamper-evidence story.
2. **Numeric weights** on each lineage step (BMA mixture weights) — PROV
   relations are unweighted.
3. **Conformal intervals** as first-class fields on the fused entity — PROV
   has no native uncertainty representation.
4. **Schema-versioned, fully-typed records** — PROV deliberately leaves the
   entity/activity attribute namespace open.

## Round-trip caveats

PROV-JSON → HELIOS is **not** lossless. HELIOS records carry domain fields
(`prediction_target`, `value_units`, `conformal_interval`) that have no
PROV-native representation; those fields would have to ride as
`helios:<field>` annotations on the entity.

HELIOS → PROV-JSON via `records_to_prov_json` is lossy in the same way: PROV
keeps the graph structure but loses the typed payload. Treat PROV-JSON as a
**publication format for the lineage graph**, not a replacement for the
HELIOS records themselves.

## See also

* `spase.md` — SPASE crosswalk for dataset-level metadata.
* `ro-crate.md` — packaging multiple HELIOS records as an RO-Crate JSON-LD.
