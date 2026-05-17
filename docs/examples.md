# Worked examples

The repository ships **eleven** worked example records under
`schema/examples/`. They are designed to cumulatively build to the centrepiece
example: a fully-traced fused SEP all-clear revocation prediction for
2024-05-08T22:00Z (the lead-up to the May 2024 Gannon superstorm).

Every example validates against the bundled JSON Schema; the test suite
asserts this (`tests/test_models.py::test_example_validates_against_schema`).

## The six upstream sources

These six records show how one feed becomes one or more HELIOS records.

| # | File | Record type | Source |
|---|---|---|---|
| 1 | `01-donki-flare-dataset.json` | `HeliosDatasetRecord` | NASA DONKI FLR endpoint for 2024-05-08. |
| 2 | `02-donki-flare-output.json` | `HeliosModelOutputRecord` | One X1.0 flare from the DONKI page above. |
| 3 | `03-scoreboard-a-output.json` | `HeliosModelOutputRecord` | One CCMC SEP Scoreboard A onset probability from UMASEP-10 at 22:00Z. |
| 4 | `04-swpc-kp-output.json` | `HeliosModelOutputRecord` | One NOAA SWPC Kp sample at 21:00Z on 2024-05-10 (Kp=9.0, G5). |
| 5 | `05-cddis-gim-tec-output.json` | `HeliosModelOutputRecord` | One CDDIS GIM TEC gridpoint (40°N, 90°W, 2024-05-10T20:00Z). |
| 6 | `06-goes-proton-output.json` | `HeliosModelOutputRecord` | One GOES-18 EPEAD ≥10 MeV proton flux sample at 22:00Z. |
| 7 | `07-dscovr-solarwind-output.json` | `HeliosModelOutputRecord` | One DSCOVR PlasMag solar-wind speed sample at L1 at 17:30Z. |

These illustrate the breadth of upstream sources HELIOS ingests: an event
catalogue (DONKI), three Scoreboards (A is shown; B and C follow the same
pattern), an index (Kp), a spatially-resolved field (GIM TEC), an in-situ
particle flux (GOES protons), and an in-situ field measurement (DSCOVR solar
wind). All carry full provenance back to a `HeliosDatasetRecord`.

## The three transformations

These three records define the transformations referenced by the fused
output's lineage.

| # | File | Type | What it does |
|---|---|---|---|
| 8 | `08-transformation-isotonic.json` | `calibration` | Isotonic regression on three Scoreboard A onset probabilities. Fitted on a rolling 90-day verification window. |
| 9 | `09-transformation-bma.json` | `bma` | Bayesian Model Averaging over the three calibrated probabilities. Weights {UMASEP-10:0.46, SEPMOD:0.31, MagPy:0.23}. |
| 10 | `10-transformation-conformal.json` | `conformal` | Split conformal wrapping with α=0.1, calibration set size 412, stratified by Kp severity bin. |

Note how each `HeliosTransformationRecord` carries:

* a `code_ref` that pins the implementing function to a specific git commit
  (`git+https://github.com/577-Industries/helios-fusion-engine@a1b2c3d4#...`),
* a `parameters` dict with the actual hyperparameter values (BMA weights,
  conformal α, calibration window size),
* `input_refs` and `output_refs` that connect the activity to specific
  model-output records.

This is what "feature-level provenance" means concretely: not just "we ran a
BMA" but "we ran *this* BMA over *these* inputs at *these* weights, and
produced *that* output, using *this exact code*."

## The centrepiece: a fully-traced fused output

`11-fused-sep-all-clear.json` is the `HeliosFusedOutputRecord` that ties
everything together:

```json
{
  "id": "helios:fused:sep-all-clear-revocation/2024-05-08T22:00Z",
  "prediction_target": "sep_all_clear_revocation",
  "value": 0.69,
  "value_units": "1",
  "conformal_interval": {
    "lower": 0.49,
    "upper": 0.86,
    "alpha": 0.1,
    "method": "conformal-split",
    "calibration_set_size": 412
  },
  "lineage": [
    {"transformation_ref": "helios:transform:calibration/isotonic/...", "...": "..."},
    {"transformation_ref": "helios:transform:bma/...", "...": "..."},
    {"transformation_ref": "helios:transform:conformal/...", "...": "..."}
  ],
  "provenance_chain_hash": "c7935d3f1df8d1d8eff627b16f8eb383be4cc31fe217bbd66a06e271197b7877"
}
```

The three-step lineage means an operator drilling into this prediction can
answer:

* **Which upstream models contributed?**
  UMASEP-10, SEPMOD, and MagPy via Scoreboard A. Each is identified by ID
  in `lineage[0].input_refs`.
* **At what weights?** {UMASEP-10:0.46, SEPMOD:0.31, MagPy:0.23} —
  recorded in transformation #9's `parameters.weights`.
* **With what calibration history?** Isotonic regression fit on the rolling
  90-day verification window 2024-02-08 .. 2024-05-08 — recorded in
  transformation #8's `parameters`.
* **With what uncertainty?** 90% conformal interval [0.49, 0.86] from a
  split-conformal procedure with calibration set size 412, stratified by Kp
  severity bin — recorded in `conformal_interval` and transformation #10.
* **Has it been tampered with?**
  `HeliosFusedOutputRecord.verify_hash()` recomputes the SHA-256 over the
  canonicalised lineage and compares. Any mutation of any field in any step
  flips the hash.

## Reproducing the chain hash

```python
from helios_provenance import parse_record
import json

rec = parse_record(json.loads(open("schema/examples/11-fused-sep-all-clear.json").read()))
assert rec.verify_hash() is True
assert rec.provenance_chain_hash == "c7935d3f1df8d1d8eff627b16f8eb383be4cc31fe217bbd66a06e271197b7877"
```

Tamper detection:

```python
tampered = rec.model_copy(deep=True)
tampered.lineage[0].notes = "I have been tampered with"
assert tampered.verify_hash() is False
```

## See also

* [RFC-0001](rfc/RFC-0001-feature-lineage.md) for the design rationale and
  open questions.
* [Schema reference](schema.md) for the field-by-field type definitions.
