# Sensitive-information gate (second gate)

Purpose: the user sanitizes first. This gate is the backstop for what slips through. It never replaces the user's own sanitization or their organization's rules on what may be shared.

## When it runs
- **Input gate:** every time the user pastes text, attaches a file, or describes a real file. Run before analysing.
- **Output gate:** before writing to any file that could leave the private workspace (anything in a git repo, a shared folder, an email, a message, a published page), and again before any commit or push.
- **Data gate:** before adding any row to `data/comparables.csv`.

## What to look for
Direct identifiers:
- **Project and location:** project names, site or building names, street addresses, lot/parcel/legal descriptions, coordinates, asset or facility IDs, unusual place names that identify a site.
- **Organizations:** vendors, suppliers, bidders and proponents; consultants; general contractors; construction managers; subcontractors; owner's representatives; law firms; anyone named as a party to the contract.
- **People:** names of individuals (staff, vendor staff, evaluators, signatories, decision-makers), signatures, emails, phone numbers, employee or licence numbers.
- **Identifiers:** contract, solicitation, PO, file and tender numbers; business numbers; bid or quote reference numbers.
- **Commercially sensitive figures:** bid prices, unit rates or cost breakdowns that can be tied to a named or identifiable party; evaluation scores; pending or unpublished award details.
- **Restricted material:** anything marked confidential, protected, privileged, in-confidence, or under NDA.

Indirect identifiers (flag as a *combination* risk): a rare service + a small region + a date + a dollar value can identify a party even with names removed.

## What to do on a hit
1. **Stop.** Do not continue the task with the flagged content, and do not write it to any file.
2. **Warn** in a short message that lists categories and locations, not the values:
   `WARNING: possible sensitive information. Found: 2 organization names (paragraph 2), 1 street address (line 14), 1 contract number (header). Values not repeated here.`
   Mask or omit the values when quoting. Never repeat them in full.
3. **Offer options,** and wait:
   - Replace with placeholders and continue (`[VENDOR-A]`, `[CONSULTANT-1]`, `[SITE-1]`, `[PERSON-1]`, `[CONTRACT-NO]`, `[AMOUNT]`). Keep one mapping table **only in the private workspace**, never in a shared or published location.
   - The user confirms the content is authorized for this use and stays in the private workspace. Then continue, but the output gate still blocks publishing.
   - Cancel.
4. **Log the event** (category and count only, no values) in the working notes so the user can see what was flagged.

## Rules
- Never guess that something is safe because a name looks generic or common. When unsure, warn.
- Do not un-redact or infer masked identities from context, and do not help re-identify them.
- If a placeholder mapping table exists, treat it as sensitive: never commit or share it.
- Warn even when the user says the data is fine to use privately if the destination is a repo, shared drive or message. Privately is not the same as publishable.
- Include a short reminder when a real file is first pasted: the tool has now seen this content; check that your organization permits that.
- Detection is imperfect. State this when reporting a clean result: "No sensitive information detected by this check. This does not guarantee none is present. Review before sharing."

## Scanner (pattern check, not AI judgment)
`python tools/scan_sensitive.py <files or folders>` finds contact info and identifiers by pattern: emails, phone numbers, postal codes, street addresses, company-suffix names (Inc., Ltd., Corp., ...), contract/solicitation/PO numbers, business numbers, SIN-like numbers, coordinates, non-government URLs, titled names (Mr./Dr./...), "Prepared by:"-style signature lines, and confidentiality markings. Exit code 1 means findings. Values are masked in its output.
- Run it as part of the output gate, on every file about to be shared, and treat exit 1 as a stop. Report its categories and line numbers to the user, never the values.
- It cannot see vendor, consultant, contractor or person names written as plain words, or site names. Those remain the AI's and the user's job.
- A line can carry the marker `gate-ok` after a human has reviewed it as public (the scanner skips it). Never add the marker yourself without the user's say-so.
- `tools/test/` holds synthetic files to check the scanner still works (`synthetic-dirty.txt` must produce findings, `synthetic-clean.txt` must not). Exclude that folder from anything shared.
- Pattern matches are false-positive-prone (e.g. the words "confidential" in a policy quote). Review each finding rather than bulk-marking.

## Pre-publish checklist (output gate)
Before any commit/push or file leaving the workspace, confirm and say so explicitly:
- [ ] Ran `tools/scan_sensitive.py` on every file to be shared: no findings, or each finding reviewed with the user
- [ ] Scanned every file to be shared for the categories above
- [ ] Only placeholders or public/synthetic data present
- [ ] No mapping table, notes or comparables rows with real identifiers included
- [ ] User has given an explicit yes to share these specific files
