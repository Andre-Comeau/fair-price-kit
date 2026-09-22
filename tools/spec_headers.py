"""Section detection from running page headers (for specs that have no 'SECTION nn nn nn' heading lines).

Real example (NCC tender specs): every page starts with a 3-4 line header laid out in columns by pdftotext:

    <project name>      <SECTION TITLE>      Section 01 33 00
    <project name cont>                      Page 2 of 6
    <project no.>                            <month, year>

Consecutive pages with the same section number form one section. Pages before the first header
(cover) become 'front matter'. Titles are a heuristic (middle columns of the first header lines) and
should be checked; the section number is the reliable part.
"""
import re

PAGE = re.compile(r"^<!-- page (\d+) -->\s*$", re.M)
# 6-digit MasterFormat number (optionally with .nn decimals), or a project-specific code like A9030
SEC = re.compile(r"\bSection\s+((?:\d{2}\s\d{2}\s\d{2}(?:\.\d+)*)|(?:[A-Z]{1,2}\d{3,5}))\b", re.I)
DROP = re.compile(r"^(Section\b|Page\s+\d+\s+of\s+\d+|[A-Z][a-z]+,?\s+\d{4}$|.*Project\s*(#|No\.?|Number)\b)", re.I)


def _header_info(page_text):
    """Return (section_number, title) from the first header lines of one page, or (None, '')."""
    lines = [ln.rstrip() for ln in page_text.split("\n") if ln.strip()][:6]
    sec = None
    for ln in lines:
        m = SEC.search(ln)
        if m:
            sec = re.sub(r"\s+", " ", m.group(1).strip())
            break
    if not sec:
        return None, ""
    pieces = []
    for ln in lines[:3]:
        cols = re.split(r"\s{2,}", ln.strip())
        for c in cols[1:]:  # first column is the project name
            if c and not DROP.match(c.strip()):
                pieces.append(c.strip())
    return sec.upper() if sec[0].isalpha() else sec, " ".join(pieces)


def spec_sections_from_headers(text):
    """Return [(section_no|None, title, start_pos, end_pos)] compatible with chunk_doc.spec_sections."""
    marks = list(PAGE.finditer(text))
    if not marks:
        return [(None, "", 0, len(text))]
    out = []  # (no, title, start_pos)
    cur = "__none__"
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        no, title = _header_info(text[m.end():end])
        if no is None:
            if cur == "__none__":
                out.append((None, "front matter", m.start()))
                cur = None
            continue
        if no != cur:
            # start AFTER the page marker, like a heading-style section: the marker of a section's first page then sits at
            # the end of the previous section, where chunk_doc expects it (starting on the marker itself made page_at() miss it)
            out.append((no, title, m.end()))
            cur = no
    if out:
        out[0] = (out[0][0], out[0][1], 0)  # the first section also owns the text before it (keeps the sections tiling the text)
    res = []
    for i, (no, title, start) in enumerate(out):
        end = out[i + 1][2] if i + 1 < len(out) else len(text)
        res.append((no, title, start, end))
    return res
