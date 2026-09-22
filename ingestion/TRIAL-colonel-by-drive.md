# Trial run on a real NCC tender package (2026-09-21)

Package: the public tender documents for an NCC retaining-wall rehabilitation (contract PO-021710, 14 PDFs, 47,821,027 bytes, all reachable without a login). Run in script mode on the maintainer's machine, with Claude standing in for the sanitizing assistant. This file holds lessons only: no document text, no names of people or firms. The documents and all derived text stay in a private workspace outside the kit.

## Stage results
| Stage | Result |
|---|---|
| Download | 14 of 14 files; total matched the size read from headers; all valid PDFs |
| Text extraction (`pdftotext -layout`) | all 14 converted. 117-page spec: no low-text pages. Reports: geotechnical 11 of 68 pages and soil screening 5 of 113 pages have almost no text (figures or scans). Two 1-page topographic surveys: no text (vector or outlined text), so they need OCR or manual transcription. |
| Classification-marking check (`prescrub.py`) | 10 documents passed. **4 stopped**: the three drawing sets (only the word "confidential", about once per sheet) and the RFP ("confidential", "secret", "top secret" and French forms, most likely a security-requirements clause). Nothing from those four was read. A human decision is needed (rulebook section 1). |
| Sectioning of the spec | **`SECTION nn nn nn - TITLE` headings do not exist.** Sections appear only in a running page header. New mode `chunk_doc.py --sections-from page-headers` (`tools/spec_headers.py`, tested by `tools/test/test_spec_headers.py`) found 30 sections and produced 44 chunks. |
| Sanitization of the spec | mapping-driven replacement, 20 placeholders, about 640 replacements (the owner's abbreviation alone appears 356 times). Leak check against the mapping: clean. Scanner: clean. |
| Index and retrieval test | 44 chunks indexed, none excluded. Three practical questions (asphalt paving, pay items, excess soil) were answered from `INDEX.md` alone. |

## Lessons (already applied to the kit unless marked open)
1. **Real specs may have no heading lines.** Fixed with the page-header mode; for the Power Automate route, Copilot inserts the heading lines (prompt P2). Section numbers in page headers can disagree with the table of contents, and the extracted table of contents is scrambled by column layout: trust the headers and check any cited section.
2. **The residual audit found what the first pass missed**: a firm that appears only as an ALL-CAPS acronym in a report citation, two stone quarries and their towns, a product brand, a second street and a drive, the spelled-out form of an abbreviated avenue, and the municipality. The audit checklist in `RULEBOOK.md` step 6 and prompt P3 now include ALL-CAPS words, brands, supplier towns, spelled-out and abbreviated variants, and names split across lines.
3. **Project names are split across two header lines** with the section title between them, so a whole-phrase match misses them; the mapping needs the partial forms too.
4. **Long-section splitting had two defects**, found on real data and fixed: every part reported the whole section's page range, and a heading-only stub chunk was created before "PART 1". Keyword extraction was noisy ("representative", "material"); spec vocabulary is now a stop list.
5. **The marking check is deliberately blunt.** On tender documents it will stop drawings and RFPs for the word "confidential" (a notice) or for security-clause wording. Expect false positives, and expect the human decision step to be used. (Open: after a human glance at one sheet or clause, allow a per-document override in `private/LOG.md`.)
6. **Pricing content is not in the spec.** It lists a unit-price item list in its contents, but that list is in the bid form or the RFP; the spec has the pay-item descriptions (what each item includes and how it is measured and paid). Price analysis needs the RFP or bid form.
7. **Public tender documents can still carry personal information** (named staff on the cover, professional seals, signature blocks). The prescrub replaced pattern-shaped items; names needed the mapping.
8. **Not tested:** Copilot extraction and sanitization, the Power Automate flows, chunking of drawings (stopped by the marking check), tables (pdftotext layout output), OCR pages, and change documents (none exist pre-award).

## Phase 2: the other 13 documents, including the four stopped by the marking check
The user authorized the four stopped documents in chat (logged first in the private log), and asked for all the rest to be processed. Result: **12 text documents sanitized** (60 mapping rules, 93 patterns), leak-checked against the mapping, scanner-clean with a project list of reviewed exceptions, chunked into **351 chunks** and indexed (0 excluded). The two 1-page surveys have no text and were not processed. The "approved" flag was set for this tooling test only: no human has reviewed the sanitized text.

| Document | Chunks | Note |
|---|---|---|
| specification (117 pp) | 44 | header-style sectioning |
| specification section (1) | 3 | |
| drawings: structural, electrical, landscape (14+5+14 pp) | 33 | one chunk per sheet page |
| RFP (94 pp, bilingual) | 94 | page chunks; contains the bidder price form |
| addenda 1 and 2 | 1 + 6 | bidder questions and answers |
| geotechnical report | 57 | |
| soil screening report | 111 | lab certificates included |
| waste-audit form, species-at-risk sheet | 1 + 1 | |

### More lessons (applied unless marked open)
1. **The marking check's four stops were false positives** here: the drawings carry a printed notice that the sheet is the owner's proprietary information and may not be copied, and the RFP's "secret / top secret" wording is a personnel-security clause. The decision still belongs to the user; the kit now records it in the log and lets a reviewed exception silence a match (below).
2. **Drawing extraction needs `pdf_to_text.py --raw`.** Layout mode turned a 14-page structural set into 9.9 million characters (98% whitespace); raw mode gives about 195,000. Drawing text is a list of labels and notes, not prose.
3. **The scrub destroyed data until three patterns were tightened**: "450 450 450" (bar spacings) looked like a SIN, "300 300 2500" looked like a phone number, and a bare "M" title turned the date "July 9, 2020" into "[PERSON] 9, 2020". Phones and SINs now need a cue (hyphens, parentheses or a label); person titles exclude bare "M". Regression cases added. Rule of thumb: **a scrub must never alter numbers in engineering documents**.
4. **Real phones were being missed** (a form like `(613)555-0123` with no space after the bracket): the new phone pattern found 77 in the soil report where the old one found 13. Emails broken across a line ("name@org- other.ca") are now matched too.
5. **The same person appears in several forms across documents** (full name in the spec, initial plus surname in a drawing title block, initials in a report footer). The mapping needs every form, and the leak check must run across the whole document set after each new alias.
6. **Reports carry the most identifying content**: consultant staff who wrote and reviewed them, the person who logged boreholes, drilling and traffic-control contractors and their towns, testing laboratories with street addresses and accreditation footers, the consultant's file numbers and even a server path. Public accreditation and professional bodies are kept.
7. **Bidder questions and answers (addenda) name neighbouring projects, other owners' tender numbers and contractors**; they are valuable scope clarifications, so they are kept with placeholders.
8. **A reviewed-exceptions list is needed.** ALL-CAPS drawing notes look like addresses (a note like "1234 EXISTING ONE WAY LANE"), "ISSUED FOR TENDER 2000-01-01" looks like a contract number, and public bodies end in "Inc." or "Corporation". `scan_sensitive.py --allow FILE` and `kb/gate-allow.txt` (read by `build_index.py`) record what a human accepted; only matching text is silenced.
9. **Page-chunk titles**: report and RFP chunks now take the page's first meaningful line as their title (`chunk_doc.py`), otherwise the index is unnavigable. Still weak for the bilingual RFP, where many pages share a running header (14 distinct titles over 94 pages). Open: heading-aware chunking for reports and RFPs.
10. **Retrieval**: from the index alone, 3 of 5 practical questions found the right chunk (earth-pressure table, shoring-pile removal, lane width); 2 needed a text search inside the chunks. That is the intended split: the index narrows, a search finishes. Keyword extraction cannot find a specific fact inside a large chunk.
11. **Pricing evidence in a tender package**: the RFP holds the bidder price form (item, description, quantity, unit, blank price columns): a quantity schedule with no prices. The award data gives only the total. **No unit prices are published anywhere.**
12. **Open**: OCR for the two survey sheets and the low-text pages in the reports; a per-document override for marking-check stops; a table-aware extractor for the price form and lab certificates.

13. **An end-to-end test found an off-by-one in header-style sectioning**: each section's start page was one page early (a section that begins on page 3 reported page 2), because a section began on its own page marker and the page counter did not count the marker it stood on. Fixed in `spec_headers.py` and pinned by `tools/test/test_pipeline.py` (a synthetic header-style spec). Page numbers quoted from header-style chunks before this fix start one page early; end pages were right.
14. **The sectioning mode is now chosen automatically** (`--sections-from auto`), and the tools fail with a clear message instead of a traceback on a missing file, and refuse to report success when the input has no text (an empty extraction would otherwise pass unnoticed).
