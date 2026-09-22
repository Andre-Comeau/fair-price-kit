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

def scan_input(text: str, allow: list = None) -> dict:
    """Run the real scanner on in-memory text. Returns the same category/masked-value shape the
    CLI prints, plus a clean flag, plus each match's (line, start, end) so a caller that already
    holds the real text (the browser tab the operator typed into) can locate the exact span to
    redact -- the server still never sends the unmasked value back.

    allow: plain-text strings the operator has already reviewed and accepted as not sensitive
    (built client-side from a previous scan's offsets; see webapp/README.md). Checked per-request,
    never written anywhere, never shared across requests -- this is not the CLI's persistent
    kb/gate-allow.txt, it only lasts as long as the browser tab remembers it."""
    allow_tuples = [("lit", a.lower()) for a in (allow or []) if a]
    hits = ss.scan_text(text or "", allow=allow_tuples)
    by_cat = {}
    findings = []
    for line_no, cat, masked, start, end in hits:
        findings.append({"line": line_no, "category": cat, "masked": masked, "start": start, "end": end})
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


# The justification template has 7 sections including two tables; a live test run on a modest
# repair-scope, non-competitive scenario used the full previous cap (4000) and was cut off mid-table
# in section 3, before it ever reached the conclusion, documentation list or sources section. Raised
# with headroom -- worst-case cost impact is small (~$0.02 extra at full use, see draft_with_llm's
# ceiling check) next to the cost of a silently truncated draft someone might not notice is cut off.
MAX_OUTPUT_TOKENS = 8000


def api_key_configured() -> bool:
    """Whether ANTHROPIC_API_KEY is set in this environment -- never returns or logs the value
    itself. Used by /api/health so the UI can say up front that drafting is disabled, instead of
    the operator only finding out after filling the whole form and clicking Generate."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# $ per million tokens, Claude Sonnet 5 (confirmed at docs.claude.com/en/docs/about-claude/pricing,
# 2026-09-22). Update this if the model in draft_with_llm's default changes.
PRICING = {
    "claude-sonnet-5": {"input": 2.00, "cache_write_5m": 2.50, "cache_hit": 0.20, "output": 10.00},
}


def estimate_cost_usd(usage: dict, model: str) -> float | None:
    """Compute the real cost of one call from the API's own usage numbers -- not a guess made
    before the call, a calculation from what actually happened."""
    p = PRICING.get(model)
    if not p:
        return None
    cost = (
        usage.get("input_tokens", 0) * p["input"]
        + usage.get("cache_creation_input_tokens", 0) * p["cache_write_5m"]
        + usage.get("cache_read_input_tokens", 0) * p["cache_hit"]
        + usage.get("output_tokens", 0) * p["output"]
    ) / 1_000_000
    return round(cost, 5)


def build_system_blocks() -> list:
    """The fixed context (SKILL.md + the whole register + the template) as a cached system block.
    It's identical on every call regardless of what the operator asked, so it's the one part worth
    caching: after the first call in a 5-minute window, repeat calls pay 10% of input price for
    this whole block instead of full price. Kept separate from build_user_message() so each can be
    tested without a network call."""
    register_csv_text = REGISTER_CSV.read_text(encoding="utf-8") if REGISTER_CSV.is_file() else ""
    skill_text = SKILL_MD.read_text(encoding="utf-8") if SKILL_MD.is_file() else ""
    template_text = TEMPLATE_MD.read_text(encoding="utf-8") if TEMPLATE_MD.is_file() else ""
    return [{
        "type": "text",
        "text": (
            f"{skill_text}\n\n---\n\n"
            f"Register (sources/register.csv), the ONLY source of policy citations:\n{register_csv_text}\n\n---\n\n"
            f"Template to fill:\n{template_text}"
        ),
        "cache_control": {"type": "ephemeral"},
    }]


def build_user_message(inputs: dict) -> str:
    """The small, per-call part -- what actually changes between drafts. Never cached; there's
    nothing to gain caching a few lines that differ every time."""
    fields = "\n".join(f"- {k}: {v}" for k, v in inputs.items() if v)
    return (
        f"Inputs supplied by the operator (mark every one of these figures user-supplied in the output):\n{fields}\n\n"
        f"Follow SKILL.md's Steps exactly. Output only the filled template."
    )


def draft_with_llm(inputs: dict = None, messages: list = None, model: str = "claude-sonnet-5",
                    max_cost_usd: float = 0.25) -> dict:
    """Calls the Anthropic Messages API with the operator's own ANTHROPIC_API_KEY (read from the
    environment only -- never stored, never sent anywhere else). This is the single point in the
    whole webapp where data leaves the machine, and it goes only to the API key's own owner's
    account, same as it would from any AI assistant.

    Two ways to call it:
    - inputs: a fresh first draft, built from the "Inputs to collect" fields.
    - messages: continue an existing conversation (the "messages" list a previous call returned,
      with one more {"role": "user", "content": ...} appended -- the operator's reply to something
      the draft raised, e.g. a gap it flagged). Exactly one of the two must be given.

    Returns {"draft": str, "usage": {...}, "estimated_cost_usd": float, "messages": [...]} -- the
    returned "messages" is the full conversation so far, including the reply just generated; pass
    it straight back in as `messages` (with a new user turn appended) for the next round. Cost is
    computed from the API response's own token counts after the call, not guessed beforehand.
    max_cost_usd is a sanity ceiling on the *estimated pre-call* cost (worst case, assuming no
    cache hit and the full max_tokens output) -- catches a runaway prompt before it's sent, not
    after; a real run typically costs far less, and a longer conversation costs more each round
    since prior turns are resent. It does not touch a budget the account itself enforces."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise DraftError(
            "ANTHROPIC_API_KEY is not set in this environment. Every other feature (scan, register "
            "lookup, award search) works without it; drafting needs it because it is the one step "
            "that requires an LLM. Set it and restart the server to enable drafting."
        )
    if messages:
        conversation = messages
    elif inputs is not None:
        conversation = [{"role": "user", "content": build_user_message(inputs)}]
    else:
        raise DraftError("draft_with_llm needs either inputs (a first draft) or messages (a reply)")

    max_tokens = MAX_OUTPUT_TOKENS
    system_blocks = build_system_blocks()
    p = PRICING.get(model)
    if p:
        worst_case_input_tok = len(system_blocks[0]["text"]) / 4 + sum(len(m.get("content", "")) for m in conversation) / 4
        worst_case = (worst_case_input_tok * p["cache_write_5m"] + max_tokens * p["output"]) / 1_000_000
        if worst_case > max_cost_usd:
            raise DraftError(
                f"refusing to call the API: worst-case estimate ${worst_case:.3f} exceeds the "
                f"${max_cost_usd:.2f} ceiling for this call. Something is unusually large -- check "
                f"the inputs (or how long this conversation has grown) before raising max_cost_usd."
            )
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system_blocks,
        "messages": conversation,
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
        draft_text = "".join(block["text"] for block in data["content"] if block.get("type") == "text")
    except (KeyError, TypeError):
        raise DraftError(f"unexpected API response shape: {data}") from None
    usage = data.get("usage", {})
    updated_messages = conversation + [{"role": "assistant", "content": draft_text}]
    return {
        "draft": draft_text,
        "usage": usage,
        "estimated_cost_usd": estimate_cost_usd(usage, model),
        "messages": updated_messages,
        # data["stop_reason"] == "max_tokens" means the model was still writing when it hit
        # max_tokens and the draft is cut off mid-document, with no error of any kind otherwise --
        # exactly what happened in live testing (cut off mid-table, before the conclusion or sources
        # section). Surfaced explicitly so a truncated draft is never mistaken for a finished one.
        "truncated": data.get("stop_reason") == "max_tokens",
    }
