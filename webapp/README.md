# webapp — a local UI for people without an AI assistant

A human-facing front end for the parts of `fair-price-kit` that don't need one. Built because someone
using this kit shouldn't have to install Claude Code or run Python from a terminal just to check
whether a paragraph is safe to share, or to look up what the register already says.

## Run it
Double-click `webapp/run.bat`. It starts the server and opens your browser to it automatically — no
terminal typing, no address to remember. The window it opens stays open while the server runs (closing
it, or `Ctrl+C` inside it, stops the server); if something goes wrong on startup, the window stays open
so you can read the error instead of it flashing shut.

Or run it yourself the same way any of the other tools here run:
```
python webapp/server.py
```
Then open `http://127.0.0.1:8420` (this also opens on its own, the same as the launcher). No
`pip install` — stdlib only, same as every other tool here, so it runs on a locked-down machine that
can't reach a package index (see `OPEN-QUESTIONS.md` #12, which is exactly this constraint).

If port 8420 is already taken (most often because the webapp is already running in another window),
the server says so plainly instead of a raw crash, and suggests `--port` to pick a different one. The
server also releases the port immediately on `Ctrl+C` and refuses to let a second instance quietly
share it (Windows in particular allows that by default, which can leave an old process answering
some requests after what looked like a clean restart) — if a restart ever doesn't pick up a change,
that's the first thing to suspect: check nothing from an earlier window is still running.

## What stays local, and what doesn't
The server binds to `127.0.0.1` only — hardcoded, not a flag, so it is never reachable from another
machine. Four of the five things it does never touch a network:

- **Scan** (`/api/scan`) — the real `tools/scan_sensitive.py` logic, called in-process on whatever you
  type. Nothing is written to disk. Each flagged item gets two buttons: **Redact** replaces the exact
  matched text in the field with a `[CATEGORY]` placeholder, in place; **Keep — not sensitive** records
  that exact text (read from your own field, never from the server's masked preview) as reviewed and
  accepted, so it won't be flagged again this browser session. Neither is written anywhere — this is
  the CLI's `kb/gate-allow.txt` reviewed-exceptions idea (`gates/sensitive-info-gate.md`), scoped to
  one tab instead of a file, since the webapp has no per-project folder to keep one in.
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
silently or crashing. The page itself says so too — if the server can't see a key, a banner appears
over the Draft section as soon as the page loads (`/api/health` reports `draft_enabled`), so you find
out before filling in the whole form rather than after clicking Generate.

Any other bug in a route handler — not just a missing key — comes back to the browser as a normal,
readable error instead of a hung or reset connection. A stuck spinner with nothing happening used to
be indistinguishable from "the server isn't running"; now every route always returns something.

## Replying to a draft
A draft can raise something worth answering — a gap it flagged, a figure it wants confirmed. After
a draft appears, a text box lets you reply; that reply continues the *same* conversation (the
API's own `messages` array, round-tripped through the browser tab) rather than starting a fresh,
context-free one, so the model sees what it said before, not just your new message in isolation.
Each reply is its own `/api/draft` call — cost and citations are reported per turn, and each turn
resends the whole conversation so far, so a long back-and-forth costs more per turn than the first
draft did (still cached on the fixed context; only the growing conversation is uncached).

## What a draft actually costs
`SKILL.md` + the whole register + the template (~4,600 tokens) go into a cached `system` block on
every call, since they're identical regardless of what you ask — after the first call in a 5-minute
window, repeat calls pay 10% of input price for that block instead of full price. On Claude Sonnet 5
pricing ($2/MTok in, $10/MTok out, $0.20/MTok on a cache hit), a full draft has run **around $0.05–0.10**
in practice — it varies with how much the model has to write to fill all 7 template sections, which
is most of the cost (output is 5x the price of input per token, and cached input is 1/10 of that
again). The UI shows the real cost from the API's own usage numbers after every call, plus a running
total for that browser tab — not an estimate, the actual figure; trust that over any number here.
`draft_with_llm()` also refuses to send a request at all if a rough worst-case estimate exceeds
`max_cost_usd` (default $0.25), as a guard against something unusually large, not a budget tracker —
the account's own billing is the real limit.

`max_tokens` (the output cap) is `engine.MAX_OUTPUT_TOKENS`, deliberately generous (8000): a lower
cap doesn't save real money if the draft doesn't need that many tokens, but it can silently cut a
draft off mid-section with no error, which is worse than the small worst-case-estimate cost it buys.
If a draft is still cut off (a very long requirement, a long reply chain), the page says so plainly —
a red "Cut off before finishing" banner, from the API's own `stop_reason` field, not a guess based on
token counts — instead of a truncated document being mistaken for a complete one.

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
- `run.bat` — double-click launcher (Windows): starts `server.py` and opens the browser, stays open
  on error.
- `server.py` — stdlib `http.server`, routes only, no logic of its own. Every route is wrapped so an
  unhandled exception becomes a clean JSON 500, not a dropped connection.
- `engine.py` — the actual functions (scan, register, award search, citation check, drafting).
  Imported and tested directly by `tools/test/test_webapp.py` without starting a server.
  `tools/test/test_webapp_server.py` tests the HTTP layer itself (routing, malformed input, the
  catch-all) against a real server on a throwaway port.
- `static/` — plain HTML/CSS/vanilla JS, no build step, no CDN dependency.
