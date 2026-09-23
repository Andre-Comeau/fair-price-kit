#!/usr/bin/env python3
"""Export one row of data/canadabuys-awards-ncr-construction.csv as an OCDS-shaped release fragment.

Usage:
  python tools/ocds_export.py CONTRACT_NUMBER [--awards-csv PATH]

Prints JSON to stdout: {"ocid": ..., "award": {...}}. Field names and structure follow the OCDS
1.1.5 release schema exactly (see sources/OCDS-MAPPING.md for the field-by-field mapping and, just
as importantly, what this does NOT attempt -- there is no tender or contract section, and no real
parties[] array, because the source data doesn't carry what those need).

The "ocid" this produces is a placeholder (`ocds-fairpricekit-<contract_number>`), not a real
Open Contracting ID -- this kit has not registered an OCID publisher prefix. It makes the output
valid OCDS *shape* for local testing or combining with real OCDS data; never publish or merge it as
if it were an officially-issued OCID.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AWARDS_CSV = ROOT / "data" / "canadabuys-awards-ncr-construction.csv"

# OCDS awardStatus is a CLOSED codelist (pending/active/cancelled/unsuccessful/null) -- verified
# against https://standard.open-contracting.org/schema/1__1__5/release-schema.json, 2026-09-23.
# This kit's award_status column uses different words (CanadaBuys' own vocabulary), so only the
# mappings below are asserted; anything else is left null with the raw value preserved in
# x_source_status rather than guessed.
AWARD_STATUS_MAP = {
    "Active": "active",
    "Cancelled": "cancelled",
    "Cancelled Award": "cancelled",
}


def load_row(contract_number: str, awards_csv: Path) -> dict:
    with awards_csv.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("contract_number") == contract_number:
                return row
    raise KeyError(f"no row with contract_number={contract_number!r} in {awards_csv}")


def to_ocds(row: dict) -> dict:
    ocid = f"ocds-fairpricekit-{row['contract_number']}"  # placeholder, see module docstring

    classification = None
    if row.get("unspsc"):
        first_code = row["unspsc"].split(";")[0].strip()
        first_desc = row.get("unspsc_description", "").split(";")[0].strip()
        classification = {"scheme": "UNSPSC", "id": first_code, "description": first_desc or None}

    additional = []
    if row.get("gsin"):
        additional.append({"scheme": "GSIN", "id": row["gsin"].split(";")[0].strip(),
                            "description": (row.get("gsin_description", "").split(";")[0].strip() or None)})

    item = {"id": "1", "description": row.get("title") or None}
    if classification:
        item["classification"] = classification
    if additional:
        item["additionalClassifications"] = additional

    value = None
    if row.get("total_contract_value"):
        try:
            value = {"amount": float(row["total_contract_value"]), "currency": row.get("currency") or None}
        except ValueError:
            value = None

    award = {
        "id": row.get("contract_number"),
        "title": row.get("title") or None,
        "date": row.get("award_date") or None,
        "status": AWARD_STATUS_MAP.get(row.get("award_status"), None),
        "value": value,
        "suppliers": [{"name": row["supplier_legal_name"]}] if row.get("supplier_legal_name") else [],
        "items": [item],
        # non-standard (x_ prefix is OCDS's own convention for publisher extensions, see
        # sources/OCDS-MAPPING.md): fields real to this kit's data but with no OCDS home.
        "x_source_status": row.get("award_status") or None,
        "x_fairpricekit_quality_flags": row.get("quality_flags") or None,
    }
    return {"ocid": ocid, "award": award}


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    awards_csv = AWARDS_CSV
    if "--awards-csv" in argv:
        awards_csv = Path(argv[argv.index("--awards-csv") + 1])
    try:
        row = load_row(args[0], awards_csv)
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(to_ocds(row), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
