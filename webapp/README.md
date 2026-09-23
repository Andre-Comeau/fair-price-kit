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

This default is exactly what it always was: local only, single user, no token needed for anything.
`--host` and `--require-auth` exist for someone running a genuinely shared instance — read
`ARCHITECTURE.md` before using them; they're covered in "Running it for more than one person" below,
not part of the default path.

If port 8420 is already taken (most often because the webapp is already running in another window),
the server says so plainly instead of a raw crash, and suggests `--port` to pick a different one. The
server also releases the port immediately on `Ctrl+C` and refuses to let a second instance quietly
share it (Windows in particular allows that by default, which can leave an old process answering
some requests after what looked like a clean restart) — if a restart ever doesn't pick up a change,
that's the first thing to suspect: check nothing from an earlier window is still running.

## What stays local, and what doesn't
The server binds to `127.0.0.1` by default — nothing reachable from another machine unless you
explicitly pass `--host` (see "Running it for more than one person" below). Five of the six things it
does never touch a network:

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
- **Commodity price index** (`/api/commodity-index`) — reads `data/statcan-ippi-construction.csv`
  directly; search a product, then compute an inflation-adjustment factor between two months.
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

## Running it for more than one person
Everything above describes the default: one person, one machine, `127.0.0.1`, no token needed
anywhere. That default doesn't change just because these flags exist.

`--host 0.0.0.0` (or any other non-loopback address) makes the server reachable from other machines.
Scan sends whatever you paste to the server process; draft spends the server's own
`ANTHROPIC_API_KEY`. On a shared instance, both need to know whose request they're handling — so the
server refuses to start on a non-loopback host at all unless `--require-auth` is also given **and**
at least one token is configured (copy `webapp/tokens.txt.example` to `webapp/tokens.txt` and add a
real one, or set `FAIR_PRICE_TOKENS`). Register lookup, award search, the commodity index and
`/api/health` never need a token — they only ever read data this repository already publishes openly
(`gates/sensitive-info-gate.md`'s scope note explains why that's fine).

```
python webapp/server.py --host 0.0.0.0 --require-auth
```
A caller without a valid token gets a plain 401 from `/api/scan` and `/api/draft`; every other route
answers normally. See `webapp/auth.py` for exactly how a token is checked, and `ARCHITECTURE.md` for
why this exists and what it deliberately does not attempt yet (no real hosted-identity provider, no
per-caller rate limiting, no dual-bot corpus split — none of that is built).

## The policy register is not a step you complete
Earlier versions of this page had "Policy register" as a numbered section between the intake form and
the award data, the same shape as the steps you actually do fill in. That was a design mistake: the
register isn't something the operator does anything with, but a numbered step in a workflow reads as
one — it can look like the policies were consulted by a person as part of preparing the justification,
when what actually happens is the whole register goes into the model's context on every draft
(`SKILL.md`) and gets applied there, automatically, every time, regardless of whether anyone opened
this page's table at all.

The register is still here — collapsed, unnumbered, at the bottom, labelled "Reference" — for the one
thing a human plausibly does want it for: looking something up, or double-checking a citation the
draft made (which is also checked automatically; see the citations line under each draft). It is
never a step, and the interface doesn't imply it was consulted just because it's present.

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

## Drafting without an API key (Microsoft Copilot or similar)
`/api/draft` needs `ANTHROPIC_API_KEY` because it calls Anthropic's Messages API directly. If your
organization gives you Microsoft 365 Copilot instead — chat in Word, Teams or the Copilot web app —
that's a different kind of AI access: it has no general-purpose completions API this webapp can call
the way it calls Anthropic's, so there's nothing for `/api/draft` to point at. The "Or draft without
an API key" section under Draft is for exactly this case, and works with any interactive AI chat your
organization allows, not Copilot specifically.

It does the same job a different way:
1. **Compose prompt** builds the identical fixed context (`SKILL.md` + the whole register + the
   template) and your intake-form inputs that `/api/draft` would send — `engine.build_copilot_prompt()`
   reuses the exact same `build_system_blocks()`/`build_user_message()` functions, so the two paths
   can't drift apart — combined into one plain-text block, since a chat window has no separate
   system/user split the way an API call does.
2. Copy it (or select the text yourself if clipboard access is blocked) and paste it into your
   assistant.
3. Paste the reply back into "Paste your assistant's response here" and **Check citations** — this
   runs the same `validate_citations()` check `/api/draft` already runs automatically, flagging any
   citation-shaped token that isn't actually in `sources/register.csv`.

What this does *not* do: track cost (there is none to the account this webapp uses), continue a
conversation on your behalf (your assistant keeps its own chat history — for a follow-up, keep
chatting there and paste each new reply back here if you want it re-checked), or resolve
`OPEN-QUESTIONS.md` #7 (what Copilot is actually approved for). It sidesteps that question rather
than answering it: you're the one submitting the prompt and reading the reply, the same trust
boundary as using your assistant directly, same as `ingestion/COPILOT-MODE.md`'s paste-ready prompts
for the ingestion pipeline. A real API integration (Azure OpenAI, a custom Copilot Studio agent) would
still need that question answered, plus Entra ID app registration and IT approval — out of scope here.

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

The request itself is given `engine.REQUEST_TIMEOUT_SECONDS` (120s) to finish. Generating up to 8000
output tokens can genuinely take a while, especially on a long reply chain; a request that's still
running past that comes back as a clear "timed out" error rather than an unlabelled failure.

## The citation check is a safety net, not a guarantee
`validate_citations()` in `engine.py` flags any all-caps hyphenated token that looks like a register
id (`TBS-DMP-4.3.1`, `CANADABUYS-AWARD-DATA`) but isn't actually one. It's a heuristic on shape, not
meaning — it can miss an unusually-written citation and can flag an unrelated token. It narrows what a
human checks before trusting a draft; it doesn't replace reading `sources/register.csv`.

## What this is not
- Not a hosted service by default, and running one is still a deliberate, separate decision, not
  a flag flipped in passing — `--host`/`--require-auth` make a shared instance *possible* without an
  app rewrite (`ARCHITECTURE.md`), they don't make one exist. A *hosted* multi-tenant version means
  someone else's inputs cross a network to infrastructure you control, which reopens
  `OPEN-QUESTIONS.md` #6-#8 in their hardest form for the caller whose data it is; this still needs
  thinking through per deployment, and nothing here decides it for you. The plain local default
  doesn't raise that question at all, because nothing here changes where the data goes versus using
  an AI assistant directly.
- Still not a UI for the private corpus (`fair-price-corpus`) — that repo, if cloned, is read
  directly by `SKILL.md`/an AI assistant, not through this webapp or any bot. See `ARCHITECTURE.md`'s
  "dual-bot" section for why that's deferred, not forgotten.
- Not a UI for the ingestion pipeline (`ingestion/`) — that still runs via the CLI tools or an AI
  assistant. Adding it here is future work, not started.
- Not a replacement for the sensitive-information gate's human review step — a clean scan is not a
  guarantee, exactly as the CLI tool itself says.

## Files
- `run.bat` — double-click launcher (Windows): starts `server.py` and opens the browser, stays open
  on error.
- `server.py` — stdlib `http.server`, routes only, no logic of its own. Every route is wrapped so an
  unhandled exception becomes a clean JSON 500, not a dropped connection.
- `auth.py` — caller resolution (`resolve_caller()`) for a shared instance; see `ARCHITECTURE.md`.
  `tools/test/test_webapp_auth.py` tests it directly.
- `tokens.txt.example` — copy to `tokens.txt` (gitignored) to configure a token roster.
- `engine.py` — the actual functions (scan, register, award search, commodity index, citation check,
  drafting, composing a Copilot-ready prompt). Imported and tested directly by `tools/test/test_webapp.py` without starting a server.
  `tools/test/test_webapp_server.py` tests the HTTP layer itself (routing, malformed input, auth
  gating, the catch-all) against a real server on a throwaway port.
- `static/` — plain HTML/CSS/vanilla JS, no build step, no CDN dependency.
