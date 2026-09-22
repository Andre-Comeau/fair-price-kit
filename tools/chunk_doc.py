#!/usr/bin/env python3
"""Split ONE sanitized Markdown document into chunk files with front matter.

Usage:
  python tools/chunk_doc.py SANITIZED.md --type spec --doc-id SPEC-1 --title "Project specification" \
         --out PROJECT/kb/chunks [--approved] [--max-chars 12000] [--meta key=json ...]

--type   spec | drawing | ccn | co | ci | cd | si | ea | other
--approved  marks the chunks `sanitization: approved`. Use it only AFTER the human review of the
         sanitized text. Without it chunks are `pending` and build_index.py will skip them.
--meta   extra front-matter fields (a `---` header block at the top of the sanitized document is read the same way,
         minus reserved keys such as sanitization/id/pages; --meta wins), e.g. --meta amount=12500 --meta amount_type='"fixed"'
         (value is parsed as JSON, else kept as a string).

Chunking rules
  spec     split at "SECTION nn nn nn" headings (6-digit; 5-digit accepted and kept as written); a
           section over --max-chars is split at "PART 1/2/3", then at paragraph breaks.
  drawing  one chunk per page (one page = one sheet).
  others   one chunk per document; split by page only if longer than --max-chars.
Division names come from masterformat.json (project dependent), never from a built-in list.
Front matter values are JSON so tools and LLMs can parse them without a YAML library.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import dump_fm, parse_fm, slug  # noqa: E402
from spec_headers import spec_sections_from_headers  # noqa: E402

# keys a document's own header block may NOT set (the chunker/flow decides these)
RESERVED = {"id", "doc_type", "doc_id", "doc_title", "section", "sheet", "chunk_title", "division", "division_name",
            "masterformat_edition", "pages", "chars", "sanitization"}

PAGE = re.compile(r"^<!-- page (\d+) -->\s*$", re.M)
SEC6 = re.compile(r"^\s*SECTION\s+(\d{2})[\s.-]?(\d{2})[\s.-]?(\d{2})(?:\.\d+)?\s*[-–—:]?\s*(.*)$", re.I)
SEC5 = re.compile(r"^\s*SECTION\s+(\d{5})\s*[-–—:]?\s*(.*)$", re.I)
PART = re.compile(r"^\s*PART\s+([123])\b\s*[-–—:]?\s*(.*)$", re.I)
SHEET = re.compile(r"^\s*(?:SHEET(?:\s*(?:NO|NUMBER)\.?)?|DWG\.?\s*NO\.?)\s*:?\s*([A-Z]{0,2}-?\d{1,3}(?:\.\d+)?[A-Za-z]?)\s*$", re.I)

def page_at(text, pos, default=1):
    last = default
    for m in PAGE.finditer(text, 0, pos + 1):
        last = int(m.group(1))
    return last


def first_line(body, width=80):
    """First line with real words (>= 8 letters overall), whitespace collapsed, cut at `width`; '' if none."""
    for line in body.splitlines():
        s = re.sub(r"\s+", " ", re.sub(r"\[[A-Z0-9?-]+\]", "", line)).strip(" .:-|_")
        if len(re.findall(r"[A-Za-z]", s)) >= 8:
            return s[:width]
    return ""


def split_long(body, max_chars):
    if len(body) <= max_chars:
        return [body]
    out, cur = [], ""
    for para in re.split(r"\n\s*\n", body):
        if cur and len(cur) + len(para) + 2 > max_chars:
            out.append(cur)
            cur = ""
        cur = (cur + "\n\n" + para) if cur else para
    if cur:
        out.append(cur)
    return out


def spec_sections(text):
    """Return [(section_no|None, title, start_pos, end_pos)]."""
    heads = []
    pos = 0
    for line in text.splitlines(keepends=True):
        m6, m5 = SEC6.match(line), SEC5.match(line)
        if m6:
            heads.append((f"{m6.group(1)} {m6.group(2)} {m6.group(3)}", m6.group(4).strip(), pos))
        elif m5:
            d = m5.group(1)
            heads.append((d, m5.group(2).strip(), pos))  # keep 5-digit numbers as the project writes them
        pos += len(line)
    if not heads:
        return [(None, "", 0, len(text))]
    out = []
    if heads[0][2] > 0 and text[:heads[0][2]].strip():
        out.append((None, "front matter", 0, heads[0][2]))
    for i, (no, title, start) in enumerate(heads):
        end = heads[i + 1][2] if i + 1 < len(heads) else len(text)
        out.append((no, title, start, end))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--type", required=True, choices=["spec", "drawing", "ccn", "co", "ci", "cd", "si", "ea", "other"])
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--max-chars", type=int, default=12000)
    ap.add_argument("--meta", action="append", default=[])
    ap.add_argument("--divisions", help="JSON file {\"edition\": str, \"divisions\": {\"03\": \"Concrete\", ...}}; "
                    "default: <out>/../masterformat.json if present. Division names are NEVER assumed: the MasterFormat "
                    "edition is project dependent, so take them from the spec's own table of contents.")
    ap.add_argument("--sections-from", choices=["headings", "page-headers"], default="headings",
                    help="spec only. headings: lines 'SECTION nn nn nn - TITLE' (default). page-headers: group pages by the "
                         "'Section nn nn nn' running header at the top of each page (see tools/spec_headers.py)")
    a = ap.parse_args()

    text = Path(a.src).read_text(encoding="utf-8")
    text = re.sub(r"\A<!--.*?-->\s*", "", text, count=1, flags=re.S) if text.startswith("<!-- converted-by") else text
    # optional metadata header at the top of the sanitized document (`---` block of `key: json` lines)
    header, text = parse_fm(text)
    header = {k: v for k, v in header.items() if k not in RESERVED}
    extra = {}
    for kv in a.meta:
        k, _, v = kv.partition("=")
        try:
            extra[k] = json.loads(v)
        except ValueError:
            extra[k] = v
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    status = "approved" if a.approved else "pending"
    div_path = Path(a.divisions) if a.divisions else out.parent / "masterformat.json"
    div_names, edition = {}, None
    if div_path.is_file():
        cfg = json.loads(div_path.read_text(encoding="utf-8"))
        div_names, edition = cfg.get("divisions", {}), cfg.get("edition")
    elif a.type == "spec":
        print(f"note: no {div_path.name}; division names will be omitted (numbers only). "
              "Build it from the spec's table of contents (ingestion/RULEBOOK.md).")

    pieces = []  # (suffix, title, section, division, start_page, end_page, body)
    if a.type == "spec":
        sections = spec_sections_from_headers(text) if a.sections_from == "page-headers" else spec_sections(text)
        for no, title, s, e in sections:
            seg = text[s:e]
            sp = page_at(text, s)
            core = re.sub(r"(?:\s*<!-- page \d+ -->\s*)+\Z", "", seg)  # a trailing page marker belongs to the next section
            ep = page_at(text, s + max(len(core) - 1, 0))
            div = no[:2] if no else None
            if len(seg) <= a.max_chars:
                pieces.append((slug(no or "front"), title, no, div, sp, ep, seg))
                continue
            parts, idxs = [], [m.start() for m in (re.finditer(r"^\s*PART\s+[123]\b.*$", seg, re.M | re.I))]
            if len(idxs) >= 2:
                bounds = ([0] if idxs[0] > 0 else []) + idxs + [len(seg)]
                for i in range(len(bounds) - 1):
                    chunk = seg[bounds[i]:bounds[i + 1]]
                    pm = PART.match(chunk.lstrip().splitlines()[0]) if chunk.strip() else None
                    parts.append((f"part{pm.group(1)}" if pm else "head", chunk))
            else:
                parts = [("", seg)]
            # a tiny heading-only 'head' part (before PART 1) is merged into the next part, not kept as a stub chunk
            if len(parts) > 1 and parts[0][0] == "head" and len(parts[0][1].strip()) < 600:
                parts = [(parts[1][0], parts[0][1] + parts[1][1])] + parts[2:]
            n = 0
            for label, chunk in parts:
                for sub in split_long(chunk, a.max_chars):
                    n += 1
                    suffix = "-".join(x for x in [slug(no or "front"), label, f"p{n}" if len(parts) > 1 or len(sub) < len(chunk) else ""] if x)
                    # page range of THIS piece (locate its first/last 60 characters inside the section)
                    first = seg.find(sub.strip()[:60])
                    last = seg.rfind(sub.strip()[-60:])
                    if first < 0 or last < 0:
                        ssp, sep = sp, ep
                    else:
                        ssp = page_at(text, s + first)
                        sep = page_at(text, s + last)
                    pieces.append((suffix, title, no, div, ssp, sep, sub))
    elif a.type == "drawing":
        marks = list(PAGE.finditer(text))
        if not marks:
            marks = []
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[m.end():end].strip("\n")
            sheet = None
            for line in body.splitlines():
                sm = SHEET.match(line)
                if sm:
                    sheet = sm.group(1).upper()
                    break
            pieces.append((f"pg{int(m.group(1)):03d}", f"Sheet page {m.group(1)}", sheet, None,
                           int(m.group(1)), int(m.group(1)), body))
        if not marks:
            pieces.append(("all", a.title, None, None, 1, 1, text))
    else:
        marks = list(PAGE.finditer(text))
        if len(text) <= a.max_chars or not marks:
            pieces.append(("all", a.title, None, None, 1, page_at(text, len(text)), text))
        else:
            for i, m in enumerate(marks):
                end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
                pbody = text[m.end():end].strip("\n")
                # page chunks of a report/RFP have no section titles: use the page's first meaningful line so the index is navigable
                pieces.append((f"pg{int(m.group(1)):03d}", first_line(pbody) or a.title, None, None,
                               int(m.group(1)), int(m.group(1)), pbody))

    written = 0
    for suffix, title, sec, div, sp, ep, body in pieces:
        body = PAGE.sub("", body).strip("\n")
        if not body.strip():
            continue
        cid = f"{slug(a.doc_id, 30)}__{suffix}"
        fm = {
            "id": cid, "doc_type": a.type, "doc_id": a.doc_id,
            "doc_title": a.title, "section": sec if a.type == "spec" else None,
            "sheet": sec if a.type == "drawing" else None,
            "chunk_title": title, "division": div,
            "division_name": div_names.get(div) if div else None,
            "masterformat_edition": edition if a.type == "spec" else None,
            "pages": [sp, ep], "chars": len(body), "sanitization": status,
        }
        fm = {**header, **fm, **extra}  # header < generated fields < explicit --meta
        fm = {k: v for k, v in fm.items() if v is not None}
        (out / f"{cid}.md").write_text(dump_fm(fm) + "\n" + body + "\n", encoding="utf-8")
        written += 1
    print(f"wrote {written} chunk(s) to {out} (sanitization: {status})")
    if not a.approved:
        print("chunks are 'pending': re-run with --approved after human review, or build_index.py will skip them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
