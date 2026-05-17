# Changelog

All notable changes to this project are documented here, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-17

### Added
- JSON Schema 2020-12 for 4 record types: `HeliosDatasetRecord`, `HeliosModelOutputRecord`, `HeliosTransformationRecord`, `HeliosFusedOutputRecord`.
- pydantic v2 reference implementation with RFC-8785 JCS canonical-JSON tamper-evident lineage hashing.
- 11 worked examples including end-to-end fused SEP all-clear lineage tracing BMA + isotonic + conformal across three Scoreboard A inputs.
- Crosswalks: SPASE 2.7.1, W3C PROV-JSON, RO-Crate 1.2 JSON-LD.
- RFC-0001 issued for community comment (8 open questions in §6).
- CLI: `helios-provenance-validate` for schema validation against arbitrary files.
- 98 tests passing at 98% line+branch coverage. `mypy --strict`, `ruff`, `ruff format --check` all clean.

See [GitHub releases](https://github.com/577Industries/helios-provenance-spec/releases/tag/v0.1.0) for the canonical release notes.
