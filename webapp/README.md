# webapp — a local UI for people without an AI assistant

A human-facing front end for the parts of `fair-price-kit` that don't need one. Built because someone
using this kit shouldn't have to install Claude Code or run Python from a terminal just to check
whether a paragraph is safe to share, or to look up what the register already says.

## Run it
```
python webapp/server.py
```
Then open `http://127.0.0.1:8420`. No `pip install` — stdlib only, same as every other tool here, so it
runs on a locked-down machine that can't reach a package index (see `OPEN-QUESTIONS.md` #12, which is
exactly this constraint).

## What stays local, and what doesn't
The server binds to `127.0.0.1` only — hardcoded, not a flag, so it is never reachable from another
machine. Four of the five things it does never touch a network:

- **Scan** (`/api/scan`) — the real `tools/scan_sensitive.py` logic, called in-process on whatever you
  type. Nothing is written to disk.
- **Register lookup** (`/api/register`) — reads `sources/register.csv` directly.
- **Award search** (`/api/awards`) — reads `data/canadabuys-awards-ncr-construction.csv` directly,
  excludes flagged rows by default.
- **Citation check** (`/api/validate`, and automatically on every `/api/draft` result) — checks every
  register-id-shaped token in a draft against the real register, and flags any that aren't there.

**Drafting** (`/api/draft`) is the one exception: it calls the Anthropic API, using
`ANTHROPIC_API_KEY` read from your own environment, to do the judgment-requiring step `SKILL.md`
describes. That is the same trust boundary as using any AI assistant on this kit directly — your
inputs go to the API key's own account, nowhere else. Set the key before starting the server:
```
export ANTHROPIC_API_KEY=sk-ant-...   # or the Windows/PowerShell equivalent
python webapp/server.py
```
Without it, every other feature still works; drafting returns a clear error instead of failing
silently or crashing.

## What a draft actually costs
`SKILL.md` + the whole register + the template (~4,600 tokens) go into a cached `system` block on
every call, since they're identical regardless of what you ask — after the first call in a 5-minute
window, repeat calls pay 10% of input price for that block instead of full price. On Claude Sonnet 5
pricing ($2/MTok in, $10/MTok out, $0.20/MTok on a cache hit), that's roughly **$0.02 for the first
draft, ~$0.013 for each one after it** in the same 5-minute window. The UI shows the real cost from
the API's own usage numbers after every call, plus a running total for that browser tab — not an
estimate, the actual figure. `draft_with_llm()` also refuses to send a request at all if a rough
worst-case estimate exceeds `max_cost_usd` (default $0.25), as a guard against something unusually
large, not a budget tracker — the account's own billing is the real limit.

## The citation check is a safety net, not a guarantee
`validate_citations()` in `engine.py` flags any all-caps hyphenated token that looks like a register
id (`TBS-DMP-4.3.1`, `CANADABUYS-AWARD-DATA`) but isn't actually one. It's a heuristic on shape, not
meaning — it can miss an unusually-written citation and can flag an unrelated token. It narrows what a
human checks before trusting a draft; it doesn't replace reading `sources/register.csv`.

## What this is not
- Not a hosted service, and not designed to become one without redesigning the privacy model first
  (see the "should we build a website" discussion in the kit's history — the short version: a
  *hosted* multi-tenant version means someone else's procurement data crosses a network to
  infrastructure you control, which reopens `OPEN-QUESTIONS.md` #6-#8 in their hardest form; this
  local-only version doesn't, because nothing here changes where the data goes versus using an AI
  assistant directly).
- Not a UI for the ingestion pipeline (`ingestion/`) — that still runs via the CLI tools or an AI
  assistant. Adding it here is future work, not started.
- Not a replacement for the sensitive-information gate's human review step — a clean scan is not a
  guarantee, exactly as the CLI tool itself says.

## Files
- `server.py` — stdlib `http.server`, routes only, no logic of its own.
- `engine.py` — the actual functions (scan, register, award search, citation check, drafting).
  Imported and tested directly by `tools/test/test_webapp.py` without starting a server.
- `static/` — plain HTML/CSS/vanilla JS, no build step, no CDN dependency.
