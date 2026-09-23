#!/usr/bin/env python3
"""Regression tests for tools/statcan_ippi_filter.py. All rows are invented, shaped like the real
StatCan WDS CSV export (see the file's own docstring for where the real one comes from).
Run: python tools/test/test_statcan_ippi_filter.py"""
import csv
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import statcan_ippi_filter as sf  # noqa: E402

_DIRS = []


def newdir():
    d = Path(tempfile.mkdtemp())
    _DIRS.append(d)
    return d


# A small synthetic metadata file: two construction-relevant groups (P41, P63) each with one child
# and one grandchild, plus one unrelated group (P11, food) that must never be kept.
METADATA_ROWS = [
    ["Cube Title", "Product Id", "CANSIM Id", "URL", "Cube Notes", "Archive Status", "Frequency",
     "Start Reference Period", "End Reference Period", "Total number of dimensions"],
    ["Test table", "99999999", "", "https://example.invalid", "", "CURRENT", "Monthly", "2015-01", "2026-08", "2"],
    [],
    ["Dimension ID", "Dimension name", "Dimension Notes", "Dimension Definitions"],
    ["1", "Geography", "", ""],
    ["2", "North American Product Classification System (NAPCS)", "", ""],
    [],
    ["Dimension ID", "Member Name", "Classification Code", "Member ID", "Parent Member ID",
     "Terminated", "Member Notes", "Member Definitions"],
    ["1", "Canada", "[11124]", "1", "", "", "", ""],
    ["2", "Total, Industrial product price index (IPPI)", "", "1", "", "", "", ""],
    ["2", "Food products", "[P11]", "2", "1", "", "", ""],  # unrelated group -- must be dropped
    ["2", "Meat products", "[172]", "3", "2", "", "", ""],
    ["2", "Lumber and other wood products", "[P41]", "10", "1", "", "", ""],
    ["2", "Lumber and other sawmill products", "[241]", "11", "10", "", "", ""],
    ["2", "Softwood lumber", "[24112]", "12", "11", "", "", ""],  # grandchild of P41
    ["2", "Fabricated metal products and construction materials", "[P63]", "20", "1", "", "", ""],
    ["2", "Metal building and construction materials", "[466]", "21", "20", "", "", ""],
]


def write_metadata(d: Path) -> Path:
    p = d / "meta.csv"
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(METADATA_ROWS)
    return p


DATA_COLUMNS = ["REF_DATE", "GEO", "DGUID", "North American Product Classification System (NAPCS)",
                 "UOM", "UOM_ID", "SCALAR_FACTOR", "SCALAR_ID", "VECTOR", "COORDINATE", "VALUE",
                 "STATUS", "SYMBOL", "TERMINATED", "DECIMALS"]


def data_row(ref_date, product, value, vector):
    return {"REF_DATE": ref_date, "GEO": "Canada", "DGUID": "", "UOM": "Index, 202001=100",
            "UOM_ID": "403", "SCALAR_FACTOR": "units", "SCALAR_ID": "0", "VECTOR": vector,
            "COORDINATE": "1.1", "VALUE": value, "STATUS": "", "SYMBOL": "", "TERMINATED": "",
            "DECIMALS": "1", "North American Product Classification System (NAPCS)": product}


def write_data(d: Path, rows) -> Path:
    p = d / "data.csv"
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DATA_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return p


def main():
    bad = []
    d = newdir()
    meta = write_metadata(d)
    rows = [
        data_row("2015-01", "Softwood lumber [24112]", "100.0", "vSOFTWOOD"),   # P41 grandchild: keep
        data_row("2015-01", "Lumber and other wood products [P41]", "100.0", "vP41TOTAL"),  # P41 total: keep
        data_row("2015-01", "Metal building and construction materials [466]", "105.0", "vMETAL"),  # P63 child: keep
        data_row("2015-01", "Meat products [172]", "110.0", "vMEAT"),  # unrelated group: drop
        data_row("2010-01", "Softwood lumber [24112]", "90.0", "vSOFTWOOD"),  # before min-date: drop
        data_row("2015-02", "Softwood lumber [24112]", "101.5", "vSOFTWOOD"),
    ]
    data = write_data(d, rows)
    out = d / "out.csv"

    code_to_group = sf.build_code_to_group(meta)
    if code_to_group.get("[24112]") != ("P41", "Lumber and other wood products"):
        bad.append(("grandchild resolves to its top group", code_to_group.get("[24112]")))
    if "[172]" in code_to_group:
        bad.append(("unrelated group must not be kept", code_to_group.get("[172]")))

    assert sf.main([str(data), str(meta), str(out)]) == 0
    with out.open(encoding="utf-8-sig", newline="") as f:
        kept = {r["vector"]: r for r in csv.DictReader(f) if r["ref_date"] == "2015-01"}
    if set(kept) != {"vSOFTWOOD", "vP41TOTAL", "vMETAL"}:
        bad.append(("row selection", sorted(kept)))
    if kept.get("vSOFTWOOD", {}).get("napcs_group") != "P41":
        bad.append(("group assigned", kept.get("vSOFTWOOD")))
    with out.open(encoding="utf-8-sig", newline="") as f:
        all_rows = list(csv.DictReader(f))
    if any(r["ref_date"] == "2010-01" for r in all_rows):
        bad.append(("min-date filter did not drop an old row", None))

    # --min-date is honoured when passed explicitly
    out2 = d / "out2.csv"
    assert sf.main([str(data), str(meta), str(out2), "--min-date", "2010-01"]) == 0
    with out2.open(encoding="utf-8-sig", newline="") as f:
        rows2 = list(csv.DictReader(f))
    if not any(r["ref_date"] == "2010-01" for r in rows2):
        bad.append(("--min-date override not honoured", None))

    for dd in _DIRS:
        shutil.rmtree(dd, ignore_errors=True)
    if bad:
        for x in bad:
            print("FAIL", x)
        return 1
    print("statcan_ippi_filter tests pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
