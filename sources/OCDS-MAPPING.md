# Mapping to the Open Contracting Data Standard (OCDS) / OC4IDS

Why: the user asked us to look at incorporating this open standard. OCDS (and its infrastructure
extension, OC4IDS) is the closest existing standard to what this kit's award data and comparables
already are — line items with a classification, a quantity, a unit, and a value, tied to a contract.
Publishing (or just being able to export) in this shape means the kit's data can be combined with any
other OCDS-publishing procurement system without a bespoke integration, and gives the kit's own
authors a well-tested vocabulary to check the register's data model against.

This is a **mapping and an exporter**, not a decision to adopt OCDS as this kit's native format.
`sources/register.csv`, `data/canadabuys-awards-ncr-construction.csv` and `data/comparables.csv`
stay as they are; `tools/ocds_export.py` produces an OCDS-shaped view of one award row on request.
Field names and structure below are read directly from the OCDS 1.1.5 release schema
(`https://standard.open-contracting.org/schema/1__1__5/release-schema.json`, fetched 2026-09-23), not
guessed — every OCDS field named here exists in that schema exactly as named.

## What OCDS's `Item` object actually looks like
`Item` (used inside `tender.items`, `award.items` and `contract.items`) has: `id` (required, unique
within the array), `description`, `classification` (one `{scheme, id, description}` object — the
*primary* classification), `additionalClassifications` (an array of the same shape, for every other
classification that applies), `quantity` (a number), and `unit` (`{scheme, id, name, value: {amount,
currency}, uri}` — the unit of measure and its unit price). There is no separate top-level "unit
price" field outside `unit.value`.

## Field-by-field mapping: an award-data row -> an OCDS `Award`
| This kit's field (`data/canadabuys-awards-ncr-construction.csv`) | OCDS field | Notes |
|---|---|---|
| `contract_number` | `award.id`, and the release's `ocid` (prefixed — see caveat below) | OCDS `award.id` must be unique within one `ocid`'s releases; `contract_number` already is |
| `award_date` | `award.date` | ISO date; OCDS wants `date-time` — midnight UTC is used if no time is known |
| `award_status` (`Active` etc.) | `award.status` | Mapped through the OCDS `awardStatus` codelist (closed list: `pending`, `active`, `cancelled`, `unsuccessful`) — `Active` -> `active`; anything else this kit hasn't seen yet is left as `null` with the raw value kept in a non-standard `x_source_status` field rather than guessed |
| `total_contract_value`, `currency` | `award.value.amount`, `award.value.currency` | `contract_amount_raw` is never used here, matching `webapp/README.md`'s own rule |
| `supplier_legal_name` | `award.suppliers[].name` | OCDS wants a `parties[]` entry with an `id` and `roles: ["supplier"]` for full compliance; the exporter emits a minimal `name`-only reference and notes the gap rather than inventing an id |
| `title`, `unspsc`, `unspsc_description` | `award.items[0].description`, `.classification.scheme = "UNSPSC"`, `.classification.id`, `.classification.description` | UNSPSC is one of the standard's own recommended item-classification schemes |
| `gsin`, `gsin_description` | `award.items[0].additionalClassifications[]`, `scheme = "GSIN"` | GSIN (Government of Canada's own goods/services identification number) is not one of OCDS's pre-listed schemes, but `classification.scheme` is an **open** codelist — a jurisdiction-specific scheme name is exactly what that's for |
| `competitive`, `selection_criteria`, `procurement_method` | not a native OCDS `Award` field | Belongs in `tender.procurementMethod` / `tender.awardCriteria` on the *tender* section instead, which this exporter does not build (see "What's not built" below) |
| `quality_flags` | not an OCDS field | Kept as a non-standard `x_fairpricekit_quality_flags` field (OCDS's own convention for publisher extensions is an `x_` prefix) so a flagged row is never silently exported looking clean |

## Caveat: this kit does not mint real OCIDs
A real OCID (Open Contracting ID) has a registered publisher prefix
(`ocds-<prefix>-<identifier>`) assigned by the Open Contracting Partnership's registry — this kit has
not registered one, and doing so is a real-world step outside this repository's scope. The exporter
builds a clearly-marked placeholder (`ocds-fairpricekit-<contract_number>`) so the *shape* of the
output is valid OCDS for testing or combining with real OCDS data locally, but it must never be
published or merged as if it were an officially-issued OCID. Say so if this output ever leaves the
kit.

## What's not built
- **`tender` and `contract` sections.** The award-notice data this kit has is award-stage only; it
  doesn't carry the tender's own `procurementMethod`/`awardCriteria`/`tenderPeriod` fields or a
  distinct post-award contract record (`contract.dateSigned`, `contract.period`, amendments). Adding
  these would need the tender notice itself (see `data/canadabuys-tender-attachments-index.csv` —
  links only, copyright protected, not something this kit can read in bulk) or the contract-history
  per-amendment data surveyed in `data/SOURCES-candidates.md` but not yet added.
- **`parties[]`.** OCDS 1.1 wants organizations declared once in a top-level `parties` array and
  cross-referenced by `id` everywhere else (the embedded-organization approach is deprecated). The
  exporter's minimal `suppliers[].name` is valid but not full OC4IDS-quality data; building real
  `parties[]` entries would need a stable organization identifier this kit's source data doesn't
  carry (a business number or similar), not just a name.
- **OC4IDS-specific fields** (the infrastructure extension: `project`, sector, funding sources,
  environmental/social safeguards) are not attempted at all — this kit's data is procurement-price
  evidence, not infrastructure-project planning data, and OC4IDS's added fields mostly describe the
  latter.
- **Publishing a real `release-package`.** The exporter emits one release fragment for one award on
  request; it does not attempt the full package/publisher metadata OCDS requires for a real feed.

## Using it
```
python tools/ocds_export.py CONTRACT_NUMBER
```
Looks up the row in `data/canadabuys-awards-ncr-construction.csv` and prints the OCDS-shaped JSON
fragment (an `award` object plus the placeholder `ocid`) to stdout. See `tools/ocds_export.py`'s own
docstring and `tools/test/test_ocds_export.py` for the exact shape and its test coverage.
