# helios-provenance-spec

[![CI](https://github.com/577Industries/helios-provenance-spec/actions/workflows/ci.yml/badge.svg)](https://github.com/577Industries/helios-provenance-spec/actions/workflows/ci.yml) [![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI](https://img.shields.io/pypi/v/helios-provenance-spec.svg)](https://pypi.org/project/helios-provenance-spec/)

> JSON Schema (draft 2020-12) describing feature-level provenance for fused space-weather model outputs, plus a pydantic v2 reference implementation. Composes SPASE 2.7.1, W3C PROV-JSON, and RO-Crate 1.2 JSON-LD with a novel feature-level transformation chain. Issued as an open RFC for community comment.

## Status

This repository is part of the **HELIOS** program — a NASA SBIR Phase I effort by
577 Industries Inc. supporting subtopic SPWX.1.S26A (Advanced Data-Driven
Applications for Space Weather R2O2R). See proposal §1.4 (CONOPS) + §4.2 (innovation #2) of the proposal.

**Initial scaffolding committed 2026-05-17. Implementation in progress.**
Open issues to comment on the design or propose contributions.

## Quickstart

```bash
pip install helios-provenance-spec
```

```python
import helios_provenance
print(helios_provenance.__version__)
```

## Documentation

- **Master plan**: see [`helios-program`](https://github.com/577Industries/helios-program) (private; internal team)
- **Specification**: docs published at the project's docs site when available
- **Provenance**: every output traces to its upstream model and transformation chain
  via [`helios-provenance-spec`](https://github.com/577Industries/helios-provenance-spec)

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Substantive changes should be discussed in an issue first.

## Citation

```bibtex
@software{helios_helios_provenance_spec,
  author       = {Waweru, Thomas and 577 Industries Inc.},
  title        = { helios-provenance-spec: JSON Schema (draft 2020-12) describing feature-level provenance for fused space-weather model outputs, plus a pydantic v2 reference implementation },
  year         = {2026},
  publisher    = {577 Industries Inc.},
  url          = {https://github.com/577Industries/helios-provenance-spec},
}
```
