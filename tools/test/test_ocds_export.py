#!/usr/bin/env python3
"""Regression tests for tools/ocds_export.py. Row shape invented but based on the real
data/canadabuys-awards-ncr-construction.csv columns. Run: python tools/test/test_ocds_export.py"""
import csv
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ocds_export as oe  # noqa: E402

_DIRS = []

COLUMNS = ["contract_number", "solicitation_number", "reference_number", "title", "award_date",
           "publication_date", "amendment_date", "contract_start", "contract_end", "amendment_number",
           "amendment_type", "total_contract_value", "contract_amount_raw", "currency", "award_status",
           "instrument_type", "notice_type", "procurement_method", "selection_criteria",
           "limited_tendering_reason", "trade_agreements", "regions_of_delivery", "unspsc",
           "unspsc_description", "gsin", "gsin_description", "supplier_legal_name", "supplier_city",
           "supplier_province", "contracting_entity", "end_user_entity", "amendment_count",
           "competitive", "is_ncc", "supplier_key", "quality_flags", "source_file"]


def newdir():
    d = Path(tempfile.mkdtemp())
    _DIRS.append(d)
    return d


def row(**kw):
    base = {c: "" for c in COLUMNS}
    base.update({
        "contract_number": "TEST-001", "title": "Roof repair", "award_date": "2025-06-01",
        "total_contract_value": "150000.00", "currency": "CAD", "award_status": "Active",
        "unspsc": "72101500", "unspsc_description": "Building maintenance and repair services",
        "gsin": "", "gsin_description": "", "supplier_legal_name": "Test Roofing Inc.",
        "quality_flags": "",
    })
    base.update(kw)
    return base


def write_csv(d: Path, rows) -> Path:
    p = d / "awards.csv"
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return p


def main():
    bad = []
    d = newdir()
    csv_path = write_csv(d, [row(), row(contract_number="TEST-FLAGGED", quality_flags="total_zero",
                                    award_status="Cancelled", total_contract_value="0.00")])

    r = oe.load_row("TEST-001", csv_path)
    doc = oe.to_ocds(r)
    if doc["ocid"] != "ocds-fairpricekit-TEST-001":
        bad.append(("placeholder ocid", doc["ocid"]))
    award = doc["award"]
    if award["id"] != "TEST-001" or award["date"] != "2025-06-01":
        bad.append(("basic id/date mapping", award))
    if award["status"] != "active":
        bad.append(("award status mapped through the closed codelist", award["status"]))
    if award["value"] != {"amount": 150000.0, "currency": "CAD"}:
        bad.append(("value mapping", award["value"]))
    if award["suppliers"] != [{"name": "Test Roofing Inc."}]:
        bad.append(("supplier mapping", award["suppliers"]))
    item = award["items"][0]
    if item["classification"] != {"scheme": "UNSPSC", "id": "72101500",
                                   "description": "Building maintenance and repair services"}:
        bad.append(("classification mapping", item.get("classification")))
    if "additionalClassifications" in item:
        bad.append(("no GSIN in source -> no additionalClassifications", item))

    flagged = oe.to_ocds(oe.load_row("TEST-FLAGGED", csv_path))
    if flagged["award"]["x_fairpricekit_quality_flags"] != "total_zero":
        bad.append(("quality flag preserved in x_ field, never silently dropped", flagged["award"]))
    if flagged["award"]["status"] != "cancelled":
        bad.append(("cancelled status mapped", flagged["award"]["status"]))

    try:
        oe.load_row("NO-SUCH-CONTRACT", csv_path)
        bad.append(("expected KeyError for an unknown contract number", None))
    except KeyError:
        pass

    for dd in _DIRS:
        shutil.rmtree(dd, ignore_errors=True)
    if bad:
        for x in bad:
            print("FAIL", x)
        return 1
    print("ocds_export tests pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
