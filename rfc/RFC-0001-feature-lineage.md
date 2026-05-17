# RFC-0001: Feature-Level Provenance for Heliophysics Fusion Systems

| Field | Value |
|---|---|
| RFC number | 0001 |
| Status | **Draft — open for community comment** |
| Authors | Thomas Waweru (577 Industries) |
| Schema version | 0.1.0 |
| Date | 2026-05-17 |
| Discussion | <https://github.com/577Industries/helios-provenance-spec/issues/1> |
| Repository | <https://github.com/577Industries/helios-provenance-spec> |

## Abstract

We propose **HELIOS Provenance v0.1**, a JSON-Schema-defined record format that
captures **feature-level** provenance for fused space-weather model outputs.
Existing community standards — SPASE 2.7.1 for dataset metadata, W3C PROV-JSON
for lineage relations, RO-Crate 1.2 for packaging — handle data-set-level
provenance well but stop short of capturing *which specific upstream values
contributed to one specific predicted value via which specific
transformations*. Operational fusion engines (Bayesian model averaging,
isotonic-regression calibration, conformal-prediction wrappers) need that
finer granularity. This RFC defines four record types — `HeliosDatasetRecord`,
`HeliosModelOutputRecord`, `HeliosTransformationRecord`, `HeliosFusedOutputRecord`
— with a SHA-256-based tamper-evident lineage chain on the fused record. We
provide a pydantic v2 reference implementation, eleven worked examples, and
crosswalks to SPASE / PROV-JSON / RO-Crate so adopters don't have to choose
between HELIOS and the standards they already publish against.

We seek community feedback before stabilising at v1.0.

## 1. Motivation

577 Industries' NASA SBIR Phase I proposal "HELIOS: Heliophysics-Enhanced
Location Integrity and Operations System" (subtopic SPWX.1.S26A) frames the
provenance affordance as essential to both science transition and operator
adoption.

From the **CONOPS** (proposal §1.4):

> Every output exposes a drill-down to its full provenance chain — which
> upstream models contributed at which weights, with which calibration
> history. This provenance affordance is essential for SRAG console adoption
> and for the CCMC proving-ground evaluation pathway.

From **Innovation #2** (§4.2):

> Provenance-aware architecture. Every output traces to its underlying models,
> data feeds, and assumptions — a property required for CCMC proving-ground
> evaluation, ARRT-compatible mission integration, and the operator trust that
> safety-critical adoption demands.

The operational pull is concrete: an SRAG console operator deciding whether to
revoke all-clear status under the operational SEP thresholds (≥10 MeV at 10
pfu; ≥100 MeV at 1 pfu) currently cross-references raw outputs from UMASEP,
HESPERIA REleASE, SEPMOD, and MagPy across Scoreboards A/B/C. When a fusion
engine reduces those into a single decision-calibrated probability with a
conformal interval, the operator (and the CCMC validator, and the
post-incident reviewer) needs to be able to ask: *which upstream model
dominated the BMA weight at 22:00Z on 8 May 2024? what calibration window was
in force? what was the conformal calibration set?* — and get a defensible
answer.

The same need applies to the precision-agriculture slice. When a fused
predicted RTK error of 4.7 cm causes an operator to delay planting, the
provenance record is what supports the *parametric-insurance* business model
of §6.4: the verified threshold crossing has to be auditable.

## 2. Background and Survey

We surveyed the heliophysics and research-object-metadata ecosystems for prior
art that already covers feature-level lineage. None does, but three standards
are close enough to **compose** rather than replace.

### 2.1 SPASE 2.7.1

[SPASE](https://spase-group.org/) is the heliophysics community's dataset
metadata standard. SPASE 2.7.1 (current at time of writing) defines resource
classes (`NumericalData`, `Catalog`, `Instrument`, `Observatory`, etc.) and a
rich vocabulary for time spans, cadence, observed regions, coordinate frames,
measurement types, and rights. It's the right standard for declaring "this is
the DSCOVR PlasMag Faraday-Cup L1 dataset, here's its DOI, here's its time
span, here's the IGS analysis centre that produced it."

What SPASE does **not** cover:

* per-value lineage,
* model transformations,
* probabilistic outputs with calibration history,
* uncertainty intervals as first-class fields,
* tamper-evident hash chains.

That's appropriate — SPASE is a dataset-discovery standard, not a fusion-output
standard. HELIOS profiles SPASE for the `HeliosDatasetRecord` and extends
beyond it for the other three record types.

### 2.2 W3C PROV-JSON

[W3C PROV-JSON](https://www.w3.org/Submission/prov-json/) is the JSON
serialisation of the W3C PROV data model — `Entity`, `Activity`, `Agent`, and
the relations `used`, `wasGeneratedBy`, `wasDerivedFrom`, `wasAttributedTo`,
`wasInformedBy`. PROV is the right vocabulary for the lineage *graph*: which
activities consumed which entities and generated which others.

What PROV-JSON does **not** cover:

* numeric weights on relations (BMA mixture weights),
* uncertainty intervals,
* a tamper-evidence story,
* heliophysics-specific schema for the entities themselves.

PROV is deliberately content-agnostic. HELIOS uses PROV's vocabulary for the
lineage edges (`HeliosTransformationRecord` ⇒ `used` + `wasGeneratedBy`;
`HeliosFusedOutputRecord.lineage[*]` ⇒ `wasDerivedFrom`) and supplies the
domain-typed entity/activity payloads itself.

### 2.3 RO-Crate 1.2

[RO-Crate 1.2](https://www.researchobject.org/ro-crate/1.2/) is the
community-standard packaging format for research objects — bundles of data and
metadata expressed as JSON-LD. RO-Crate gives us:

* a recognised packaging container,
* a JSON-LD substrate that plays well with citation tools (Zenodo, DataCite),
* a `@context` mechanism for typed annotations.

What RO-Crate does **not** cover:

* per-value semantics inside a crate (it's a packaging standard),
* heliophysics-specific record types.

HELIOS records emit `to_jsonld()` fragments that drop cleanly into the
`@graph` of an RO-Crate, with the HELIOS namespace under `@context`.

### 2.4 What's missing

To restate: no existing standard captures, in one place, *all of*:

1. **Per-value** lineage (not just per-dataset).
2. **Transformation records** with parameters and code references that bind
   inputs to outputs.
3. **BMA mixture weights** as first-class fields on the lineage edges.
4. **Calibration history** (which calibration model was in force when this
   value was produced, fit on what window).
5. **Distribution-free uncertainty** (conformal intervals as first-class
   fields on the fused output, not as free-form annotations).
6. **Tamper-evident hashing** of the lineage chain.

The HELIOS contribution is the missing composition layer.

## 3. Design

### 3.1 Four record types

The spec defines four record types, all extending a common
`HeliosProvenanceRecord` base (`id`, `record_type`, `schema_version`,
`created_at`, `agent`):

| Record type | Captures | PROV mapping |
|---|---|---|
| `HeliosDatasetRecord` | One upstream dataset snapshot (DONKI page, IONEX file, Scoreboard A snapshot) | `Entity` |
| `HeliosModelOutputRecord` | One value at one timestamp from one model (a Kp sample, a TEC gridpoint, a Scoreboard A onset probability) | `Entity` |
| `HeliosTransformationRecord` | One transformation invocation (an isotonic-calibration step, a BMA averaging step, a conformal-interval wrapping step) | `Activity` |
| `HeliosFusedOutputRecord` | One fused output value with full feature-level lineage | `Entity` |

All four reject extra properties (`unevaluatedProperties: false` at the schema
level, `extra="forbid"` at the pydantic level). Strict typing is deliberate:
if a producer adds a new field, the consumers find out at validation time
instead of silently dropping data.

### 3.2 Lineage as an ordered list of steps

A `HeliosFusedOutputRecord` carries a `lineage` field — an **ordered** list
of `LineageStep` objects. Each step has:

* `transformation_ref` — ID of a `HeliosTransformationRecord`,
* `input_refs` — IDs of the model-output records consumed,
* `output_refs` — IDs of the model-output records produced,
* `weight` (optional) — numeric weight applied at this step,
* `notes` (optional) — free-form annotation.

Order is significant: HELIOS lineage is causal, so reordering the steps
must yield a different chain hash. We do **not** sort the list when hashing;
only object-key order is normalised within each step.

### 3.3 Tamper-evident chain hashing

`HeliosFusedOutputRecord.provenance_chain_hash` is a lowercase hex SHA-256
over a canonicalised payload of the lineage plus a value/timestamp pinning:

```json
{
  "schema_version": "0.1.0",
  "prediction_target": "<prediction target>",
  "timestamp": "<iso timestamp>",
  "value": <fused value>,
  "value_units": "<udunits>",
  "lineage": [<lineage steps, nulls stripped>]
}
```

Canonicalisation uses [RFC 8785 JCS](https://datatracker.ietf.org/doc/html/rfc8785)
when the `rfc8785` package is installed, falling back to
`json.dumps(..., sort_keys=True, separators=(",", ":"), allow_nan=False)`
otherwise. Both paths produce identical bytes for JCS-safe inputs (the schema
disallows NaN/Infinity).

This gives us:

* **Tamper detection**: any mutation of the lineage, value, timestamp, or
  unit flips the hash.
* **Reproducibility**: independent parties can recompute the hash from the
  same lineage.
* **Append-only auditability**: a downstream system can store
  `(record_id, provenance_chain_hash, timestamp)` triples without storing
  the full lineage payload, then verify on demand.

### 3.4 Crosswalks, not replacements

For each near-neighbour standard, the repo ships a crosswalk (see
`schema/crosswalks/`):

* `spase.md` — every `HeliosDatasetRecord` field mapped to its SPASE 2.7.1
  element. A heliophysics adopter publishing a HELIOS-ingested dataset in a
  SPASE registry can use `helios_provenance.crosswalk.dataset_to_spase_xml`
  to emit a stub and hand-complete the SPASE-only fields (`Parameter`,
  `MeasurementType`).
* `prov.md` — HELIOS record types mapped to PROV concepts; the
  `records_to_prov_json` emitter produces a PROV-JSON document covering an
  arbitrary set of records.
* `ro-crate.md` — every record's `.to_jsonld()` output drops into the
  `@graph` of an RO-Crate 1.2 zip.

## 4. Worked example: SEP all-clear revocation, 8 May 2024 22:00 UTC

The eleven examples under `schema/examples/` build up to a single fused
output that traces back through BMA + isotonic + conformal to three upstream
Scoreboard A inputs. This is the demonstration centrepiece of the RFC.

The fused record `helios:fused:sep-all-clear-revocation/2024-05-08T22:00Z`:

* `prediction_target = "sep_all_clear_revocation"`,
* `value = 0.69` (probability the all-clear status should be revoked),
* `value_units = "1"` (dimensionless),
* `conformal_interval = { lower: 0.49, upper: 0.86, alpha: 0.1, method: "conformal-split", calibration_set_size: 412 }`,
* `provenance_chain_hash = c7935d3f1df8d1d8eff627b16f8eb383be4cc31fe217bbd66a06e271197b7877`.

Its three-step `lineage`:

1. **Isotonic calibration** (`helios:transform:calibration/isotonic/…`).
   Consumes the raw onset probabilities from UMASEP-10, SEPMOD, and MagPy
   (three `HeliosModelOutputRecord`s on Scoreboard A). Produces three
   calibrated probabilities. Calibration model: isotonic regression fit on a
   rolling 90-day verification window (2024-02-08 .. 2024-05-08).
2. **BMA averaging** (`helios:transform:bma/…`). Consumes the three
   calibrated probabilities. BMA weights {UMASEP-10: 0.46, SEPMOD: 0.31,
   MagPy: 0.23} are themselves a function of 90-day rolling Brier-score skill;
   the weights are recorded inside the transformation record's `parameters`.
   Produces one uncalibrated fused probability.
3. **Conformal wrapping** (`helios:transform:conformal/…`). Consumes the
   uncalibrated fused probability and produces the final fused output with
   its conformal interval. Calibration set size 412; stratified by Kp
   severity bin so the interval doesn't collapse on the extreme events that
   matter most.

The hash recomputes deterministically:

```python
>>> from helios_provenance import parse_record
>>> rec = parse_record(json.loads(open("schema/examples/11-fused-sep-all-clear.json").read()))
>>> rec.verify_hash()
True
```

Mutating any field in any lineage step flips the hash:

```python
>>> tampered = rec.model_copy(deep=True)
>>> tampered.lineage[0].notes = "tampered"
>>> tampered.verify_hash()
False
```

That's the full story the RFC is asking the community to ratify: *here is the
canonical example, here is the canonical hash, here is the deterministic
recomputation*.

## 5. Compatibility

Adopters can publish HELIOS records alongside their existing SPASE
registrations, PROV-JSON bundles, or RO-Crate exports — the crosswalks are
designed to be *additive*. A HELIOS-ingested dataset's SPASE registration is
the SPASE registration; the HELIOS record is an enrichment that adds value-
and transformation-level provenance, not a replacement.

The reference implementation (`helios_provenance` on PyPI) targets Python
3.11+ with pydantic v2 and minimal dependencies. The schema itself is
language-neutral.

## 6. Open questions for the community

We deliberately under-specify some fields in v0.1 because the right answer
depends on how the community wants to use the spec. We seek input on:

1. **`code_ref` format.** Should it be (a) a free-form URI, (b) a git
   permalink with commit SHA, (c) a content-addressable hash (git-SHA-256 or
   IPFS CID), (d) all of the above (let the producer choose)? The reference
   implementation currently accepts any non-empty string; we suggest
   `git+https://...@<sha>#path=<path>` as the canonical form but do not
   enforce it.
2. **Record-ID namespace.** v0.1 uses `helios:<type>:<source>:<localpart>`
   as a convention but does not enforce it at the schema level. Should the
   schema mint a stable URI scheme (`urn:helios:...`) or stay convention-only?
3. **`spase_resource_id` requirement.** Should every `HeliosDatasetRecord`
   that maps to a registered SPASE resource be **required** to carry the
   SPASE `ResourceID`, or remain optional? Mandatory would force adopters
   to register with SPASE first; optional permits ahead-of-SPASE adoption.
4. **`extra` on `HeliosModelOutputRecord`.** v0.1 allows free-form
   `extra` to accommodate source-specific metadata (DONKI `activityID`,
   Scoreboard `event_window`, etc.). Should `extra` itself have a sub-schema
   per-source? That would help static analysis but ossifies the spec.
5. **Conformal-interval method enum.** v0.1 lists `conformal-split`,
   `conformal-mondrian`, `conformal-cv-plus`, `other`. Should we add
   `conformal-quantile-regression`, `conformal-locally-adaptive`,
   `inductive-conformal` as named values, or keep `other` + parameters as the
   extension point?
6. **Versioning policy.** v0.1 is `0.1.0`, expected to break before `1.0.0`.
   Should `record_type` itself carry a version (e.g. `HeliosFusedOutputRecord/v0.1`)
   or just the top-level `schema_version`? The current design uses
   `schema_version` only.
7. **JSON-LD context promotion.** The `@context` URI in the reference
   implementation is a placeholder. When (and where) should we publish a
   stable HELIOS namespace? Candidates: `577industries.github.io`
   (organisational), `w3id.org/helios/...` (community-owned), or piggyback
   on `schema.org` + PROV-O.
8. **Tamper-evidence policy.** The current hash covers the lineage plus
   value/timestamp/units. Should it also cover the `conformal_interval`,
   `location`, and `agent`? Arguments both ways: more coverage = stronger
   tamper-evidence, but also more frequent hash churn during
   bookkeeping-only updates.

We'd welcome comments on any of the above in issue
[#1](https://github.com/577Industries/helios-provenance-spec/issues/1).

## 7. Adoption ask

We hope to circulate this RFC to:

* the **SPASE community** (spase-group.org), to confirm the SPASE crosswalk
  doesn't fight the SPASE 2.7.1 data model;
* the **CCMC** (ccmc-feedback), to align with proving-ground evaluation needs;
* the **sunpy** and **PySPEDAS** developer communities, for adoption alongside
  existing Python heliophysics tooling;
* **NASA SRAG** and **M2M SWAO**, the two operational consumers the HELIOS
  fusion engine is targeted at, to confirm the lineage drill-down satisfies
  console-operator needs;
* the **OSF / DataCite / Zenodo** communities, for the RO-Crate packaging
  story.

Feedback channels: GitHub issues on this repository, or email
<engineering@577industries.com>.

## 8. Stability commitment

* **v0.1.0** (this RFC) is explicitly **unstable**. Field names, enum values,
  and the hash payload composition can change in any subsequent `0.x` release.
* Producers consuming v0.1 are encouraged to **pin** to `helios-provenance-spec==0.1.*`.
* The path to v1.0 is: collect community feedback ⇒ ship v0.2 incorporating
  resolutions to the open questions in §6 ⇒ field a real fusion engine
  against v0.2 for at least one full validation cycle (Table 3-1 retrospective
  per the HELIOS proposal §3.1) ⇒ promote to v1.0 with a stable IRI for the
  JSON-LD context.
* `record_type` and `schema_version` enums are reserved for v1.0; no v0.x
  release will repurpose them.

## 9. References

* HELIOS NASA SBIR Phase I proposal, §1.4 (CONOPS) and §4.2 (Innovation #2). 577 Industries Inc., 2026.
* SPASE 2.7.1 Data Model. <https://spase-group.org/data/schema/>
* W3C PROV-JSON: a JSON Representation for PROV. W3C Submission, 2013. <https://www.w3.org/Submission/prov-json/>
* RO-Crate 1.2 Specification. <https://www.researchobject.org/ro-crate/1.2/>
* RFC 8785: JSON Canonicalization Scheme (JCS). <https://datatracker.ietf.org/doc/html/rfc8785>
* JSON Schema 2020-12. <https://json-schema.org/draft/2020-12/json-schema-core.html>
* Vovk, V., Gammerman, A., Shafer, G., *Algorithmic Learning in a Random World (Conformal Prediction)*, 2nd ed., Springer, 2022.
