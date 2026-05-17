# Crosswalk: HELIOS Provenance v0.1 ↔ RO-Crate 1.2

[RO-Crate 1.2](https://www.researchobject.org/ro-crate/1.2/) is the
community-standard packaging format for "research objects" — bundles of data
and metadata expressed as JSON-LD. A HELIOS provenance bundle (one or more
records that together explain a fused output) packages cleanly as an
RO-Crate.

## Why package HELIOS as RO-Crate?

* **Distribution.** Operators can hand a single zip containing the fused
  output, every upstream value that fed into it, every transformation, and
  the schema itself to a reviewer/regulator/customer without external
  references.
* **Citability.** RO-Crates have a stable
  `ro-crate-metadata.json` root, can be assigned a DOI via Zenodo, and are
  recognised by data-citation tooling.
* **Interoperability.** Tools like Galaxy, WorkflowHub, and TRE platforms
  already consume RO-Crates.

## Minimal crate layout

```text
helios-fused-2024-05-08T22:00Z.crate/
├── ro-crate-metadata.json          # the JSON-LD root
├── helios-provenance-v0.1.json     # the schema (vendored copy)
└── records/
    ├── 01-donki-flare-dataset.json
    ├── 02-donki-flare-output.json
    ├── ...
    └── 11-fused-sep-all-clear.json
```

## Mapping HELIOS records to RO-Crate entities

Each HELIOS record becomes a node in the RO-Crate `@graph`. The
`to_jsonld()` method on every pydantic model emits a JSON-LD fragment with a
HELIOS namespace under `@context`:

```json
{
  "@context": "https://577-industries.github.io/helios-provenance-spec/context/v0.1.jsonld",
  "@type": "helios:HeliosFusedOutputRecord",
  "@id": "helios:fused:sep-all-clear-revocation/2024-05-08T22:00Z",
  "record_type": "HeliosFusedOutputRecord",
  "prediction_target": "sep_all_clear_revocation",
  ...
}
```

To assemble these fragments into a full RO-Crate, the operator (or a future
HELIOS packaging helper) wraps them:

```json
{
  "@context": [
    "https://w3id.org/ro/crate/1.2/context",
    "https://577-industries.github.io/helios-provenance-spec/context/v0.1.jsonld"
  ],
  "@graph": [
    {
      "@id": "ro-crate-metadata.json",
      "@type": "CreativeWork",
      "conformsTo": { "@id": "https://w3id.org/ro/crate/1.2" },
      "about": { "@id": "./" }
    },
    {
      "@id": "./",
      "@type": "Dataset",
      "name": "HELIOS fused SEP all-clear revocation, 2024-05-08T22:00Z",
      "datePublished": "2024-05-08T22:14:00Z",
      "license": { "@id": "https://www.apache.org/licenses/LICENSE-2.0" },
      "hasPart": [
        { "@id": "records/01-donki-flare-dataset.json" },
        { "@id": "records/11-fused-sep-all-clear.json" }
      ]
    },
    { /* each HELIOS record .to_jsonld() output */ }
  ]
}
```

## Reference: HELIOS types as JSON-LD `@type`s

| HELIOS record type | JSON-LD `@type` | RO-Crate role |
|---|---|---|
| `HeliosDatasetRecord` | `helios:HeliosDatasetRecord` | `Dataset` content node |
| `HeliosModelOutputRecord` | `helios:HeliosModelOutputRecord` | data observation node |
| `HeliosTransformationRecord` | `helios:HeliosTransformationRecord` | `CreateAction` analogue |
| `HeliosFusedOutputRecord` | `helios:HeliosFusedOutputRecord` | derivative output node |
| `Agent` | `helios:Agent` | `SoftwareApplication` / `Person` / `Organization` |

The HELIOS `@context` (placeholder URL, to be promoted to a stable IRI at
v1.0) defines aliases for the HELIOS field names. Until that promotion,
adopters MAY substitute their own context. Tools should accept either.

## Open questions for v1.0

* Should HELIOS define its own JSON-LD context, or piggyback on schema.org +
  PROV-O?
* Should HELIOS records be a separate ro-crate-profile (e.g.
  `https://w3id.org/ro/crate/1.2/profiles/helios-provenance`)?

See `rfc/RFC-0001-feature-lineage.md` § "Open questions" for the community
discussion these belong to.

## See also

* `spase.md` — SPASE crosswalk for dataset-level metadata.
* `prov.md` — W3C PROV-JSON crosswalk for the lineage relations.
