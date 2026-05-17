# helios-provenance-spec

> JSON Schema (draft 2020-12) describing **feature-level provenance** for
> fused space-weather model outputs, plus a pydantic v2 reference
> implementation. Composes SPASE 2.7.1, W3C PROV-JSON, and RO-Crate 1.2
> JSON-LD with a novel feature-level transformation chain.

This is the **HELIOS Provenance Spec v0.1**, issued as a [Request for
Comments](rfc/RFC-0001-feature-lineage.md). Community feedback expected before
stabilising to v1.0.

## Status

| Field | Value |
|---|---|
| Schema version | `0.1.0` |
| Package version | `0.1.0` |
| Stability | **Draft / RFC** — pin to `0.1.*` |
| License | Apache-2.0 |

## Why HELIOS Provenance?

Existing community standards cover dataset-level provenance (SPASE), generic
lineage relations (PROV), and packaging (RO-Crate), but none captures *which
specific upstream values contributed to one specific predicted value via
which specific transformations*. Operational fusion engines (Bayesian model
averaging, isotonic-regression calibration, conformal-prediction wrappers)
need that finer granularity for CCMC proving-ground evaluation, SRAG console
adoption, and the parametric-insurance audit trail that the HELIOS
commercialisation story leans on.

See the [RFC](rfc/RFC-0001-feature-lineage.md) for the full motivation,
design, open questions, and adoption ask.

## Quickstart

```bash
pip install helios-provenance-spec
```

```python
from helios_provenance import HeliosProvenanceValidator, parse_record
import json

# Validate any HELIOS record against the bundled JSON Schema.
v = HeliosProvenanceValidator()
record_dict = json.loads(open("schema/examples/11-fused-sep-all-clear.json").read())
assert v.is_valid(record_dict)

# Parse it into a typed pydantic model.
record = parse_record(record_dict)
print(record.prediction_target, "=", record.value)
# -> "sep_all_clear_revocation = 0.69"

# Verify the tamper-evident lineage hash recomputes.
print("hash ok:", record.verify_hash())
# -> hash ok: True
```

CLI:

```bash
helios-provenance-validate schema/examples/*.json
# 01-donki-flare-dataset.json: OK
# ...
# 11-fused-sep-all-clear.json: OK
```

## What's in this site

* [Schema reference](schema.md) — the four record types and their fields.
* [Worked examples](examples.md) — narrated walk-through of the eleven
  worked examples shipped in the repo.
* [API reference](api.md) — autodoc of the pydantic models, validator,
  hashing helpers, and crosswalks.
* [RFC-0001](rfc/RFC-0001-feature-lineage.md) — the design document for
  community comment.
* Crosswalks:
  * [SPASE 2.7.1](crosswalks/spase.md)
  * [W3C PROV-JSON](crosswalks/prov.md)
  * [RO-Crate 1.2](crosswalks/ro-crate.md)

## HELIOS programme context

This repository is **Artifact A** of the HELIOS programme — a NASA SBIR
Phase I effort by 577 Industries Inc. supporting subtopic SPWX.1.S26A
(Advanced Data-Driven Applications for Space Weather R2O2R). See proposal
§1.4 (CONOPS) and §4.2 (Innovation #2).
