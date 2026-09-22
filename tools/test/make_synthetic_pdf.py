#!/usr/bin/env python3
"""Write a small SYNTHETIC text-layer PDF (all data invented) for pipeline tests.

Usage: python tools/test/make_synthetic_pdf.py OUT.pdf [--marked] [--blank-page] [--header-style]
--marked        adds a "Protected B" line (to test the classification stop)
--blank-page    adds a page with no text (to test low-text detection)
--header-style  sections identified only by a running page header ("Section nn nn nn"), no SECTION heading lines
"""
import sys

PAGES = [
    ["PROJECT MANUAL - SYNTHETIC EXAMPLE", "Owner: Example Owner Corp.", "Project at 123 Example Street, Ottawa K1A 0B1",
     "Contact: Mr. Smith, (613) 555-0123, jane.doe@example.com", "Prepared by: A. Person"],
    ["SECTION 03 30 00 - CAST-IN-PLACE CONCRETE", "PART 1 - GENERAL", "1.1 Summary: concrete work per drawings.",
     "See Section 05 12 00 and Drawing A-101 for embedded steel.", "Refer to CO-007 for the revised slab thickness.",
     "PART 2 - PRODUCTS", "2.1 Concrete: 32 MPa at 28 days.", "PART 3 - EXECUTION", "3.1 Place concrete in one pour."],
    ["SECTION 05 12 00 - STRUCTURAL STEEL FRAMING", "PART 1 - GENERAL", "1.1 Summary: supply and erect structural steel.",
     "Unit price allowance: 4,250.00 per tonne (synthetic).", "PART 2 - PRODUCTS", "2.1 Steel: CSA G40.21 350W."],
]


# Header-style spec (invented): every page starts with a 3-line running header; no "SECTION nn nn nn" heading lines.
PAGES_HEADER_STYLE = [
    ["CONSTRUCTION SPECIFICATIONS FOR EXAMPLE WALL", "Prepared by: A. Person"],
    ["Example Wall     TABLE OF CONTENTS          Section 00 01 10", "Rehab (Phase 2)                    Page 1 of 1",
     "Project #: 000-00                 March, 2025", "00 01 10  Table of contents"],
    ["Example Wall     CAST-IN-PLACE CONCRETE     Section 03 30 00", "Rehab (Phase 2)                    Page 1 of 2",
     "Project #: 000-00                 March, 2025", "1.1 Summary: concrete work.", "See Section 05 12 00 for steel.",
     "Refer to CO-007 for the revised slab."],
    ["Example Wall     CAST-IN-PLACE CONCRETE     Section 03 30 00", "Rehab (Phase 2)                    Page 2 of 2",
     "Project #: 000-00                 March, 2025", "2.1 Concrete: 32 MPa at 28 days."],
    ["Example Wall     STRUCTURAL STEEL FRAMING   Section 05 12 00", "Rehab (Phase 2)                    Page 1 of 1",
     "Project #: 000-00                 March, 2025", "1.1 Summary: supply and erect steel."],
]


def esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build(pages):
    objs = []  # index i -> bytes for object i+1
    n = len(pages)
    page_ids = [4 + 2 * i for i in range(n)]
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, lines in enumerate(pages):
        stream = "BT /F1 11 Tf 50 750 Td 16 TL\n" + "".join(f"({esc(l)}) Tj T*\n" for l in lines) + "ET" if lines else ""
        cid = page_ids[i] + 1
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {cid} 0 R "
                    f"/Resources << /Font << /F1 3 0 R >> >> >>".encode())
        data = stream.encode("latin-1")
        objs.append(b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offs:
        out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    return bytes(out)


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    pages = [list(p) for p in (PAGES_HEADER_STYLE if "--header-style" in argv else PAGES)]
    if "--marked" in argv:
        pages[0].append("PROTECTED B")
    if "--blank-page" in argv:
        pages.append([])
    open(argv[0], "wb").write(build(pages))
    print(f"wrote {argv[0]} ({len(pages)} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
