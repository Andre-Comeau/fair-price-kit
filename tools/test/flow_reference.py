#!/usr/bin/env python3
"""Reference implementation of the Power Automate flows (ingestion/POWER-AUTOMATE.md).

Purpose: the flows cannot be run here, so this script follows the flows' EXACT algorithm
(same splits, same page counting, same JSON assembly, no regex) on synthetic fixtures. Build the
flows, run them on the same fixtures, and compare their output with `flow-fixtures/expected.json`.
It is a development/test aid: it is not needed on the target computer.

Usage:
  python tools/test/flow_reference.py selftest           # run fixtures, check invariants, compare to expected.json
  python tools/test/flow_reference.py write-expected     # (re)write expected.json from the fixtures
  python tools/test/flow_reference.py gate FILE MAPPING.csv   # Flow 1 checks on one file
"""
import csv
import json
import sys
from pathlib import Path

# run from the kit folder; falls back to the script location
HERE = Path("tools/test") if Path("tools/test").is_dir() else Path(__file__).resolve().parent
FIX = HERE / "flow-fixtures"
EXPECTED = FIX / "expected.json"  # {chunk filename: content, "INDEX.md": ..., "index.json": ...}
NL = "\n"  # decodeUriComponent('%0A')
MARKERS = ["protected a", "protected b", "protected c", "top secret", "secret", "confidential",
           "cabinet confidence", "protégé", "très secret", "confidentiel", "srcl"]
RESERVED = {"id", "doc_type", "doc_id", "doc_title", "section", "sheet", "chunk_title", "division",
            "division_name", "masterformat_edition", "pages", "chars", "sanitization"}
FIXED_TIME = "2000-01-01T00:00:00Z"  # the real flow uses utcNow(); ignore this field when comparing


# ---- helpers mirroring expressions -------------------------------------------------------------
def q(s):
    """JSON-quote: substring(string(createArray(x)), 1, sub(length(string(createArray(x))), 2))"""
    return json.dumps(s, ensure_ascii=False, separators=(",", ":"))[0:]


def count_markers(s):
    """sub(length(split(s, '<!-- page ')), 1)"""
    return len(s.split("<!-- page ")) - 1


def norm(text):
    """replace(text, decodeUriComponent('%0D%0A'), decodeUriComponent('%0A'))"""
    return text.replace("\r\n", "\n")


def fm_line(k, v_json):
    return f"{k}: {v_json}"


# ---- Flow 1: gate ------------------------------------------------------------------------------
def gate(text, mapping_rows):
    t = norm(text)
    tl = t.lower()
    leaks = [r["placeholder"] for r in mapping_rows
             if len(r.get("real_value") or "") > 3 and (r["real_value"]).lower() in tl]
    marks = [m for m in MARKERS if m in tl]
    channels = [c for c in ("@", "http", "www.") if c in tl]
    pending = "[party-?" in tl
    return {"known_value_leaks": leaks, "marking_words": marks, "contact_chars": channels,
            "unresolved_placeholder": pending,
            "pass": not (leaks or marks or channels or pending)}


# ---- Flow 2: chunk -----------------------------------------------------------------------------
def build_fm(header_lines, fields):
    """header lines first, generated fields after (generated keys win when parsed: later key overrides)."""
    lines = list(header_lines) + [fm_line(k, v) for k, v in fields]
    return "---" + NL + NL.join(lines) + NL + "---" + NL


def split_header(text):
    """Optional metadata block at the top: '---' lines. Returns (header_lines, body)."""
    t2 = NL + text
    parts = t2.split(NL + "---" + NL)
    if text.startswith("---" + NL) and len(parts) >= 3:
        header = [ln for ln in parts[1].split(NL) if ln.strip() and ln.split(":", 1)[0].strip() not in RESERVED]
        body = (NL + "---" + NL).join(parts[2:])
        return header, body
    return [], text


def doc_type_of(name):
    p = name.lower()
    for pre, t in (("spec-", "spec"), ("dwg-", "drawing"), ("ccn-", "ccn"), ("co-", "co"), ("ci-", "ci"),
                   ("cd-", "cd"), ("si-", "si"), ("ea-", "ea")):
        if p.startswith(pre):
            return t
    return "other"


def chunk_file(name, raw_text):
    """Return {filename: content}. name like 'spec-vol1.md'."""
    stem = name.rsplit(".", 1)[0]
    doc_id = stem.upper()
    dtype = doc_type_of(name)
    text = norm(raw_text)
    out = {}
    if dtype == "spec":
        items = (NL + text).split(NL + "SECTION ")
        counter = count_markers(items[0])
        pre = items[0].strip()
        pend = counter - (1 if pre.endswith("-->") else 0)
        if pre.endswith("-->"):
            pre = NL.join(pre.split(NL)[:-1])
        if pre:
            cid = f"{stem.lower()}__front"
            out[cid + ".md"] = build_fm([], [("id", q(cid)), ("doc_type", q("spec")), ("doc_id", q(doc_id)),
                                             ("doc_title", q("")), ("chunk_title", q("front matter")),
                                             ("pages", f"[1,{max(pend, 1)}]"), ("chars", str(len(pre))),
                                             ("sanitization", q("approved"))]) + NL + pre + NL
        for item in items[1:]:
            heading = item.split(NL)[0]
            h = heading.split(" - ")
            sec = h[0].strip()
            title = " - ".join(h[1:]).strip()
            digits = sec.replace(" ", "")
            division = digits[0:2]
            markers = count_markers(item)
            tail = 1 if item.strip().endswith("-->") else 0
            start = max(counter, 1)
            end = counter + markers - tail
            counter += markers
            lines = item.strip().split(NL)
            if tail:  # drop the last line: it is the next chunk's page marker.  take(split(..), sub(length(split(..)), 1))
                lines = lines[:-1]
            body = "SECTION " + NL.join(lines)
            cid = f"{stem.lower()}__{sec.replace(' ', '-')}"
            out[cid + ".md"] = build_fm([], [("id", q(cid)), ("doc_type", q("spec")), ("doc_id", q(doc_id)),
                                             ("doc_title", q("")), ("section", q(sec)), ("chunk_title", q(title)),
                                             ("division", q(division)), ("pages", f"[{start},{max(end, start)}]"),
                                             ("chars", str(len(body))), ("sanitization", q("approved"))]) + NL + body + NL
    elif dtype == "drawing":
        items = text.split("<!-- page ")
        for item in items[1:]:
            page = item.split(" -->")[0].strip()
            body = NL.join(item.split(NL)[1:]).strip()
            padded = ("000" + page)[len(page):len(page) + 3]
            cid = f"{stem.lower()}__pg{padded}"
            out[cid + ".md"] = build_fm([], [("id", q(cid)), ("doc_type", q("drawing")), ("doc_id", q(doc_id)),
                                             ("doc_title", q("")), ("chunk_title", q(f"Sheet page {page}")),
                                             ("pages", f"[{page},{page}]"), ("chars", str(len(body))),
                                             ("sanitization", q("approved"))]) + NL + body + NL
    else:
        header, body = split_header(text)
        body = body.strip()
        cid = f"{stem.lower()}__all"
        out[cid + ".md"] = build_fm(header, [("id", q(cid)), ("doc_type", q(dtype)), ("doc_id", q(doc_id)),
                                             ("doc_title", q("")), ("chunk_title", q("")),
                                             ("pages", f"[1,{max(count_markers(body), 1)}]"), ("chars", str(len(body))),
                                             ("sanitization", q("approved"))]) + NL + body + NL
    return out


# ---- Flow 3: index -----------------------------------------------------------------------------
def parse_chunk(content):
    """front matter lines 'key: json' -> object, via:  '"'+key+'":'+value  joined, wrapped in { }"""
    parts = (NL + content).split(NL + "---" + NL)
    header = [ln for ln in parts[1].split(NL) if ln.strip()]
    kv = ['"' + ln[:ln.index(": ")] + '":' + ln[ln.index(": ") + 2:] for ln in header]
    return json.loads("{" + ",".join(kv) + "}")


def build_index(chunk_files, mapping_rows=None):
    """Flow 3. Each chunk is re-checked against the (possibly grown) mapping table; a leaking chunk is excluded."""
    chunks, excluded = [], []
    for name in sorted(chunk_files):
        content = chunk_files[name]
        o = parse_chunk(content)
        if o.get("sanitization") != "approved":
            continue
        if mapping_rows:
            leaks = gate(content, mapping_rows)["known_value_leaks"]
            if leaks:
                excluded.append(f"{name}: known-value leak ({', '.join(leaks)})")
                continue
        o["path"] = "chunks/" + name
        chunks.append(o)
    # index.json: compact JSON (flow: string(body('approved')) inside a concat); "generated" is utcNow() in the flow
    idx = {"schema": "kb-index/1", "generated": FIXED_TIME, "chunk_count": len(chunks), "chunks": chunks}
    rows = ["# Knowledge-base index", "",
            "Read this file first. Then open only the chunks you need.", "",
            f"{len(chunks)} chunks.", "",
            "| id | type | section/sheet | title | pages | amount |", "|---|---|---|---|---|---|"]
    for c in chunks:
        pg = c.get("pages", [])
        pages = str(pg[0]) if len(pg) == 2 and pg[0] == pg[1] else "-".join(str(x) for x in pg)
        rows.append("| {} | {} | {} | {} | {} | {} |".format(
            c["id"], c["doc_type"], c.get("section") or c.get("sheet") or "",
            (c.get("chunk_title") or c.get("doc_title") or "").replace("|", "/"), pages, c.get("amount", "")))
    if excluded:
        rows += ["", "## Excluded (fix and rebuild)", ""] + ["- " + e for e in excluded]
    return json.dumps(idx, indent=1, ensure_ascii=False), NL.join(rows) + NL


# ---- driver ------------------------------------------------------------------------------------
def run_fixtures():
    files = {}
    # fixtures are flat: spec-/dwg-/co- files are the "approved" set; gate-*.md feed the gate tests
    for name in ("spec-vol1.md", "dwg-arch.md", "co-007.md"):
        files.update(chunk_file(name, (FIX / name).read_text(encoding="utf-8")))
    idx_json, idx_md = build_index(files)
    return files, idx_json, idx_md


def write_expected():
    files, idx_json, idx_md = run_fixtures()
    data = dict(files)
    data["INDEX.md"], data["index.json"] = idx_md, idx_json
    with open(EXPECTED, "w", encoding="utf-8", newline=NL) as f:
        json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=True)
    print(f"wrote expected.json ({len(files)} chunks + INDEX.md + index.json)")


def selftest():
    bad = []
    files, idx_json, idx_md = run_fixtures()
    # invariants
    def chunk(n):
        return parse_chunk(files[n])
    s1, s2 = chunk("spec-vol1__03-30-00.md"), chunk("spec-vol1__05-12-00.md")
    if s1["pages"] != [2, 2]:
        bad.append(("03 30 00 pages", s1["pages"]))
    if s2["pages"] != [3, 4]:
        bad.append(("05 12 00 pages", s2["pages"]))
    if "See SECTION 05 12 00" not in files["spec-vol1__03-30-00.md"]:
        bad.append(("mid-line SECTION reference must not split", None))
    if len([n for n in files if n.startswith("spec-vol1__")]) != 3:
        bad.append(("spec chunk count (front + 2 sections)", len(files)))
    if [chunk(n)["pages"] for n in sorted(files) if n.startswith("dwg-arch__")] != [[1, 1], [2, 2], [3, 3]]:
        bad.append(("drawing pages", None))
    co = chunk("co-007__all.md")
    if co["sanitization"] != "approved" or co["id"] != "co-007__all":
        bad.append(("header spoofing not overridden", co))
    if co["amount"] != 11500 or co["related"][0]["doc"] != "CCN-012":
        bad.append(("change metadata", co))
    # text integrity: every chunk body is an exact substring of its source (order preserved)
    src = norm((FIX / "spec-vol1.md").read_text(encoding="utf-8"))
    for n in ("spec-vol1__03-30-00.md", "spec-vol1__05-12-00.md"):
        body = (NL + "---" + NL).join(("\n" + files[n]).split(NL + "---" + NL)[2:]).strip()
        if body not in src:
            bad.append(("chunk text not verbatim", n))
    # gates
    rows = list(csv.DictReader((FIX / "mapping.csv").open(encoding="utf-8")))
    g = gate((FIX / "gate-leaky.md").read_text(encoding="utf-8"), rows)
    if g["pass"] or set(g["known_value_leaks"]) != {"[SUB-MECH-1]", "[PERSON-CM-PM-1]"} or not g["unresolved_placeholder"] \
            or "protected b" not in g["marking_words"] or "@" not in g["contact_chars"]:
        bad.append(("leaky gate", g))
    g2 = gate((FIX / "gate-clean.md").read_text(encoding="utf-8"), rows)
    if not g2["pass"]:
        bad.append(("clean gate must pass", g2))
    # index re-check: a chunk that contains a mapped real value (added to the mapping later) is excluded
    leaky_chunk = build_fm([], [("id", q("x__all")), ("doc_type", q("co")), ("doc_id", q("X")), ("doc_title", q("")),
                               ("chunk_title", q("")), ("pages", "[1,1]"), ("chars", "10"),
                               ("sanitization", q("approved"))]) + NL + "Paid to Contoso Concrete." + NL
    _, md_ex = build_index({"x__all.md": leaky_chunk}, rows)
    if "known-value leak ([SUB-CONCRETE-1])" not in md_ex or "x__all |" in md_ex:
        bad.append(("index must exclude a chunk containing a mapped value", md_ex))
    g3 = gate("Ab is short and must not trip anything", rows)
    if not g3["pass"]:
        bad.append(("short mapping value ignored", g3))
    # CRLF input gives identical chunks
    crlf = (FIX / "spec-vol1.md").read_text(encoding="utf-8").replace("\n", "\r\n")
    if chunk_file("spec-vol1.md", crlf) != {k: v for k, v in files.items() if k.startswith("spec-vol1__")}:
        bad.append(("CRLF handling", None))
    # compare to expected.json
    if EXPECTED.exists():
        exp = json.loads(EXPECTED.read_text(encoding="utf-8"))
        got = dict(files)
        got["INDEX.md"], got["index.json"] = idx_md, idx_json
        for n in sorted(set(exp) | set(got)):
            if exp.get(n) != got.get(n):
                bad.append(("differs from expected.json", n))
    else:
        bad.append(("expected.json missing (run write-expected)", None))
    if bad:
        for b in bad:
            print("FAIL", b)
        return 1
    print(f"flow reference selftest OK ({len(files)} chunks, gates, index)")
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "selftest":
        return selftest()
    if argv[0] == "write-expected":
        write_expected()
        return 0
    if argv[0] == "gate" and len(argv) == 3:
        rows = list(csv.DictReader(open(argv[2], encoding="utf-8")))
        g = gate(Path(argv[1]).read_text(encoding="utf-8"), rows)
        print(json.dumps(g, indent=1))
        return 0 if g["pass"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
