#!/usr/bin/env python3
"""Regression test for tools/spec_headers.py (header-style specs). All text is invented.
Run: python tools/test/test_spec_headers.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from spec_headers import spec_sections_from_headers  # noqa: E402

DOC = """<!-- page 1 -->
CONSTRUCTION SPECIFICATIONS FOR EXAMPLE WALL
<!-- page 2 -->
Example Wall     TABLE OF CONTENTS         Section 00 01 10
Rehab (Phase 2)                                   Page 1 of 1
Project #: 000-00                                March, 2025
00 01 10   Table of contents
<!-- page 3 -->
Example Wall     PAY ITEM DESCRIPTION                   Section 01 11 00
Rehab (Phase 2)                                              Page 1 of 2
Project #: 000-00                                           March, 2025
Item 1 is paid by lump sum. See Section 05 12 00 for steel.
<!-- page 4 -->
Example Wall     PAY ITEM DESCRIPTION                   Section 01 11 00
Rehab (Phase 2)                                              Page 2 of 2
Project #: 000-00                                           March, 2025
Item 2 is paid by unit price.
<!-- page 5 -->
Example Wall       AVAILABLE PROJECT                          Section 00 31 00
Rehab (Phase 2)         INFORMATION                                  Page 1 of 3
Project #: 000-00                                            March, 2025
1 GENERAL
<!-- page 6 -->
Example Wall     EXCAVATION PROTECTION        Section A9030
Rehab (Phase 2)                                   Page 1 of 1
Project #: 000-00                               March 2025
1 GENERAL
<!-- page 7 -->
Example Wall     SPECIAL PROCEDURES FOR CONTAMINATED   Section 01 35 13.43
Rehab (Phase 2)  SITES                                       Page 1 of 2
Project #: 000-00                                          March, 2025
1 GENERAL
"""


def main():
    secs = spec_sections_from_headers(DOC)
    got = [(no, title) for no, title, _s, _e in secs]
    want_numbers = [None, "00 01 10", "01 11 00", "00 31 00", "A9030", "01 35 13.43"]
    bad = []
    if [n for n, _ in got] != want_numbers:
        bad.append(("section numbers", [n for n, _ in got]))
    titles = dict(got)
    if titles.get("00 31 00") != "AVAILABLE PROJECT INFORMATION":
        bad.append(("wrapped two-line title", titles.get("00 31 00")))
    if titles.get("01 35 13.43") != "SPECIAL PROCEDURES FOR CONTAMINATED SITES":
        bad.append(("wrapped title with decimals", titles.get("01 35 13.43")))
    if titles.get("01 11 00") != "PAY ITEM DESCRIPTION":
        bad.append(("title", titles.get("01 11 00")))
    # pages 3 and 4 are one section; the mid-page 'see Section 05 12 00' must not start a new section
    pay = [s for s in secs if s[0] == "01 11 00"]
    if len(pay) != 1 or "<!-- page 4 -->" not in DOC[pay[0][2]:pay[0][3]]:
        bad.append(("pages 3-4 grouped in one section", len(pay)))
    # sections tile the document with no gaps or overlaps
    spans = [(s[2], s[3]) for s in secs]
    if spans[0][0] != 0 or spans[-1][1] != len(DOC) or any(a[1] != b[0] for a, b in zip(spans, spans[1:])):
        bad.append(("sections do not tile the document", spans))
    # no header at all -> one 'front matter' style section, no crash
    if spec_sections_from_headers("just text\nno markers") != [(None, "", 0, len("just text\nno markers"))]:
        bad.append(("no page markers", None))
    if bad:
        for b in bad:
            print("FAIL", b)
        return 1
    print("spec_headers tests pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
