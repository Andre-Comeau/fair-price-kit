# Architecture: current state and the rework in progress

This document exists because the kit outgrew a single README section. It records what's actually
built, what's a firm design decision waiting on implementation, and what's still genuinely open —
kept separate so a reader doesn't have to guess which is which. Written 2026-09-23, alongside the
first pieces of a larger rework; expect this file to keep changing as the rest lands.

## Where this started
The kit began as a single local tool: `webapp/server.py` bound to `127.0.0.1` only, used by one
person on one machine, with a private companion repo (`fair-price-corpus`) for anything sanitized
from real project documents. That design was deliberately conservative — see the "What this is not"
section that used to be in `webapp/README.md` — because the privacy model for anything more had not
been thought through yet.

## The question that started the rework: could someone else run this?
Two different things were being conflated under "hosting":
1. **GitHub self-run** — someone clones the repo and runs `python webapp/server.py` themselves, on
   their own machine, under their own `ANTHROPIC_API_KEY`. This was already possible and needed
   nothing new; it's still the recommended path for a single user (`webapp/README.md`).
2. **A genuinely shared instance** — one running server, reachable by more than one person, so
   nobody has to install anything. This needed real design work, because the local-only version's
   privacy guarantee ("nothing leaves 127.0.0.1") stops being true the moment the host isn't the
   only caller.

## The two-area concept, and what actually got built
The working design (from the "could someone else run the website" discussion) splits the webapp into:
- **A public area**: analysis against data this repository already publishes openly — the policy
  register, the CanadaBuys award data, the commodity price index. No project-specific or
  caller-specific information is involved, so no caller identity is needed.
- **A private/session area**: anything that touches a caller's own input — pasted text to scan,
  a drafting conversation sent to the host's own `ANTHROPIC_API_KEY`. In a shared instance, this needs
  to know *whose* request it is, both so one caller's inputs and API spend aren't reachable by
  another, and so the host isn't silently paying for and exposing drafting to anyone who finds the URL.

**Built now:**
- `webapp/auth.py`: `resolve_caller()`, a single function that answers "who is this request from?"
  from a per-caller token roster (`webapp/tokens.txt`, gitignored, or `FAIR_PRICE_TOKENS`). Nothing
  else in the webapp knows or depends on *how* that question is answered — swapping the mechanism
  (Cloudflare Access issuing a verified header, an OAuth session, Tailscale-level network trust) means
  changing this one function, not the routes that call it.
- `webapp/server.py`: routes are split by the rule above. `/api/register`, `/api/awards`,
  `/api/commodity-index` and `/api/health` never require a caller. `/api/scan` and `/api/draft`
  require one whenever auth is turned on (`--require-auth` / `FAIR_PRICE_REQUIRE_AUTH=1`) — off by
  default, so the existing local single-user workflow is completely unaffected.
- A **structural safety rail**, not just a convention: the server refuses to bind any host other than
  `127.0.0.1`/`localhost`/`::1` unless auth is both turned on and a token roster actually exists. It
  is not possible to accidentally expose scan/draft to the open internet by passing `--host` without
  also doing the auth setup; the server errors out with the specific missing piece named.

**Not built — deferred, and why:**
- **The dual-bot / private-raw-data-bot + public-analysis-bot split** (the "Raw Source Bot" /
  "wiki bot" idea, from the World Machines reference). This is a real design direction for once
  `fair-price-corpus` is actually wired into a live query path — right now it isn't (`SKILL.md` reads
  it directly as a human-readable file, not through any bot or API this webapp calls). Building the
  dual-bot split before there's a corpus-querying bot to split would be solving a problem that doesn't
  exist yet. The access-control layer above is deliberately built so that when a corpus-querying
  feature does get added, gating it is "add one more `_require_caller()` call", not a rewrite.
- **Cloudflare Access** (or any hosted-identity mechanism) as the real auth backend. The token-roster
  approach (internally "Option A" during design) is what's implemented; it is adequate for a small,
  known set of callers and nothing about its interface needs to change to swap in something stronger
  later — that was the point of isolating it into `resolve_caller()`.
- **Actually deploying a shared instance anywhere.** Nothing here stands up hosting; it makes hosting
  *possible* without an app rewrite, on infrastructure someone chooses later.

## Data categories, and where each one lives
Three different things were being called "data" in earlier discussion, with different rules:
1. **Data needing sanitization before it can be public** — real project documents (specs, drawings,
   change orders). Stays local, goes through `ingestion/RULEBOOK.md`'s stop rules and the
   sensitive-information gate before anything derived from it can leave the workspace. Never
   redistributed as source documents even after sanitization (copyright is separate from privacy —
   see `data/README.md`).
2. **Data that is already public** — CanadaBuys award notices, the StatCan commodity price index,
   any cited open-government dataset. This is the opposite failure mode: over-redacting a contract
   number or vendor name here doesn't add privacy (the government already published it), it just
   makes the row useless as a citable comparable. `gates/sensitive-info-gate.md` now says this
   explicitly — its identifier rules apply to raw project records, not to a file whose provenance is
   an already-public, licensed dataset.
3. **Copyrighted, licensed catalogue data** (e.g. a commercial cost-data product). Out of scope for
   now — the kit doesn't hold or redistribute this. Kept as a category here only so future data
   sources get sorted correctly on arrival rather than lumped in with #1 or #2 by default.

## Open standards adopted
- **OCDS/OC4IDS**: `sources/OCDS-MAPPING.md` maps this kit's award-data schema to the OCDS `Item` and
  `Award` objects (fields verified against the real 1.1.5 release schema, not guessed), and
  `tools/ocds_export.py` exports one award row in that shape. Deliberately partial — no `tender` or
  `contract` section, no real `parties[]`, no minted OCID — see that file for exactly what's missing
  and why. This is a mapping and an export path, not a decision to change the kit's native format.
- **Commodity price indexes**: `data/statcan-ippi-construction.csv` (Statistics Canada IPPI, filtered
  to five construction-relevant commodity groups) is now real, downloaded, cited data — not just a
  register entry pointing at a page. It answers a gap `SKILL.md` already named (inflation-adjusting a
  comparable) that the kit had no data for before. `STATCAN-BCPI` (building-price index, Ottawa area)
  is still register-only, not yet downloaded — the natural next addition in the same shape.

## Open questions this rework did not resolve
Everything in `OPEN-QUESTIONS.md` still stands. Specifically unresolved by this rework:
- Which access-control mechanism a real shared deployment should actually use (waiting on further
  input before committing past the token-roster default).
- Whether/when `fair-price-corpus` gets an actual query path (bot or otherwise) rather than being
  read as a file — the dual-bot design only becomes concretely buildable once that exists.
- Where a shared instance would actually run (no hosting decision has been made; this rework only
  removes the *code-level* blocker to making that decision later).
