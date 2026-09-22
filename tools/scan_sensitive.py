#!/usr/bin/env python3
"""Pattern-based pre-share scan for contact info and identifiers.

Backstop for the sensitive-information gate (gates/sensitive-info-gate.md).
It finds only pattern-shaped items (emails, phones, postal codes, addresses,
company-suffix names, contract numbers, ...). It CANNOT find vendor, person or
site names written in plain words. A clean result is not a guarantee.

Usage:  python tools/scan_sensitive.py PATH [PATH ...]
Exit:   0 = nothing found, 1 = findings, 2 = usage/read error
Values are masked in the output; they are never printed in full.
A line containing the marker  gate-ok  is skipped (use for reviewed public items).
"""
import re
import sys
from pathlib import Path

PUBLIC_URL_HOSTS = (".canada.ca", "canada.ca", ".gc.ca", "gc.ca")  # public government sites are not flagged
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
TEXT_EXT = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".html", ".htm",
            ".xml", ".tsv", ".rtf", ".eml", ".log", ""}
MARKER = "gate-ok"

STREET = (r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|"
          r"way|court|ct|crescent|cres|place|pl|parkway|pkwy|highway|hwy|"
          r"rue|chemin|promenade|prom|sentier)")
SUFFIX = r"(?:Inc|Ltd|Ltée|Limitée|Limited|Corp|Corporation|LLC|LLP|Co|GP|S\.?E\.?N\.?C\.?|ULC)"

PATTERNS = [
    # allows a hyphen followed by a line-break space inside the domain ("name@org- other.ca"), common in extracted PDFs
    ("email", re.compile(r"[\w.+-]+@[\w-]+(?:-\s+[\w-]+)?(?:\.[\w-]+)+")),
    # a phone number needs a cue: parentheses, hyphen/dot separators, or a label (Tel, Phone, Fax, T:, F:).
    # Plain space-separated digit groups ("300 300 2500") are dimensions in drawings, not phones.
    ("phone", re.compile(
        r"(?<![\w.])(?:(?:\+?1[\s.-]?)?(?:\([2-9]\d{2}\)[\s.-]?\d{3}[\s.-]\d{4}|[2-9]\d{2}[.-]\d{3}[.-]\d{4})"
        r"|(?:(?i:tel|phone|fax|cell|mobile)\.?:?|(?i:[tf])\s*:)\s*(?:\+?1[\s.-]?)?\(?[2-9]\d{2}\)?[\s.-]\d{3}[\s.-]\d{4})(?!\d)")),
    ("postal-code", re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[A-Z][ -]?\d[A-Z]\d\b", re.I)),
    # number + 1-3 Capitalized words + street type ("123 Example Street"); or French "45 rue Principale".
    # Capitalization of the name words is case-sensitive so numbered spec headings ("3.1 Place concrete") do not match.
    ("street-address", re.compile(
        r"\b\d{1,6}[A-Za-z]?,?\s+(?:[A-Z][\w'.-]*\s+){1,3}(?i:" + STREET + r")\b\.?"
        r"|\b\d{1,6}[A-Za-z]?,?\s+(?i:rue|chemin|boulevard|boul|avenue|av|promenade)\.?\s+[A-Z][\w'-]+")),
    ("company-name", re.compile(r"\b(?:[A-Z][\w&'.-]*\s+){1,5}" + SUFFIX + r"\b\.?")),
    ("business-number", re.compile(r"\b\d{9}\s?R[TPCZ]\s?\d{4}\b", re.I)),
    # hyphenated 3-3-3, or labelled (SIN / social insurance number); "450 450 450" is a dimension list
    ("sin-like", re.compile(r"\b\d{3}-\d{3}-\d{3}\b|(?i:\bSIN\b|social\s+insurance(?:\s+number)?|\bNAS\b)\W{0,3}\d{3}[ -]?\d{3}[ -]?\d{3}\b")),
    ("coordinates", re.compile(r"[-+]?\d{1,3}\.\d{4,}\s*[,;]\s*[-+]?\d{1,3}\.\d{4,}")),
    ("url", re.compile(r"\bhttps?://[^\s)>\]\"']+|\bwww\.[^\s)>\]\"']+", re.I)),
    ("contract-id", re.compile(
        r"\b(?:contract|solicitation|tender|rfp|rfq|rfi|rfso|po|purchase order|file|"
        r"project|amendment|bid|quote)\b\s*(?:no\.?|number|#|n[o°]\.?)?\s*[:#]?\s*"
        r"[A-Z0-9]{2,}(?:[-/][A-Z0-9]+)+\b", re.I)),
    # titles only. A bare "M" needs a period and a space ("M. Tremblay"): "M.Sc." and "H/M Lab" are not names, and an
    # over-eager match once turned the date "July 9, 2020" into "[PERSON] 9, 2020" (destroying data is worse than missing a name).
    ("person-title", re.compile(
        r"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Mme)\.?\s+[A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+)?|\bM\.\s+[A-Z][a-z'-]+")),
    # a value that is only a [PLACEHOLDER] is fine
    ("signature-line", re.compile(r"^\s*(?:signed|signature|approved by|prepared by|reviewed by)\s*:(?!\s*\[[A-Z0-9 -]+\]\s*$).*\S", re.I)),
    ("marked-restricted", re.compile(
        r"\b(?:confidential|protected\s+[abc]|privileged|in[- ]confidence|"
        r"commercially sensitive|nda)\b", re.I)),
]


def mask(value: str) -> str:
    v = value.strip()
    if len(v) <= 4:
        return "*" * len(v)
    return v[:2] + "*" * min(len(v) - 3, 8) + v[-1]


ALLOW = []  # reviewed exceptions: ("lit", lowercase substring) or ("re", compiled regex); see load_allow


def load_allow(path):
    """Read a reviewed-exceptions file: one entry per line, '#' comments. A plain line is a case-insensitive
    substring of the MATCHED text; a line starting 're:' is a regex searched in the matched text. Use it for
    matches a human has reviewed and accepted (public body names, ALL-CAPS drawing notes read as addresses,
    a proprietary-information notice). It only silences matching text; it never disables a pattern."""
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        ALLOW.append(("re", re.compile(line[3:].strip(), re.I)) if line.startswith("re:") else ("lit", line.lower()))


def is_allowed(text: str) -> bool:
    tl = text.lower()
    return any((k == "lit" and v in tl) or (k == "re" and v.search(text)) for k, v in ALLOW)


def is_public_url(url: str) -> bool:
    host = re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split(":")[0].lower()
    return host.endswith(PUBLIC_URL_HOSTS)


def is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXT


def iter_files(paths):
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not (set(f.parts) & SKIP_DIRS) and is_text(f):
                    yield f
        elif p.is_file():
            yield p
        else:
            print(f"error: not found: {raw}", file=sys.stderr)
            sys.exit(2)


def scan_file(path: Path):
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"error: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)
    for n, line in enumerate(text.splitlines(), 1):
        if MARKER in line:
            continue
        for cat, rx in PATTERNS:
            for m in rx.finditer(line):
                if cat == "url" and is_public_url(m.group(0)):
                    continue
                if is_allowed(m.group(0)):
                    continue
                hits.append((n, cat, mask(m.group(0))))
    return hits


def main(argv):
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 2
    if "--allow" in argv:  # --allow FILE: reviewed exceptions (see load_allow)
        i = argv.index("--allow")
        if i + 1 >= len(argv):
            print("error: --allow needs a file", file=sys.stderr)
            return 2
        load_allow(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    total = 0
    by_cat = {}
    for f in iter_files(argv):
        hits = scan_file(f)
        for n, cat, masked in hits:
            print(f"{f}:{n}: {cat}: {masked}")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        total += len(hits)
    if total:
        summary = ", ".join(f"{c}={n}" for c, n in sorted(by_cat.items()))
        print(f"\nWARNING: {total} possible sensitive item(s) ({summary}). "
              "Values masked. Do not share until reviewed.")
        print("This scan finds patterns only. It cannot detect vendor, person or site names in plain words.")
        return 1
    print("No pattern matches. This does NOT guarantee the content is free of "
          "vendor, person, site or other identifying names. Review before sharing.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
