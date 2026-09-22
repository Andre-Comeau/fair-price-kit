#!/usr/bin/env python3
"""End-to-end test of the script pipeline on a SYNTHETIC PDF (all data invented):
init_project -> pdf_to_text -> prescrub -> (simulated sanitization) -> chunk_doc -> build_index, plus the gates:
marking stop, low-text detection, pending/unsanitized chunks refused, reviewed exceptions.
Needs poppler's `pdftotext`; without it the test prints SKIP and exits 0.
Run: python tools/test/test_pipeline.py"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
TEST = Path(__file__).resolve().parent


def run(script, *args, cwd=None):
    r = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def main():
    if not shutil.which("pdftotext"):
        print("SKIP test_pipeline: pdftotext (poppler) not installed")
        return 0
    bad = []
    tmp = Path(tempfile.mkdtemp())
    try:
        proj = tmp / "P001"
        rc, out = run(TOOLS / "init_project.py", proj)
        if rc != 0 or not (proj / "kb" / "chunks").is_dir():
            bad.append(("init_project", out))
        # 1. a clean synthetic spec
        pdf = proj / "raw" / "spec.pdf"
        run(TEST / "make_synthetic_pdf.py", pdf)
        rc, out = run(TOOLS / "pdf_to_text.py", pdf, proj / "text" / "spec.raw.md")
        if rc != 0 or "low-text pages: none" not in out:
            bad.append(("pdf_to_text", out))
        rc, out = run(TOOLS / "prescrub.py", proj / "text" / "spec.raw.md", proj / "text" / "spec.pre.md")
        pre = (proj / "text" / "spec.pre.md").read_text(encoding="utf-8")
        if rc != 0 or "jane.doe@example.com" in pre or "555-0123" in pre or "[EMAIL]" not in pre:
            bad.append(("prescrub replaces contact info", out))
        # 2. unsanitized names must be caught before indexing (owner name and address left in on purpose)
        san = proj / "sanitized" / "spec.md"
        san.write_text(pre, encoding="utf-8")
        chunks = proj / "kb" / "chunks"
        rc, out = run(TOOLS / "chunk_doc.py", san, "--type", "spec", "--doc-id", "SPEC-1", "--out", chunks, "--approved")
        rc, out = run(TOOLS / "build_index.py", proj / "kb")
        if "excluded" not in out or "company-name" not in out:
            bad.append(("index must exclude a chunk with an unreplaced owner name", out))
        # 3. after sanitization the same chunks index cleanly, with correct sections and pages
        for f in chunks.glob("*.md"):
            f.unlink()
        clean = pre.replace("Example Owner Corp.", "[OWNER]").replace("123 Example Street, Ottawa", "[SITE-ADDRESS]")
        san.write_text(clean, encoding="utf-8")
        run(TOOLS / "chunk_doc.py", san, "--type", "spec", "--doc-id", "SPEC-1", "--out", chunks, "--approved")
        rc, out = run(TOOLS / "build_index.py", proj / "kb")
        idx = json.loads((proj / "kb" / "index.json").read_text(encoding="utf-8"))
        sections = {c.get("section"): c["pages"] for c in idx["chunks"]}
        if rc != 0 or idx["chunk_count"] != 3 or sections.get("03 30 00") != [2, 2] or sections.get("05 12 00") != [3, 3]:
            bad.append(("clean index", out, sections))
        if "CO-007" not in idx["xref"] or "SEC-05 12 00" not in idx["xref"]:
            bad.append(("cross-references", list(idx["xref"])))
        # 4. pending chunks are never indexed
        for f in chunks.glob("*.md"):
            f.unlink()
        run(TOOLS / "chunk_doc.py", san, "--type", "spec", "--doc-id", "SPEC-1", "--out", chunks)  # no --approved
        rc, out = run(TOOLS / "build_index.py", proj / "kb")
        if rc != 1 or "not approved" not in out:
            bad.append(("pending chunks must be refused", rc, out))
        # 5. classification marking stops the scrub and writes nothing
        marked = tmp / "marked.pdf"
        run(TEST / "make_synthetic_pdf.py", marked, "--marked")
        run(TOOLS / "pdf_to_text.py", marked, tmp / "m.md")
        rc, out = run(TOOLS / "prescrub.py", tmp / "m.md", tmp / "m.out.md")
        if rc != 3 or (tmp / "m.out.md").exists():
            bad.append(("marking stop", rc, out))
        # 6. blank pages are reported, not invented
        blank = tmp / "blank.pdf"
        run(TEST / "make_synthetic_pdf.py", blank, "--blank-page")
        rc, out = run(TOOLS / "pdf_to_text.py", blank, tmp / "b.md")
        if "low-text pages: [4]" not in out:
            bad.append(("low-text detection", out))
        # 7. reviewed exceptions: a match silenced by kb/gate-allow.txt, others still stop the index
        (chunks).mkdir(exist_ok=True)
        for f in chunks.glob("*.md"):
            f.unlink()
        noted = clean.replace("Refer to CO-007", "Contact Northwind Traders Inc. and refer to CO-007")
        san.write_text(noted, encoding="utf-8")
        run(TOOLS / "chunk_doc.py", san, "--type", "spec", "--doc-id", "SPEC-1", "--out", chunks, "--approved")
        rc, out = run(TOOLS / "build_index.py", proj / "kb")
        if "company-name" not in out:
            bad.append(("company name must be flagged", out))
        (proj / "kb" / "gate-allow.txt").write_text("Northwind Traders Inc\n", encoding="utf-8")
        rc, out = run(TOOLS / "build_index.py", proj / "kb")
        if rc != 0 or "excluded 0" not in out:
            bad.append(("reviewed exception should let the chunk through", out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if bad:
        for b in bad:
            print("FAIL", b)
        return 1
    print("pipeline test passes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
