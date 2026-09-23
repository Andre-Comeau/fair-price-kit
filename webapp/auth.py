"""Caller resolution for the webapp -- the one place "who is this request from?" is decided.

Everything else in the webapp (server.py's route gating) asks this module a yes/no question; nothing
else here knows or cares how the answer was worked out. That's deliberate: the mechanism below (a
per-caller token roster, checked in constant time) is one legitimate way to answer "who is this
caller", not the only one this webapp will ever use. When a hosted deployment wants something
stronger (Cloudflare Access issuing a verified identity header, an OAuth session, network-level trust
via Tailscale), only resolve_caller() needs to change -- server.py's calls to it, and everything that
depends on the caller_id/reason it returns, stay the same.

This module has no opinion about *whether* auth is required at all -- that's auth_required(), read
from the environment, and it defaults to off: the local single-user workflow (webapp/README.md) never
needed a caller identity, and nothing about this module changes that unless FAIR_PRICE_REQUIRE_AUTH
is explicitly set. See ARCHITECTURE.md for why this exists now: it's the piece a hosted, shared
instance needs that a 127.0.0.1-only instance never did, so a caller's own inputs (a pasted paragraph
for scanning, an LLM drafting call billed to the host's own API key) aren't reachable by anyone who
happens to find the URL.
"""
import hmac
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKENS_FILE = ROOT / "tokens.txt"  # gitignored -- see tokens.txt.example


def auth_required() -> bool:
    """Whether routes that touch a caller's own inputs should refuse an unresolved caller. Off by
    default -- sets to on by giving the server --require-auth or FAIR_PRICE_REQUIRE_AUTH=1, which is
    also what refuses a non-loopback --host without a token roster configured (see server.py)."""
    return os.environ.get("FAIR_PRICE_REQUIRE_AUTH", "").strip().lower() in ("1", "true", "yes")


def _load_roster() -> dict:
    """token -> label. Reads webapp/tokens.txt (one 'token,label' per line, '#' comments and blank
    lines skipped) and the FAIR_PRICE_TOKENS environment variable (comma-separated 'token:label'
    pairs, for a deployment that would rather not keep a token file on disk) -- both are merged, an
    empty roster is not an error (it just means every caller is unresolved). Read fresh on every
    call: this is a handful of lines at most, and re-reading means an operator can edit tokens.txt
    (or the environment, restarting the process) without the roster going stale mid-session for a
    reason that isn't obvious from the outside."""
    roster = {}
    if TOKENS_FILE.is_file():
        for line in TOKENS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            token, _, label = line.partition(",")
            token, label = token.strip(), label.strip()
            if token:
                roster[token] = label or "unlabelled"
    for pair in os.environ.get("FAIR_PRICE_TOKENS", "").split(","):
        token, _, label = pair.strip().partition(":")
        token, label = token.strip(), label.strip()
        if token:
            roster[token] = label or "unlabelled"
    return roster


def roster_configured() -> bool:
    """Whether any token is configured at all -- server.py uses this to refuse starting on a
    non-loopback host with --require-auth set but nothing in the roster (every caller would be
    silently unresolved, which looks like it's working until the first real request isn't local)."""
    return bool(_load_roster())


def _extract_token(headers) -> str:
    """headers: an email.message.Message-like object (BaseHTTPRequestHandler.headers) or a plain
    dict -- both support .get(name, default) case-insensitively for the former, so this works
    against either without server.py needing to know which. Accepts 'Authorization: Bearer <token>'
    (preferred) or 'X-Fair-Price-Token: <token>' (simpler for a manual curl/script caller)."""
    auth = (headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (headers.get("X-Fair-Price-Token") or "").strip()


def resolve_caller(headers) -> tuple:
    """Returns (caller_id, reason). caller_id is the roster label (truthy) if the request's token
    matches a real entry, else None. reason is a short, safe-to-return-to-the-client string when
    caller_id is None ('no token supplied' / 'token not recognized'), never included when resolution
    succeeded. Comparison is constant-time (hmac.compare_digest) against every roster entry -- this
    is a handful of tokens, not a large keyspace, so timing differences between 'checked 1 token' and
    'checked all of them' are not a realistic concern, but comparing the same way regardless of
    roster size costs nothing and removes the question."""
    token = _extract_token(headers)
    if not token:
        return None, "no token supplied"
    roster = _load_roster()
    for candidate, label in roster.items():
        if hmac.compare_digest(token, candidate):
            return label, None
    return None, "token not recognized"
