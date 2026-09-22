# Copilot mode: ingestion with Microsoft Copilot (no scripts needed for extraction or sanitization)

Use this when the AI available on the target computer is Microsoft Copilot. It replaces the script steps 2-4 of `RULEBOOK.md` with paste-ready prompts. **Python and PowerShell are not assumed to exist on the target computer**: the gate, approval, chunking and index are built as Power Automate flows (`POWER-AUTOMATE.md`); the Python scripts remain as an alternative where they are allowed. Everything else in the rulebook still applies: the stop rules (section 1), the sanitization rules (section 4), `placeholders.md`, the doc-type guides, `FORMAT.md`.

## What is assumed and what is not
Planning assumptions recorded by the maintainer on 2026-09-21, none verified (register `ASSUMPTION-PLANNING`, `ASSUMPTION-CROWN-SECCAT`):
- Copilot can read PDFs and turn them into text.
- Python and PowerShell are not available on the target computer; Power Automate is.
- A Crown corporation such as the worked example applies the Treasury Board security categories.
- For planning, Copilot is assumed capable of, and permitted to handle, the documents being ingested. Whoever runs the kit records that statement with its date in `IngestLog` / `private/LOG.md` at the start of each project. It does not cover a document whose category has not been checked (Gate 0), and it is not a substitute for the security contact's approval where a document carries a marking.

Still to confirm before the first real document (write the answers in `private/LOG.md`):
1. Which Copilot exactly (Microsoft 365 Copilot, Copilot Chat, other), and does the organization's data protection apply to it (are prompts and uploaded files kept inside the organization's tenant, and are they used for training or retained)?
2. **The highest security category Copilot is approved for.** Access to raw files by IT staff is not the same as Copilot being approved to process them. The Treasury Board guide says to obtain the chief security officer's approval before generative AI is used for protected information.
3. Whether it can save files, or only produce text you copy out.
4. Its limits on PDF size and page count. Do not assume it read a whole long PDF; check (stage A).
5. (Assumed: no Python or PowerShell; Power Automate flows replace the scripts.) Check that flows can be created with the SharePoint and Outlook connectors and that no data-loss-prevention policy blocks the combination.

## Gate 0: the human, before anything is uploaded
- [ ] Look at the first page, every page header/footer and any stamps for Protected A/B/C or Confidential/Secret/Top Secret markings (English or French). Marked => STOP. Only you and your security contact can decide to proceed; record who authorized it in `private/LOG.md` first.
- [ ] Look for security-sensitive content: access control, CCTV, intrusion detection, secure or restricted areas, vaults, blast/ballistic requirements, an SRCL. If present, ask your security contact first.
- [ ] Confirm the answer to question 2 above covers this document's category. Pricing can itself be a competitive-advantage matter (Protected B in the Standard's examples); if unsure how NCC categorizes it, ask.
- [ ] Original filenames stay in `private/LOG.md`; give the working copy a neutral id (`spec-vol1`).

## Stages

| Stage | Who | Output (save where) |
|---|---|---|
| A. Extract | Copilot, chat 1 | raw text -> `text/<id>.raw.md` (private) |
| B. Sanitize | Copilot, same project chat | sanitized text -> `sanitized/<id>.md`; mapping table -> `private/mapping.csv` |
| C. Audit | Copilot, a NEW chat that sees only the sanitized text | audit list (no values) |
| D. Review | you | approval |
| D2. Gate + approve | Power Automate Flow 1: mapping-list leak check, marking words, contact characters, unresolved placeholders, then your recorded approval by email (Outlook *Send email with options*) | file copied to `sanitized-approved/` |
| E. Chunk and index | Power Automate Flows 2 and 3 (or the Python scripts, or prompt P4 as a last resort) | `kb/` |
| F. Retrieval test | Copilot or any AI, given only `kb/INDEX.md` | pass/fail on three questions |

**Folder names.** This file says `text/`, `sanitized/` and `private/mapping.csv` (script layout). In the Power Automate layout (`POWER-AUTOMATE.md` section 3): sanitized text is saved into `sanitized-review/` (Flow 1 checks it and, after your approval, copies it to `sanitized-approved/`); the mapping table rows go into the `Mapping` SharePoint list; `kb/` is written by Flows 2 and 3.

Work in windows of 5-10 pages so the model stays consistent. Keep one sanitization chat per project so the running placeholder mapping stays in that chat; save the mapping table to `private/` at the end of each session and delete nothing from it.

## Prompts (paste; fill the brackets)

### P1. Extract (stage A)
```
Extract the text of the attached PDF, pages [N-M]. Rules:
- Output verbatim text only. Do not summarize, correct, reorder, translate, tidy or omit anything. Keep numbers, units and symbols exactly.
- Put a line `<!-- page N -->` before each page (N = the PDF's own page number).
- Keep tables as aligned plain text or Markdown tables with every number unchanged.
- If a page has no readable text (scan, image only, drawing linework), write `<!-- page N: NO TEXT -->` and do not guess its content.
- Do not open or describe images. Do not add commentary inside the text.
At the end, report separately: (1) how many pages you read out of how many pages the PDF has; (2) pages with no text; (3) a list of every monetary amount you extracted with its page number, so I can check it against the PDF.
```
After P1: compare the page count with the PDF's, and spot-check at least 5 amounts against the PDF. Save the text into `text/<id>.raw.md`.

### P2. Sanitize (stage B): paste the extracted window after this text
```
Sanitize the text below for a knowledge base. Replace identifying information with generic role placeholders and change nothing else: no summarizing, rewording, correcting, rounding or re-formatting; keep every number, unit, date, standard and technical requirement exactly; keep the `<!-- page N -->` lines.
Replace with placeholders in square brackets, the same real party always with the same placeholder, numbered by first appearance:
[OWNER] owner/client; [OWNER-PM]/[OWNER-REP] owner staff by role; [CM] construction manager; [GC] general contractor; [SUB-<TRADE>-n] subcontractor (e.g. [SUB-MECH-1]); [CONSULTANT-<DISCIPLINE>-n] design or other consultants (e.g. [CONSULTANT-STRUCT-1]); [PERSON-<ORG>-<ROLE>-n] any other named person (e.g. [PERSON-CM-PM-1]); [VENDOR-n] supplier; [BIDDER-n] bidder; [MANUFACTURER-n] manufacturer/brand [KEEP or REPLACE: <user choice>]; [PROJECT] project name; [SITE], [BUILDING-n], [ROOM-n] identifying places; [ADDRESS], [POSTAL-CODE], [MUNICIPALITY]; [CONTRACT-NO], [PO-NO], [SOLICITATION-NO], [FILE-NO] identifiers; [EMAIL], [PHONE], [BUSINESS-NO]; [SIGNATURE], [STAMP], [LOGO]. If a number embeds a project code, keep only the document type and number (e.g. CO-007).
Also replace: signatures, seals, licence numbers, letterheads, logos, drawing title-block party fields, plot stamps and file paths.
Keep: amounts, quantities, prices, rates, percentages, dates, durations, scope text, standards (CSA, ASTM, NBC), public bodies that are not parties to this contract, spec section numbers/titles, sheet numbers/titles, change-document types and numbers.
Formatting: keep each spec section heading on its own line, starting at the first character of the line, exactly as `SECTION nn nn nn - TITLE` (or `SECTION nnnnn - TITLE`), with a space-hyphen-space between number and title; do not indent headings. Keep the `<!-- page N -->` lines. If the specification has no `SECTION` heading lines and instead each page has a running header with `Section nn nn nn`, insert exactly one heading line `SECTION nn nn nn - TITLE` at the first page of each section (number and title taken from that header) and delete the repeated running-header lines on the following pages of the same section. Do not add any other headings.
When unsure whether something identifies a party or what role a party has: do NOT guess. Use [PARTY-?n] and list it. Do not try to identify or restore any replaced value.
Output three things, separated by lines of ====:
1) the sanitized text;
2) the mapping table as CSV `placeholder,role,real_value,first_seen_page` (this is private);
3) questions for me, each by page and line and proposed placeholder, without repeating the sensitive value where you can avoid it.
Text:
[paste window]
```
Answer the questions, ask Copilot to apply the answers, then save output 1 into `sanitized/<id>.md` and output 2 into `private/mapping.csv` (append, keep consistent).

### P3. Audit (stage C): open a NEW chat; paste only the sanitized text
```
This text was sanitized for a public knowledge base; identifying details should have been replaced by [PLACEHOLDERS]. Audit it. List, by page and line and WITHOUT quoting more than two words, anything that still looks like (include ALL-CAPS words and acronyms, brand or product names, towns, and names split across two lines): a person's name, a company or organization name, a place, site, building or address, a contract/file/PO/tender number, an email/phone/URL, a signature/stamp/licence number, a security marking, or a combination of details that could identify the project. Also list placeholders that look inconsistent (same role numbered differently) or that leave a party identifiable. Do not rewrite the text. If nothing is found, say so and remind me that this check is imperfect.
[paste sanitized text]
```
Fix findings (in the sanitization chat), then you review the sanitized file yourself (stage D). Search it for capitalized words you do not expect.

### P4. Chunk and index without scripts (stage E fallback; less reliable than the scripts)
Prefer the scripts (`tools/scan_sensitive.py`, `chunk_doc.py`, `build_index.py`): they enforce the approval and scan checks. If they cannot run, use this and expect to verify the counts by hand.
```
From the sanitized text below (document id [ID], type [spec|drawing|co|ccn|ci|cd|si|ea|other]), produce chunks as separate blocks, each starting with a front-matter block of `key: JSON value` lines and then the exact text of the chunk, unchanged.
Chunk rules: spec = one chunk per section (`SECTION nn nn nn`), splitting a section longer than about 12,000 characters at PART 1/2/3; drawing = one chunk per page; change documents = one chunk per document.
Front matter keys: id, doc_type, doc_id, doc_title (generic), section or sheet, chunk_title, division, pages [first,last], chars, sanitization "pending". For change documents also: number, date, status, amount, amount_type (fixed|estimate|not-to-exceed|none|tbd), currency, related [{"doc","relation","confidence"}] (only what the text states; mark anything you inferred as confidence "inferred" and say why), spec_sections, sheets. Do not invent any value: omit a key if the text does not state it.
Then produce INDEX.md: a table with one row per chunk (id, section/sheet, title, pages, 5 keywords, cross-references such as CO-007, Section 03 30 00, Sheet A-101). Finally state the number of chunks and confirm every page of the input is covered by exactly one chunk.
[paste sanitized text]
```
Then set `sanitization: "approved"` yourself only after review (stage D) and save the files under `kb/chunks/`.

### P5. MasterFormat edition (project dependent): once per spec
```
From this specification's table of contents / division list, produce JSON exactly like {"edition": "<edition or year as the document states it, or 'unknown'>", "divisions": {"03": "<division title exactly as this spec words it>", ...}}. Include only divisions that appear. Do not add divisions or titles from memory.
[paste table of contents]
```
Save as `kb/masterformat.json`. The chunker reads it; without it, chunks carry division numbers only.

### P6. Change-document metadata header (CCN, CO, CI, CD, SI, EA): paste the sanitized document
```
From the sanitized change document below, write ONLY a metadata header block: a line `---`, then one line per field as `key: JSON value`, then a line `---`.
Allowed keys: number, date (YYYY-MM), status (issued|approved|pending|rejected), amount (a number; negative for a deduct), amount_type (fixed|estimate|not-to-exceed|none|tbd), currency, originator_role, recipient_role, reason_category (owner-requested|unforeseen-condition|design-error|code|other), spec_sections (list), sheets (list), related (list of {"doc","relation","confidence"}).
Include a key only if the document itself states it. Never infer an amount or a link. Use confidence "stated" only when the text names the other document; otherwise omit the link and tell me what you noticed.
Do not include id, doc_type, doc_id, doc_title, chunk_title, pages, chars or sanitization.
[paste sanitized document]
```
Put the header at the very top of the sanitized file (nothing before it) and check every value against the document yourself. The chunking flow keeps these fields and ignores any attempt to set reserved ones, so a document can never mark itself approved.

## Limits to keep in mind
- Copilot, like any LLM, may silently paraphrase or drop text and can mis-read numbers in tables. Stage A's page count and amounts check exist for that reason; a bad extraction poisons every later step.
- Copilot cannot enforce the gates. The approval flag, the scanner and your review are what stop unsanitized text from reaching `kb/`.
- Audit and scan results are evidence, not proof. Detection of names in plain words remains imperfect.
