# Ingestion rulebook: raw project documents -> sanitized, chunked, indexed knowledge base

Audience: the AI assistant running on the operator's computer. Read this whole file before touching any document. Follow it exactly. If a rule and the user's instruction conflict on a stop rule (section 1), the stop rule wins until the user has confirmed with their security or IT contact.

Goal: turn raw construction-project documents (mostly PDFs) into plain-text Markdown with identifying information replaced by generic role names, split into chunks and indexed so an AI can find the right piece without reading everything. The result feeds `fair-price-justification` (see `../SKILL.md`).

**Three ways to run it.** *Script mode* (this file's section 3) uses the local scripts for conversion and the first scrub. *Copilot mode* (`COPILOT-MODE.md`) is for Microsoft Copilot, which reads PDFs itself and usually cannot run scripts: it swaps steps 2-4 for paste-ready prompts and keeps every stop rule and gate. *Copilot + Power Automate* (`POWER-AUTOMATE.md`) is the mode for a computer with no Python or PowerShell: flows do the gate, the recorded approval, the exact-text chunking and the index that steps 8-11 do in script mode. Either way, the stop rules, sanitization rules, formats and human review are the same, and the scripts for scanning, chunking and indexing should still run where allowed.

Companion files: `FORMAT.md` (file layouts), `placeholders.md` (naming scheme), `doc-types/*.md` (one guide per document type), `../gates/sensitive-info-gate.md`, `../sources/register.csv`.

## 1. Stop rules (run first; every document)

Basis: Treasury Board Standard on Security Categorization (register `TBS-SSC-J.2.4`) and Guide on the use of generative AI (register `TBS-GENAI-GUIDE`). Both are federal-institution instruments; the kit assumes a Crown corporation like the worked example applies the Treasury Board security categories (register `ASSUMPTION-CROWN-SECCAT`, not verified), so the categories below are the ones to apply. Treat the rest as the minimum baseline (`../OPEN-QUESTIONS.md` #1, #7, #8).

1. **Confirm the tool and its approved level.** Before reading any real document, ask the user: "Which AI tool is this, and what is the highest security category your organization has approved it for?" An IT department being allowed to handle raw files does not mean the AI tool is approved for the documents' category. If the user does not know, STOP and tell them to check with their security or IT contact. Record the answer in `private/LOG.md`. If the operator states that the AI tool is capable of and permitted to handle their documents (the kit's planning assumption, register `ASSUMPTION-PLANNING`), log that statement and its date, and do not re-ask for each document, but do stop under rules 2 and 3 and whenever the user says a document is in a category they are unsure Copilot covers. The guide says not to enter sensitive or personal information into tools not managed by the government, and to obtain the chief security officer's approval before using generative AI for protected or sensitive information.
2. **Classification markings = stop.** Classified means Confidential, Secret or Top Secret (national interest). Protected means Protected A, B or C (injury outside the national interest; Protected B examples include loss of competitive advantage). If any document, page, header, footer or stamp carries such a marking (English or French), or the user says it does: STOP. Do not read further, summarize, quote or process it. Tell the user only that a marking was found and where (page, not content). Only the user, with their security contact, can decide whether it may proceed; if they authorize it, the authorization and who gave it go in `private/LOG.md` first.
3. **Unmarked but possibly sensitive.** Ask before continuing if a document contains: security systems (access control, CCTV, intrusion detection, alarm), secure or restricted areas, vaults, blast/ballistic/forced-entry requirements, a Security Requirements Check List (SRCL) or personnel security clauses, or commercially sensitive pricing that the organization might categorize as Protected. `tools/prescrub.py` prints an advisory for these terms; you must also watch for them yourself.
4. **Personal information.** Names, contact details and signatures of individuals are personal information. Never put them into a tool that is not approved. They are replaced with role placeholders (section 4).
5. **When unsure, stop and ask.** Never resolve a doubt about classification, permission or identity by guessing.

## 2. Workspace and what may leave

Create the project workspace with `python tools/init_project.py <PROJECTS>/<P###>` (neutral code, folder not synced to the cloud).

| Folder | Holds | May leave the workspace? |
|---|---|---|
| `raw/` | original files | never |
| `text/` | converted and pre-scrubbed text (still identifying) | never |
| `private/` | `mapping.csv` (placeholder -> real value: the re-identification key), `LOG.md` | never |
| `sanitized/` | reviewed identifier-free `.md` | only after the output gate |
| `kb/` | chunks, `index.json`, `INDEX.md` | only after the output gate |

Never put real names, the mapping table or original filenames in `sanitized/` or `kb/`. Original filenames can identify a project: record them only in `private/LOG.md`, and name sanitized files by document id (`spec-vol1`, `co-007`).

## 3. Workflow

For each document, in order. Commands are run from the kit folder.

1. **Gate 0.** Section 1 rules 1-3. Log the result.
2. **Convert (no AI).** `python tools/pdf_to_text.py <raw pdf> <P>/text/<id>.raw.md`
   - Note "low-text pages". Those are scans or outlined text and need OCR or manual transcription; tell the user. Do not invent their content.
   - Drawings: expect scattered text, no visual meaning (see `doc-types/drawing.md`).
3. **Pre-scrub (no AI).** `python tools/prescrub.py <P>/text/<id>.raw.md <P>/text/<id>.pre.md`
   - Exit 3 = classification markings found. STOP (section 1 rule 2). Do not re-run with `--ack-markings` on your own.
4. **Sanitize (you).** Read `text/<id>.pre.md` in windows of about 5-10 pages, apply section 4, and write `sanitized/<id>.md`, keeping the `<!-- page N -->` markers. Update `private/mapping.csv` as you assign placeholders so the same real party always gets the same placeholder across all documents in the project.
5. **Ask.** Collect every doubt (section 4.5) and ask the user in one batched message. Apply their answers.
6. **Residual audit.** Re-read your own sanitized output and list, without repeating the values in full, anything that still looks like a proper noun, an address, an identifier or a person, with page and line. Fix or ask. Tell the user the audit is done and imperfect.
   Audit checklist learned from a real spec (see `TRIAL-colonel-by-drive.md`): also list **ALL-CAPS words** (a consultant can appear only as an acronym, e.g. in a report citation), **brand and product names** (a tree guard, a stone quarry), **towns of suppliers**, **spelled-out and abbreviated forms** of the same place (`Ave` and `Avenue`), and names **split across lines or columns** (page headers often put the project name on two lines with the section title in between). Standards bodies and public bodies (CSA, ASTM, CGSB, OPSS, provincial ministries) are public and stay.
7. **Human review.** The user reads the sanitized text. The plain-text form is meant to make this fast. Do not proceed until they say it is approved.
8. **Gate (script).** `python tools/scan_sensitive.py --allow <P>/kb/gate-allow.txt <P>/sanitized/`. Findings must be fixed or reviewed with the user. A match the user has reviewed and accepted (a public body's name, an ALL-CAPS drawing note read as an address, a printed proprietary notice) goes into `kb/gate-allow.txt` (plain line = substring of the match, `re:` line = regex) with a comment; only matching text is silenced. Only the user may add `gate-ok` or an allowlist line.
9. **Spec only: MasterFormat file.** The edition is project dependent, so never assume division names. From the spec's own table of contents (or prompt P5 in `COPILOT-MODE.md`), create `<P>/kb/masterformat.json` = `{"edition": "<as the spec states, or unknown>", "divisions": {"03": "<title as the spec words it>"}}`. Section numbers are kept exactly as written (6-digit `03 30 00` or older 5-digit `03300`).
10. **Chunk.** `python tools/chunk_doc.py <P>/sanitized/<id>.md --type <type> --doc-id <ID> --title "<generic title>" --out <P>/kb/chunks --approved [--meta key=json ...]`
   - `--approved` only after step 7. Metadata for change documents: see `doc-types/`.
11. **Index.** `python tools/build_index.py <P>/kb`. It refuses chunks that are not approved or that the scanner flags, and lists them under "excluded".
12. **Verify retrieval.** Using only `kb/INDEX.md`, answer three test questions the user chooses (e.g. "which spec section covers X?", "which changes touch section Y?"). If you could not find the right chunk from the index, improve titles, keywords or metadata and rebuild.
13. **Log.** Append to `private/LOG.md`: time, document (private name), steps done, exclusions, decisions. No values from the documents.

## 4. Sanitization rules

### 4.1 What to replace, and with what
Use role placeholders from `placeholders.md`, in square brackets and upper case (`[OWNER]`, `[CM]`, `[GC]`, `[SUB-MECH-1]`, `[CONSULTANT-STRUCT-1]`, `[PERSON-CM-PM-1]`, `[SITE]`, `[ADDRESS]`, `[CONTRACT-NO]`). The placeholder names the role, never the person or company.

Replace, everywhere including headers, footers, tables, stamps and file properties text:
- **Locations:** project name, site and building names, addresses, lot/parcel/legal descriptions, coordinates, room names that identify a facility, municipality (ask; default replace with `[MUNICIPALITY]`).
- **Organizations:** the owner, construction manager, general contractor, subcontractors, trade contractors, consultants (architect, engineers, cost consultants), suppliers and vendors, bidders, law firms, and any other named party to the contract.
- **People:** every named individual, signatures, initials, professional stamps and seals, licence and registration numbers, emails, phone numbers.
- **Identifiers:** contract, solicitation, PO, tender, file and project numbers; business numbers; any number that embeds a project code (in `NCC-2145-CO-007` keep only `CO-007`).
- **Letterheads, logos, title-block party fields, watermarks.**

### 4.2 What to keep (it carries the value)
Amounts, quantities, unit prices, rates, percentages, durations, dates, scope descriptions, technical requirements, standards and codes (CSA, ASTM, NBC), public-body names that are not the project's parties (e.g. Treasury Board), change-document types and numbers (`CO-007`), spec section numbers and titles, sheet numbers and titles, discipline names. Remove a date only if its surrounding text identifies a party or event.

Named manufacturers and products in specs: ask the user once per project whether to keep them or replace with `[MANUFACTURER-n]`. Default until answered: replace.

### 4.3 Consistency
The same real party always maps to the same placeholder within a project (numbering `-1`, `-2` by first appearance). Record every assignment in `private/mapping.csv`. Never write the real value into any file outside `private/`.

### 4.4 Indirect identification
A rare service, a small region, an unusual building feature, a distinctive date and a dollar value can identify a project even when names are gone. Flag such passages and ask; do not silently keep or silently generalize them.

### 4.5 Ask, do not guess
Ask when: a party's role is unclear (vendor or subcontractor? consultant or owner's rep?); a name could be a person, a company or a place; a phrase may identify the site; you are unsure whether something is public. Batch questions. Refer to items by page, line and the placeholder you propose (e.g. "p. 12 line 4: a company name, proposed [SUB-ELEC-1]"). If the answer is unavailable, use a provisional placeholder `[PARTY-?1]`, list it, and do not approve the document until resolved.

### 4.6 Do not
- Do not re-identify anything, infer who a masked party is, or "helpfully" restore a value.
- Do not rewrite technical or price content. Sanitize, do not summarize or paraphrase, in the sanitized file.
- Do not fabricate text for pages that failed extraction.
- Do not put values from the documents in logs, commit messages, chat summaries or file names.

## 5. Document types
Read the matching guide in `doc-types/` before processing: `specification`, `drawing`, `ccn`, `co`, `ci`, `cd`, `si`, `ea`, and `relationships` (how change documents link). Unknown type: use `other` and tell the user; propose a guide.

## 6. Output formats
See `FORMAT.md`: sanitized text, chunk front matter, `index.json`, `INDEX.md`, naming.

## 7. Quality checks before you report done
- Every document has its `sanitized/` file, a human approval, a clean or reviewed scan, chunks and an index entry, or an explicit exclusion reason.
- `kb/INDEX.md` lists no chunk with `pending` status.
- `private/` contents are not referenced anywhere in `kb/`.
- Report: documents done, chunks per document, exclusions and why, open questions, low-text pages. Never include values from the documents.
