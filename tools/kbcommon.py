"""Shared helpers for the ingestion tools (stdlib only)."""
import json
import re

_FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)

# Change-document references, e.g. "CCN-012", "CO 7", "EA No. 4". Heuristic: "CO 2 emissions" would match.
REF_CHANGE = re.compile(r"\b(CCN|CO|CI|CD|SI|EA)(?:\s*(?:No\.?|Number|#)\s*|[\s.:-]+)0*(\d{1,4})\b")
REF_SECTION = re.compile(r"\b(?:Section|Sect\.)\s+(\d{2})[\s.-]?(\d{2})[\s.-]?(\d{2})\b|\b(?:Section|Sect\.)\s+(\d{5})\b", re.I)
REF_SHEET = re.compile(r"\b(?:Drawings?|Dwgs?\.?|Sheets?)\s+([A-Z]{1,2}-?\d{2,3}[A-Za-z]?)\b", re.I)


def dump_fm(d):
    return "---\n" + "".join(f"{k}: {json.dumps(v, ensure_ascii=False)}\n" for k, v in d.items()) + "---\n"


def parse_fm(text):
    m = _FM.match(text)
    if not m:
        return {}, text
    d = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        try:
            d[k.strip()] = json.loads(v.strip())
        except ValueError:
            d[k.strip()] = v.strip()
    return d, text[m.end():]


def slug(s, n=40):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:n].strip("-") or "x"


def find_refs(text):
    refs = set()
    for m in REF_CHANGE.finditer(text):
        refs.add(f"{m.group(1).upper()}-{int(m.group(2)):03d}")
    for m in REF_SECTION.finditer(text):
        digits = "".join(g for g in m.groups() if g)
        # 6-digit numbers are spaced ("03 30 00"); older 5-digit numbers are kept as written ("03300")
        refs.add("SEC-" + (" ".join([digits[0:2], digits[2:4], digits[4:6]]) if len(digits) == 6 else digits))
    for m in REF_SHEET.finditer(text):
        refs.add("SHEET-" + m.group(1).upper().replace(" ", ""))
    return sorted(refs)
