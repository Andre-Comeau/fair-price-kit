# fair-price-kit

A working-draft toolkit for two connected jobs:

1. **Drafting "fair and reasonable price" justifications** for procurement decisions in the Canadian federal context, with every policy citation traceable to a source register, and public award data as market evidence.
2. **Turning construction project documents** (specifications, drawings, change documents, tender packages) into sanitized, chunked, indexed plain text that an AI assistant can search without reading everything, with stop rules for classified or sensitive material.

The National Capital Commission (NCC), a federal Crown corporation, is the **worked example**, using public information only. Nothing here states or implies that any person works for, with or on behalf of it.

> **Status: draft v0.1 (2026-09-21).** Not approved by any organization's security, privacy or legal function. Nothing has been run in Microsoft Copilot or Power Automate yet (see `OPEN-QUESTIONS.md`). Read `NOTICE.md` before using or sharing anything: it covers copyright, data licences, tender-document restrictions and disclaimers.

## Start here
| If you want to... | Read |
|---|---|
| know what is still unconfirmed | `OPEN-QUESTIONS.md` |
| draft a price justification | `SKILL.md`, `templates/justification-template.md`, `sources/register.csv` |
| ingest real project documents | `ingestion/RULEBOOK.md` (stop rules first), then `ingestion/COPILOT-MODE.md` or `ingestion/POWER-AUTOMATE.md` |
| use the public award data | `data/canadabuys-awards-ncr-construction.README.md` (cautions before any number) |
| check the tools work | `python tools/test/run_all.py` |
| see what a real run taught us | `ingestion/TRIAL-colonel-by-drive.md` |

## What is in the repository
- **The skill.** `SKILL.md` (agent instructions in the Agent Skills form), `templates/justification-template.md`, `sources/register.csv` (25 entries: 20 read at the page or API they cite, 1 partly verified, 2 marked unverified, 2 planning assumptions).
- **Gates.** `gates/sensitive-info-gate.md` (rules for warning about locations, vendors, consultants, contractors and individuals) and `tools/scan_sensitive.py` (pattern scanner; supports reviewed exceptions with `--allow`).
- **Ingestion.** `ingestion/RULEBOOK.md` (stop rules on classified and protected material and on tool authorization; workflow from PDF to chunks), `COPILOT-MODE.md` (paste-ready prompts for Microsoft Copilot), `POWER-AUTOMATE.md` (build guide for the gate, approval, chunking and index as cloud flows where no scripting is available), `FORMAT.md`, `placeholders.md`, and `doc-types/` (specification, drawing, CCN, CO, CI, CD, SI, EA and how change documents relate).
- **Tools** (pure Python, standard library; `pdftotext` from poppler, or `pypdf`, for PDFs): `init_project.py`, `pdf_to_text.py`, `prescrub.py`, `chunk_doc.py`, `spec_headers.py`, `build_index.py`, `scan_sensitive.py`, `canadabuys_filter.py`. Tested on Python 3.10.
- **Data.** `data/canadabuys-awards-ncr-construction.csv` (125 Ottawa-area construction awards, 2022-2026), `data/canadabuys-tender-attachments-index.csv` (links only; 555), their two READMEs, `data/SCOUTING-canadabuys.md` (what CanadaBuys offers and its rules), `data/SOURCES-candidates.md` (survey of further public sources: bids and amendments, escalation indexes, labour and equipment rates), and `data/comparables.csv` (empty by design).
- **Tests.** `tools/test/` (synthetic data only): `python tools/test/run_all.py` runs five groups, including an end-to-end pipeline test (skipped with a message if `pdftotext` is not installed).

## Using it as an agent skill
Copy this folder to `~/.claude/skills/fair-price-justification/` (Claude Code personal skills) so `SKILL.md` sits at the top of the skill folder. This installation route has **not** been tested here. The skill instructs the agent to cite only the register, to draft (never approve), to run the sensitive-information gate, and to use the award data only under the rules in `SKILL.md`.

## Data and licensing (short version; full text in `NOTICE.md`)
- Code, documents and templates: MIT License (`LICENSE`), © 2026 Andre-Comeau.
- **Contains information licensed under the Open Government Licence – Canada.** The CanadaBuys-derived data files keep that licence and this attribution; they are filtered and extended, are not official, and do not imply endorsement.
- Tender documents are **not** included and are copyright protected; only links are listed. Do not redistribute them, and do not script bulk downloads (CanadaBuys `robots.txt` disallows crawling).
- Policy text is paraphrased from Treasury Board of Canada Secretariat sources, with references, and may be out of date. Read the original.
- Not legal, procurement or security advice.

## Known limits
- Award data give the winning total only: no bids received, no unit prices, tax basis unstated, cumulative totals for amended contracts. 21 of 125 rows are flagged and should not be used as price comparables.
- The sanitization pipeline reduces risk; it does not guarantee that no identifying information remains. Pattern scanning cannot find names in plain words, so it relies on a human review and an audit prompt.
- The Copilot prompts and the Power Automate flows are designed and reference-tested in Python only; they have not been run in those products.
- OCR is not included. Scanned pages are reported, not read.
