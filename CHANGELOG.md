# Changelog

All notable changes to `helios-provenance-spec` are documented here.

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Pre-1.0 (`0.x.y`) releases are **unstable**; any minor-version bump may
introduce breaking schema or API changes. Producers and consumers should pin
to `helios-provenance-spec==0.1.*` (or equivalent) during the RFC period.

## [0.1.0] — 2026-05-17

First public draft. **Issued as RFC.** Community feedback expected before
stabilising to v1.0; see
[RFC-0001](rfc/RFC-0001-feature-lineage.md) and
[issue #1](https://github.com/577Industries/helios-provenance-spec/issues/1).

### Added — schema

- `schema/helios-provenance-v0.1.json` — JSON Schema (draft 2020-12)
  defining four record types:
  - `HeliosDatasetRecord` — dataset-level metadata, SPASE-compatible.
  - `HeliosModelOutputRecord` — one value at one timestamp from one upstream
    model or measurement.
  - `HeliosTransformationRecord` — one transformation invocation
    (calibration / BMA / conformal / scaling / filter / other).
  - `HeliosFusedOutputRecord` — fused output with full feature-level lineage
    and a tamper-evident SHA-256 chain hash.
- Eleven worked examples covering DONKI flare notifications, CCMC SEP
  Scoreboard A outputs, NOAA SWPC Kp, CDDIS GIM TEC, GOES proton flux,
  DSCOVR solar wind, isotonic / BMA / conformal transformations, and a
  fully-traced fused SEP all-clear revocation output for 2024-05-08T22:00Z.
- Field-by-field crosswalks to SPASE 2.7.1 (`schema/crosswalks/spase.md`),
  W3C PROV-JSON (`schema/crosswalks/prov.md`), and RO-Crate 1.2
  (`schema/crosswalks/ro-crate.md`).

### Added — Python reference implementation (`helios_provenance`)

- Pydantic v2 models mirroring the JSON Schema 1:1 with `extra="forbid"`.
- `HeliosFusedOutputRecord.build_with_hash(...)` convenience constructor
  that computes the tamper-evident chain hash.
- `HeliosFusedOutputRecord.verify_hash()` for tamper detection.
- `parse_record(...)` to dispatch on `record_type` and parse arbitrary JSON.
- `to_jsonld()` on every record type, emitting RO-Crate 1.2-compatible
  JSON-LD fragments.
- `helios_provenance.hashing` — RFC-8785 JCS canonical-JSON hashing with
  a documented fallback when `rfc8785` is not available; null-stripping
  normalisation so `{"weight": null}` and `{}` hash identically.
- `helios_provenance.validator.HeliosProvenanceValidator` — `jsonschema`
  wrapper with `FormatChecker` so `date-time` and `uri` format keywords are
  asserted, not annotated.
- CLI: `helios-provenance-validate <file>...` (also `python -m
  helios_provenance.validator`). Supports stdin via `-` and a `-v` flag.
- `helios_provenance.crosswalk` — `dataset_to_spase_xml` and
  `records_to_prov_json` emitters.

### Added — RFC

- `rfc/RFC-0001-feature-lineage.md` — design document. Motivation
  (proposal §1.4 + §4.2), background survey (SPASE / PROV-JSON / RO-Crate),
  design, the centrepiece worked example, eight open questions for the
  community, adoption ask, stability commitment.

### Added — docs

- MkDocs site with Home, Schema reference, Worked examples, API reference,
  RFC, and crosswalks pages.

### Added — tests

- 98 tests, 98% coverage on `src/helios_provenance/`:
  - pydantic round-trips for all eleven examples,
  - JSON Schema negative cases (missing fields, wrong types, extra
    properties, wrong record_type, non-iso timestamps, out-of-range alphas,
    malformed hashes),
  - hashing invariants (key-order insensitivity, step-order sensitivity,
    tamper detection, null-stripping equivalence, NaN/Inf rejection),
  - validator CLI (exit codes, stdin, verbose flag, error reporting),
  - SPASE XML emitter (well-formedness, DOI/cadence/synth ResourceID),
  - PROV-JSON emitter (entities, activities, agents, used /
    wasGeneratedBy / wasDerivedFrom / wasAttributedTo edges).

### Added — tooling

- `ruff check .`, `ruff format --check .`, and `mypy --strict` all green.
- `pyproject.toml` declares `rfc3339-validator` and `rfc3987` deps so the
  validator's format checks work out of the box.

### Known limitations / open questions

See RFC-0001 §6. Headline items:

- `code_ref` format is intentionally free-form for v0.1; community input
  invited on whether to require git permalink + SHA or accept any URI.
- `@context` URI in `to_jsonld()` is a placeholder pending v1.0 promotion.
- `record_type` enum may grow in v0.2 (e.g. `HeliosCalibrationModelRecord`
  to factor out reusable calibration models).
- Tamper-evidence hash covers lineage + value + timestamp + units;
  community input invited on whether to extend to `conformal_interval`,
  `location`, and `agent`.

[0.1.0]: https://github.com/577Industries/helios-provenance-spec/releases/tag/v0.1.0
