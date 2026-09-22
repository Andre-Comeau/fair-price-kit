#!/usr/bin/env python3
"""Build kb/index.json and kb/INDEX.md from approved chunks.

Usage: python tools/build_index.py PROJECT/kb [--include-pending]

A chunk is indexed only if
  - its front matter says `sanitization: approved` (human-reviewed), and
  - tools/scan_sensitive.py patterns find nothing in it (lines marked gate-ok are skipped).
Everything else is listed under "excluded" with the reason (categories/lines, never values).
The index gives an AI a map so it opens only the chunks it needs:
  INDEX.md   read first (human/AI readable)
  index.json machine lookup: chunks, by_doc_type, by_division, xref (reference -> chunk ids)
Exit: 0 ok (even with exclusions), 1 if nothing could be indexed, 2 usage error.
"""
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_sensitive as ss  # noqa: E402
from kbcommon import find_refs, parse_fm  # noqa: E402

STOP = set("""this that with from shall will have been were which their there other than into such
any all are and the for not but may per each also under upon where when include including included
provide provided work works contractor owner section part general products execution
representative material materials project required requirements refer shown specified specification specifications drawings drawing item items include includes shall must use used using""".split())


def keywords(text, n=10):
    text = re.sub(r"\[[A-Z0-9 -]+\]", " ", text)  # placeholders like [PERSON] are not search terms
    words = re.findall(r"[a-z][a-z-]{3,}", text.lower())
    c = Counter(w for w in words if w not in STOP)
    return [w for w, _ in c.most_common(n)]


def scan_text(text):
    hits = Counter()
    for line in text.splitlines():
        if ss.MARKER in line:
            continue
        for cat, rx in ss.PATTERNS:
            for m in rx.finditer(line):
                if cat == "url" and ss.is_public_url(m.group(0)):
                    continue
                if ss.is_allowed(m.group(0)):  # human-reviewed exception from kb/gate-allow.txt
                    continue
                hits[cat] += 1
    return hits


def main(argv):
    inc_pending = "--include-pending" in argv
    args = [a for a in argv if a != "--include-pending"]
    if len(args) != 1 or args[0] in {"-h", "--help"}:
        print(__doc__)
        return 2
    kb = Path(args[0])
    chunks_dir = kb / "chunks"
    if not chunks_dir.is_dir():
        print(f"error: {chunks_dir} not found", file=sys.stderr)
        return 2

    allow_file = kb / "gate-allow.txt"  # reviewed exceptions for the scanner (see scan_sensitive.load_allow)
    if allow_file.is_file():
        try:
            ss.load_allow(allow_file)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    chunks, excluded, xref = [], [], {}
    for f in sorted(chunks_dir.glob("*.md")):
        fm, body = parse_fm(f.read_text(encoding="utf-8"))
        rel = f"chunks/{f.name}"
        if fm.get("sanitization") != "approved" and not inc_pending:
            excluded.append({"path": rel, "reason": f"sanitization is {fm.get('sanitization', 'missing')}, not approved"})
            continue
        hits = scan_text(body + " " + json.dumps(fm))
        if hits:
            excluded.append({"path": rel, "reason": "scanner findings: " + ", ".join(f"{k}={v}" for k, v in sorted(hits.items()))})
            continue
        refs = find_refs(body)
        entry = dict(fm)  # all front matter, incl. change-document metadata (number, amount, related, ...)
        entry.update({"path": rel, "keywords": keywords(body), "refs": refs})
        chunks.append(entry)
        for r in refs:
            xref.setdefault(r, []).append(entry["id"])

    if not chunks:
        print("nothing indexed.", *(f"  excluded {e['path']}: {e['reason']}" for e in excluded), sep="\n")
        return 1

    by_type, by_div = {}, {}
    for c in chunks:
        by_type.setdefault(c["doc_type"], []).append(c["id"])
        if c.get("division"):
            by_div.setdefault(c["division"], []).append(c["id"])
    index = {"schema": "kb-index/1", "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "chunk_count": len(chunks), "chunks": chunks, "by_doc_type": by_type, "by_division": by_div,
             "xref": xref, "excluded": excluded}
    (kb / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")

    md = ["# Knowledge-base index", "",
          "Read this file first. Then open only the chunks you need. `index.json` has the same data for programmatic lookup.",
          "Chunks are sanitized: identifiers are replaced by role placeholders such as [OWNER], [CM], [GC], [SUB-MECH-1].", "",
          f"{len(chunks)} chunks; {len(excluded)} excluded (see bottom).", "",
          "## How to find things",
          "- By document type or MasterFormat division: tables below.",
          "- By cross-reference: `xref` in index.json maps e.g. `CO-007`, `CCN-012`, `SEC-03 30 00`, `SHEET-A101` to the chunks that mention them.",
          "- Change documents link to each other loosely (not one-to-one); follow `refs` and `xref`, and treat links as leads to verify in the text.", ""]
    for t in sorted(by_type):
        md += [f"## {t}", "", "| id | section/sheet | title | pages | keywords | refs |", "|---|---|---|---|---|---|"]
        for c in chunks:
            if c["doc_type"] != t:
                continue
            md.append("| {id} | {s} | {t} | {p} | {k} | {r} |".format(
                id=c["id"], s=c.get("section") or c.get("sheet") or "", t=(c.get("chunk_title") or c.get("doc_title") or "").replace("|", "/"),
                p="-".join(str(x) for x in dict.fromkeys(c.get("pages", []))), k=", ".join(c["keywords"][:6]),
                r=", ".join(c["refs"][:6])))
        md.append("")
    if excluded:
        md += ["## Excluded (fix, review or approve, then rebuild)", ""] + [f"- {e['path']}: {e['reason']}" for e in excluded] + [""]
    (kb / "INDEX.md").write_text("\n".join(md), encoding="utf-8")
    print(f"indexed {len(chunks)} chunk(s); excluded {len(excluded)}")
    for e in excluded:
        print(f"  excluded {e['path']}: {e['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
