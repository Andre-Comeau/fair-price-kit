#!/usr/bin/env python3
"""Create a project workspace for the ingestion workflow.

Usage: python tools/init_project.py PROJECT_DIR

PROJECT_DIR should be a neutral, non-identifying folder name (e.g. P001), inside a
folder that is NOT synced to a cloud service. Layout created:

  raw/         originals (PDF etc.)               PRIVATE
  text/        converted + pre-scrubbed text      PRIVATE
  private/     mapping table, log                 PRIVATE
  sanitized/   reviewed, identifier-free .md      shareable only after the output gate
  kb/          chunks + index.json + INDEX.md     shareable only after the output gate
"""
import sys
from pathlib import Path

PRIVATE = ["raw", "text", "private"]
SHAREABLE = ["sanitized", "kb", "kb/chunks"]


def main(argv):
    if len(argv) != 1 or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 2
    root = Path(argv[0])
    if root.exists() and any(root.iterdir()):
        print(f"error: {root} exists and is not empty; refusing to touch it", file=sys.stderr)
        return 2
    for d in PRIVATE + SHAREABLE:
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / ".gitignore").write_text("raw/\ntext/\nprivate/\n", encoding="utf-8")
    (root / "README-PRIVATE.txt").write_text(
        "raw/, text/ and private/ contain unsanitized or re-identifying material.\n"
        "Never copy them into a repository, shared drive, email or chat.\n"
        "Only sanitized/ and kb/ may leave, and only after the output gate\n"
        "(tools/scan_sensitive.py clean or reviewed, plus explicit user approval).\n",
        encoding="utf-8")
    (root / "private" / "mapping.csv").write_text(
        "placeholder,role,real_value,first_seen_doc\n", encoding="utf-8")  # real_value = the re-identification key: most sensitive file
    (root / "private" / "LOG.md").write_text(
        "# Private ingestion log (never share)\n\n| time | doc (private name) | step | note |\n|---|---|---|---|\n",
        encoding="utf-8")
    (root / "kb" / "gate-allow.txt").write_text(
        "# Reviewed exceptions for tools/scan_sensitive.py (read automatically by tools/build_index.py).\n"
        "# Only a human adds lines here, after looking at the match. A plain line is a case-insensitive substring of the\n"
        "# MATCHED text; a line starting 're:' is a regex. Only matching text is silenced; the patterns stay on.\n"
        "# Add a short comment above each entry saying why it is safe (e.g. a public body's name).\n",
        encoding="utf-8")
    print(f"created {root}/ with raw text private sanitized kb (kb/gate-allow.txt is the reviewed-exceptions list)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
