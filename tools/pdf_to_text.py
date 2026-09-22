#!/usr/bin/env python3
"""Convert a PDF to page-marked Markdown text. Local only: no network, no LLM.

Usage: python tools/pdf_to_text.py IN.pdf OUT.md [--min-chars 40] [--raw]

--raw   read text in content-stream order (pdftotext -raw) instead of preserving the page layout. Use it for
        DRAWINGS: layout mode pads large sheets with spaces (a 14-page drawing set gave 9.9 million characters,
        98% whitespace) and scatters labels; raw mode is compact.

Engines, in order: pdftotext (poppler, -layout), then pypdf if installed.
Pages with almost no text (scans, or text drawn as outlines) are listed: this
tool does NOT OCR. The source filename and the PDF's metadata (title, author,
producer) are deliberately NOT copied into the output; they often identify
the project or people.
Exit: 0 ok, 2 usage/engine error, 4 no page had usable text (needs OCR).
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def via_pdftotext(pdf, raw=False):
    exe = shutil.which("pdftotext")
    if not exe:
        return None, None
    r = subprocess.run([exe, "-raw" if raw else "-layout", "-enc", "UTF-8", str(pdf), "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace").strip() or "pdftotext failed")
    pages = r.stdout.decode("utf-8", "replace").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages, "pdftotext"


def via_pypdf(pdf):
    try:
        from pypdf import PdfReader
    except ImportError:
        return None, None
    return [(p.extract_text() or "") for p in PdfReader(str(pdf)).pages], "pypdf"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--min-chars", type=int, default=40, help="non-space chars below which a page counts as 'no text'")
    ap.add_argument("--raw", action="store_true", help="content-stream order, no layout padding (for drawings)")
    a = ap.parse_args()
    pdf = Path(a.pdf)
    if not pdf.is_file():
        print(f"error: not found: {pdf}", file=sys.stderr)
        return 2
    try:
        pages, engine = via_pdftotext(pdf, a.raw)
        if pages is None:
            pages, engine = via_pypdf(pdf)
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 2
    if pages is None:
        print("error: no PDF engine found. Install poppler (pdftotext) or `pip install pypdf`.", file=sys.stderr)
        return 2

    low = []
    out = []
    for i, text in enumerate(pages, 1):
        body = "\n".join(line.rstrip() for line in text.splitlines()).strip("\n")
        if len(re.sub(r"\s", "", body)) < a.min_chars:
            low.append(i)
        out.append(f"<!-- page {i} -->\n{body}\n")
    header = (f"<!-- converted-by: pdf_to_text; engine: {engine}; pages: {len(pages)}; "
              f"low_text_pages: {low}; source: withheld -->\n\n")
    Path(a.out).write_text(header + "\n".join(out), encoding="utf-8")

    print(f"pages: {len(pages)}  engine: {engine}  low-text pages: {low if low else 'none'}")
    if low:
        print("note: low-text pages may be scans or outlined text; they need OCR or manual transcription.")
    return 4 if len(low) == len(pages) else 0


if __name__ == "__main__":
    sys.exit(main())
