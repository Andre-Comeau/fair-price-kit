"""The deterministic engine behind webapp/server.py -- no network, no LLM, stdlib only.

Kept separate from server.py so it can be imported and tested directly (tools/test/test_webapp.py)
without starting an HTTP server. server.py wires these functions to routes; nothing here knows
about HTTP. Only draft_with_llm() in this module talks to a network, and only when called.
"""
import csv
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import scan_sensitive as ss  # noqa: E402

REGISTER_CSV = ROOT / "sources" / "register.csv"
AWARDS_CSV = ROOT / "data" / "canadabuys-awards-ncr-construction.csv"
SKILL_MD = ROOT / "SKILL.md"
TEMPLATE_MD = ROOT / "templates" / "justification-template.md"

ID_LIKE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9.]+)+\b")  # matches TBS-DMP-4.3.1, CANADABUYS-AWARD-DATA, OPSS-127, ...


# ---------- sensitive-information gate (wraps tools/scan_sensitive.py, no file I/O) ----------

def scan_input(text: str) -> dict:
    """Run the real scanner on in-memory text. Returns the same category/masked-value shape the
    CLI prints, plus a clean flag. This is the identical logic SKILL.md requires running before
    anything is used or shared -- just called in-process instead of via subprocess."""
    hits = ss.scan_text(text or "")
    by_cat = {}
    findings = []
    for line_no, cat, masked in hits:
        findings.append({"line": line_no, "category": cat, "masked": masked})
        by_cat[cat] = by_cat.get(cat, 0) + 1
    return {"clean": not hits, "count": len(hits), "by_category": by_cat, "findings": findings}


# ---------- register lookup ----------

def load_register() -> list:
    if not REGISTER_CSV.is_file():
        return []
    with REGISTER_CSV.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def register_ids() -> set:
    return {row["id"] for row in load_register() if row.get("id")}


# ---------- public award data lookup ----------

def load_awards() -> list:
    if not AWARDS_CSV.is_file():
        return []
    with AWARDS_CSV.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def search_awards(query: str = "", unflagged_only: bool = True, competitive_only: bool = False, limit: int = 25) -> list:
    """Search the award data by a plain-text match against title/description fields. Mirrors the
    rules SKILL.md states: unflagged rows only by default, and flags shown explicitly otherwise so
    a flagged row is never silently presented as a comparable."""
    rows = load_awards()
    q = query.strip().lower()
    out = []
    for r in rows:
        if unflagged_only and r.get("quality_flags"):
            continue
        if competitive_only and r.get("competitive") != "yes":
            continue
        if q:
            haystack = " ".join([r.get("title", ""), r.get("unspsc_description", "")]).lower()
            if q not in haystack:
                continue
        out.append(r)
        if len(out) >= limit:
            break
    return out


# ---------- citation check on a draft (heuristic, not a guarantee -- see webapp/README.md) ----------

def validate_citations(draft_text: str) -> dict:
    """Flag any ALL-CAPS hyphenated token in a draft that looks like a register id but is not
    actually in sources/register.csv -- catches a fabricated or misremembered citation before a
    human reads the draft as trustworthy. Heuristic: matches the register's own id shape, so it
    can both miss a citation written unusually and flag an unrelated all-caps token; it narrows
    what a human checks, it does not replace checking sources/register.csv directly."""
    known = register_ids()
    cited = sorted(set(ID_LIKE.findall(draft_text or "")))
    used = [c for c in cited if c in known]
    unknown = [c for c in cited if c not in known]
    return {"used": used, "unknown": unknown, "ok": not unknown}


# ---------- drafting (the one function that reaches the network) ----------

class DraftError(Exception):
    pass


def build_prompt(inputs: dict) -> str:
    register_csv_text = REGISTER_CSV.read_text(encoding="utf-8") if REGISTER_CSV.is_file() else ""
    skill_text = SKILL_MD.read_text(encoding="utf-8") if SKILL_MD.is_file() else ""
    template_text = TEMPLATE_MD.read_text(encoding="utf-8") if TEMPLATE_MD.is_file() else ""
    fields = "\n".join(f"- {k}: {v}" for k, v in inputs.items() if v)
    return (
        f"{skill_text}\n\n---\n\n"
        f"Register (sources/register.csv), the ONLY source of policy citations:\n{register_csv_text}\n\n---\n\n"
        f"Template to fill:\n{template_text}\n\n---\n\n"
        f"Inputs supplied by the operator (mark every one of these figures user-supplied in the output):\n{fields}\n\n"
        f"Follow SKILL.md's Steps exactly. Output only the filled template."
    )


def draft_with_llm(inputs: dict, model: str = "claude-sonnet-5") -> str:
    """Calls the Anthropic Messages API with the operator's own ANTHROPIC_API_KEY (read from the
    environment only -- never stored, never sent anywhere else). This is the single point in the
    whole webapp where data leaves the machine, and it goes only to the API key's own owner's
    account, same as it would from any AI assistant."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise DraftError(
            "ANTHROPIC_API_KEY is not set in this environment. Every other feature (scan, register "
            "lookup, award search) works without it; drafting needs it because it is the one step "
            "that requires an LLM. Set it and restart the server to enable drafting."
        )
    prompt = build_prompt(inputs)
    body = json.dumps({
        "model": model,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise DraftError(f"Anthropic API error {e.code}: {e.read().decode('utf-8', 'replace')[:500]}") from None
    except urllib.error.URLError as e:
        raise DraftError(f"could not reach the Anthropic API: {e.reason}") from None
    try:
        return "".join(block["text"] for block in data["content"] if block.get("type") == "text")
    except (KeyError, TypeError):
        raise DraftError(f"unexpected API response shape: {data}") from None
