#!/usr/bin/env python3
"""Deterministic first-pass scrub + classification-marking check. No LLM involved.

Usage: python tools/prescrub.py IN.md OUT.md [--ack-markings]

Run this BEFORE any LLM sees the text. It
  1. looks for security-classification markings and security-sensitive terms
     (Protected A/B/C, Confidential, Secret, Top Secret, French equivalents, ...).
     If markings are found it writes nothing and exits 3, unless --ack-markings
     is given after a HUMAN has decided the document may proceed;
  2. replaces pattern-shaped identifiers with generic tokens: emails, phone
     numbers, postal codes, coordinates, business numbers, SIN-like numbers,
     non-government URLs, titled personal names, and the value after
     "Prepared by:" style signature lines.
It does NOT catch names in plain words (companies, people, sites, addresses).
That is the LLM's and the reviewer's job (see ingestion/RULEBOOK.md).
Output shows counts and line numbers only, never the values.
Exit: 0 ok, 2 usage error, 3 classification markings found (nothing written).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_sensitive as ss  # noqa: E402

MARKINGS = re.compile(
    r"\b(?:protected\s+[abc]|top\s+secret|secret|confidential|cabinet\s+confidence|"
    r"prot[ée]g[ée]\s+[abc]|tr[èe]s\s+secret|confidentiel|"
    r"security\s+requirements?\s+check\s*list|srcl)\b", re.I)
SECURITY_TERMS = re.compile(
    r"\b(?:access\s+control|card\s+reader|cctv|intrusion\s+detection|security\s+zone|"
    r"secure\s+room|secure\s+area|restricted\s+area|vault|security\s+system|"
    r"blast|ballistic|forced[- ]entry|alarm\s+panel)\b", re.I)

SIGNATURE = re.compile(r"^(\s*(?:signed|signature|approved by|prepared by|reviewed by)\s*:).*\S", re.I | re.M)

RULES = [  # (category in scan_sensitive, token)
    ("email", "[EMAIL]"),
    ("phone", "[PHONE]"),
    ("postal-code", "[POSTAL-CODE]"),
    ("coordinates", "[COORDINATES]"),
    ("business-number", "[BUSINESS-NO]"),
    ("sin-like", "[ID-NUMBER]"),
    ("person-title", "[PERSON]"),
]
PATS = dict(ss.PATTERNS)


def lines_with(rx, text):
    return sorted({n for n, line in enumerate(text.splitlines(), 1) if rx.search(line)})


def main(argv):
    ack = "--ack-markings" in argv
    args = [x for x in argv if x != "--ack-markings"]
    if len(args) != 2:
        print(__doc__)
        return 2
    src, dst = Path(args[0]), Path(args[1])
    if not src.is_file():
        print(f"error: not found: {src}", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8", errors="replace")

    marks = lines_with(MARKINGS, text)
    sec = lines_with(SECURITY_TERMS, text)
    if sec:
        print(f"ADVISORY: security-sensitive terms on lines {sec[:20]}{'...' if len(sec) > 20 else ''}. "
              "Ask the user whether this content is restricted before it goes further.")
    if marks and not ack:
        print(f"STOP: possible classification or security markings on lines {marks[:20]}"
              f"{'...' if len(marks) > 20 else ''}. Nothing written.")
        print("A human must decide whether this document may be processed at all "
              "(see ingestion/RULEBOOK.md section 1). Re-run with --ack-markings only after that decision.")
        return 3

    counts = {}
    for cat, token in RULES:
        text, n = PATS[cat].subn(token, text)
        if n:
            counts[cat] = n
    text, n = SIGNATURE.subn(r"\1 [PERSON]", text)
    if n:
        counts["signature-line"] = n
    # non-government URLs
    def _url(m):
        return m.group(0) if ss.is_public_url(m.group(0)) else "[URL]"
    text, n = PATS["url"].subn(_url, text)
    n = len(re.findall(r"\[URL\]", text))
    if n:
        counts["url"] = n

    dst.write_text(text, encoding="utf-8")
    print("replaced:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "nothing")
    if marks:
        print(f"markings acknowledged by user on lines {marks[:20]} (record this in private/LOG.md)")
    print("Still to do by the LLM/reviewer: company, vendor, person, site and address names in plain words.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
