#!/usr/bin/env python3
"""Filter the full Statistics Canada Industrial Product Price Index table (18-10-0266-01) down to
the construction-relevant product groups.

Usage:
  python tools/statcan_ippi_filter.py FULL.csv METADATA.csv OUT.csv [--min-date 2015-01]

FULL and METADATA are the two files inside the table's own CSV download zip:
  https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/18100266/en
  (register id STATCAN-IPPI; the WDS API takes the 8-digit product id, i.e. the table id with the
  trailing "-01" version suffix dropped: 18-10-0266-01 -> 18100266)
That endpoint returns a "SUCCESS" JSON object whose "object" field is the download URL for a zip
containing 18100266.csv (the data) and 18100266_MetaData.csv (dimensions and codes) -- both needed
here, since the data file only carries each product's name and NAPCS code, not which of the five
construction-relevant top-level groups it belongs to.

Keeps every row (all levels of aggregation, not just leaves) whose NAPCS classification code is P41
(Lumber and other wood products), P61 (Primary ferrous metal products), P62 (Primary non-ferrous
metal products), P63 (Fabricated metal products and construction materials), P81 (Cement, glass and
other non-metallic mineral products), or a descendant of one of those five groups in the metadata's
own parent-child hierarchy. This is materials-cost movement, not a building or project price -- see
data/statcan-ippi-construction.README.md for how to use it (inflation-adjust a prior comparable,
never as a comparable itself).

--min-date (default 2015-01) drops rows before that month: the full table runs back to 1956, far more
history than any comparable this kit will realistically adjust needs, and keeping it all would make
the output file unwieldy for no benefit. Raise or lower it if the comparables you're adjusting are
older or newer than this default covers.
"""
import csv
import sys
from pathlib import Path

csv.field_size_limit(10**9)

TOP_GROUPS = {
    "P41": "Lumber and other wood products",
    "P61": "Primary ferrous metal products",
    "P62": "Primary non-ferrous metal products",
    "P63": "Fabricated metal products and construction materials",
    "P81": "Cement, glass, and other non-metallic mineral products",
}

OUT_COLUMNS = ["ref_date", "napcs_group", "napcs_group_name", "product", "uom", "value",
               "vector", "coordinate", "status", "terminated"]


def build_code_to_group(metadata_path: Path) -> dict:
    """Read the metadata's member table (Dimension 2 = NAPCS) and, for every member, walk its
    Parent Member ID chain to see whether it descends from one of TOP_GROUPS. Returns
    {classification code (with brackets, as it appears in the data file's product column): (group, name)}."""
    members = {}  # member_id -> (name, code, parent_id)
    with metadata_path.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        in_members = False
        for row in rd:
            if not row:
                continue
            if row[0] == "Dimension ID" and len(row) > 1 and row[1] == "Member Name":
                in_members = True  # the member table's own header line -- everything after is data
                continue
            if not in_members or len(row) < 5 or row[0] != "2":  # dimension 2 = NAPCS; dimension 1 = geography
                continue
            name, code, member_id, parent_id = row[1], row[2], row[3], row[4]
            members[member_id] = (name, code, parent_id)

    top_ids = {mid: code.strip("[]") for mid, (_, code, _) in members.items() if code.strip("[]") in TOP_GROUPS}

    def reaches_top(member_id, seen=frozenset()):
        if member_id in seen or member_id not in members:
            return None
        if member_id in top_ids:
            return top_ids[member_id]
        _, _, parent_id = members[member_id]
        if not parent_id:
            return None
        return reaches_top(parent_id, seen | {member_id})

    code_to_group = {}
    for member_id, (_, code, _) in members.items():
        group = reaches_top(member_id)
        if group:
            code_to_group[code] = (group, TOP_GROUPS[group])
    return code_to_group


def main(argv):
    min_date = "2015-01"
    args = list(argv)
    if "--min-date" in args:
        i = args.index("--min-date")
        min_date = args[i + 1]
        args = args[:i] + args[i + 2:]
    if len(args) != 3:
        print(__doc__)
        return 2
    full_csv, metadata_csv, out_csv = (Path(a) for a in args)

    code_to_group = build_code_to_group(metadata_csv)
    print(f"matched {len(code_to_group)} NAPCS codes under the {len(TOP_GROUPS)} construction-relevant groups",
          file=sys.stderr)

    kept, total = [], 0
    with full_csv.open(encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            total += 1
            if r["REF_DATE"] < min_date:
                continue
            napcs = r["North American Product Classification System (NAPCS)"]
            if "[" not in napcs:
                continue
            code = "[" + napcs.rsplit("[", 1)[1]
            if code not in code_to_group:
                continue
            group, group_name = code_to_group[code]
            kept.append({
                "ref_date": r["REF_DATE"],
                "napcs_group": group,
                "napcs_group_name": group_name,
                "product": napcs,
                "uom": r["UOM"],
                "value": r["VALUE"],
                "vector": r["VECTOR"],
                "coordinate": r["COORDINATE"],
                "status": r["STATUS"],
                "terminated": r["TERMINATED"],
            })

    kept.sort(key=lambda r: (r["napcs_group"], r["product"], r["ref_date"]))
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        w.writeheader()
        w.writerows(kept)
    print(f"source rows: {total}; kept: {len(kept)} (>= {min_date}, {len(TOP_GROUPS)} construction-relevant "
          f"NAPCS groups); distinct products: {len(set(r['product'] for r in kept))}; wrote {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
