# Specification (`--type spec`)

**What it is:** the written technical requirements, usually organized by MasterFormat division and section ("master builder classifications"). Usually one or more volumes; each section normally has PART 1 General, PART 2 Products, PART 3 Execution.

**Why chunking matters most here:** specs are long and the answer to a question usually lives in one section.

**Chunking (automatic):** `chunk_doc.py --type spec` splits at `SECTION nn nn nn - TITLE` headings (6-digit; 5-digit accepted), keeps anything before the first section as a `front` chunk (Division 00/01 front matter, table of contents), and splits any section over the size cap at `PART 1/2/3`, then paragraph breaks. Check the result: if a spec uses different heading text (e.g. "SECTION 033000", "Section 03 30 00"), the tool handles common forms; if sections were not detected you get one big chunk, so tell the user and adjust the heading pattern rather than hand-splitting.

**Header-style specs (no `SECTION` heading lines).** Some real specs (for example in the worked example) identify sections only by a running page header (`<project> <TITLE> Section 01 33 00 / Page 2 of 6`), and pdftotext lays the header out in columns, sometimes across two lines. `chunk_doc.py` detects this automatically (`--sections-from auto`, the default) and groups pages by the header's section number (`tools/spec_headers.py`); force it with `--sections-from page-headers`. The section number is reliable; the title is a heuristic from the header columns. Numbers in headers can disagree with the table of contents (whose extracted layout is scrambled): trust the headers, and check any section you cite. Where the Python tool is not available (Power Automate route), have Copilot insert one `SECTION nn nn nn - TITLE` line at the first page of each section (prompt P2), so the standard chunker/flow works.

**MasterFormat edition:** it depends on the project (the 6-digit `03 30 00` numbering and the older 5-digit `03300` numbering are both in use, and divisions and their titles differ between editions). Build `kb/masterformat.json` from *this spec's* table of contents (see `../RULEBOOK.md` step 9); never fill division names from memory. Section numbers are kept as the spec writes them.

**Sanitize focus:** project name, owner, consultants and their stamps (front matter, section headers/footers often repeat project name and date on every page), named manufacturers and suppliers (ask once per project: keep or `[MANUFACTURER-n]`), addresses, contract numbers, contact persons in Division 01 (submittal contacts, testing agencies), allowance names. Keep: requirements, quantities, standards, allowance amounts and unit prices.

**Repeating headers and footers:** they appear on every page. Replace consistently, and when a repeated line is only project identification, it may be removed from the sanitized text (note that in `private/LOG.md`).

**Metadata to set:** `--doc-id SPEC-VOL1 --title "Project specification, volume 1"`. Division and section come from the text.

**Links:** specs cite other sections ("see Section 05 12 00"), drawings, and sometimes change documents (addenda, CO references). These are picked up in `refs`/`xref`.

**Pricing-relevant items to keep intact:** allowances, unit price schedules, alternates, measurement and payment clauses, general requirements on change pricing (markup, overhead and profit rules) and their cross-references. These support fair-and-reasonable analysis.
