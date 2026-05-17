# helios-provenance-spec

[![CI](https://github.com/577Industries/helios-provenance-spec/actions/workflows/ci.yml/badge.svg)](https://github.com/577Industries/helios-provenance-spec/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI](https://img.shields.io/pypi/v/helios-provenance-spec.svg)](https://pypi.org/project/helios-provenance-spec/)
[![Schema: v0.1.0](https://img.shields.io/badge/schema-v0.1.0-orange.svg)](schema/helios-provenance-v0.1.json)
[![Status: RFC](https://img.shields.io/badge/status-RFC-yellow.svg)](rfc/RFC-0001-feature-lineage.md)

> JSON Schema (draft 2020-12) describing **feature-level provenance** for
> fused space-weather model outputs, plus a pydantic v2 reference
> implementation. Composes SPASE 2.7.1, W3C PROV-JSON, and RO-Crate 1.2
> JSON-LD with a novel feature-level transformation chain. Issued as an open
> RFC for community comment.

## Status

This repository is part of the **HELIOS** programme — a NASA SBIR Phase I
effort by 577 Industries Inc. supporting subtopic SPWX.1.S26A (Advanced
Data-Driven Applications for Space Weather R2O2R). See proposal §1.4 (CONOPS)
+ §4.2 (Innovation #2).

**v0.1.0 — Request For Comments.** First publicly circulated draft. Community
feedback expected before stabilising to v1.0. Pin to `helios-provenance-spec==0.1.*`.

* Design document: [`rfc/RFC-0001-feature-lineage.md`](rfc/RFC-0001-feature-lineage.md)
* Discussion: [issue #1](https://github.com/577Industries/helios-provenance-spec/issues/1)

## What it gives you

Existing community standards cover dataset-level provenance (SPASE), generic
lineage relations (PROV), and packaging (RO-Crate), but none captures
*which specific upstream values contributed to one specific predicted value
via which specific transformations*. Operational fusion engines (Bayesian
Model Averaging, isotonic-regression calibration, conformal-prediction
wrappers) need that finer granularity for CCMC proving-ground evaluation,
SRAG console adoption, and audit-grade parametric-insurance trails.

This repo defines four record types:

1. **`HeliosDatasetRecord`** — one upstream dataset snapshot (SPASE-compatible).
2. **`HeliosModelOutputRecord`** — one value at one timestamp from one upstream model.
3. **`HeliosTransformationRecord`** — one transformation invocation (PROV `Activity`).
4. **`HeliosFusedOutputRecord`** — fused output with full feature-level lineage and a tamper-evident SHA-256 chain hash.

Plus a pydantic v2 reference implementation, eleven worked examples, a CLI
validator, SPASE / PROV-JSON / RO-Crate crosswalks, and an MkDocs site.

## Quickstart

```bash
pip install helios-provenance-spec
```

Validate an existing record:

```bash
helios-provenance-validate path/to/record.json
```

Use the pydantic models:

```python
from helios_provenance import parse_record, HeliosProvenanceValidator
import json

record = parse_record(json.load(open("schema/examples/11-fused-sep-all-clear.json")))
print(record.prediction_target, "=", record.value)
# -> sep_all_clear_revocation = 0.69

print("tamper-evident hash verifies:", record.verify_hash())
# -> True
```

## Worked examples

Eleven example records under [`schema/examples/`](schema/examples/) cumulatively
build to a fully-traced fused SEP all-clear revocation output for
2024-05-08T22:00Z. The fused output's three-step lineage traces back through
**conformal-prediction wrapping** → **BMA averaging** → **isotonic calibration**
to three upstream Scoreboard A inputs (UMASEP-10, SEPMOD, MagPy). See
[`docs/examples.md`](docs/examples.md) for the narrated walk-through.

## Repo layout

```
helios-provenance-spec/
├── schema/
│   ├── helios-provenance-v0.1.json     # JSON Schema 2020-12
│   ├── examples/                       # 11 validated example records
│   └── crosswalks/                     # SPASE / PROV-JSON / RO-Crate
├── src/helios_provenance/              # Python reference implementation
│   ├── models.py                       # pydantic v2 models
│   ├── hashing.py                      # RFC-8785 canonical hashing
│   ├── validator.py                    # jsonschema wrapper + CLI
│   └── crosswalk.py                    # SPASE XML / PROV-JSON emitters
├── tests/                              # 98 tests, 98% coverage
├── rfc/
│   └── RFC-0001-feature-lineage.md     # design document, open for comment
├── docs/                               # MkDocs (Material) site source
└── CHANGELOG.md
```

## Development

```bash
pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy
pytest
```

## Documentation

* [Docs site](https://577industries.github.io/helios-provenance-spec/) (build via `mkdocs serve`)
* [RFC-0001](rfc/RFC-0001-feature-lineage.md) — design, motivation, open questions
* [Schema reference](docs/schema.md) — field-by-field type definitions
* [Worked examples](docs/examples.md) — narrated walk-through of all eleven examples

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Substantive changes should be
discussed in an issue first. The eight open questions in
[RFC-0001 §6](rfc/RFC-0001-feature-lineage.md#6-open-questions-for-the-community)
are particularly hungry for community input.

## Citation

```bibtex
@software{helios_provenance_spec,
  author       = {Waweru, Thomas and 577 Industries Inc.},
  title        = {helios-provenance-spec: feature-level provenance for fused space-weather model outputs},
  year         = {2026},
  version      = {0.1.0},
  publisher    = {577 Industries Inc.},
  url          = {https://github.com/577Industries/helios-provenance-spec},
}
```
