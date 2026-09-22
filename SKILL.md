---
name: fair-price-justification
description: Drafts a written justification that the price being approved on a Canadian federal procurement or contracting decision is fair and reasonable, structured against the Treasury Board procurement instruments and the organization's own procurement policy. Use when someone must document why a price, quote, bid or contract amendment is acceptable, or needs the price-support section of a contract file or approval memo.
---

# Fair-price justification

## When to use
The user has a decision to approve (contract, amendment, sole-source, quote selection) and must write down why the price is fair and reasonable, in a form that stands up to review and audit.

## Sensitive-information gate (runs first, and again before output)
The user is expected to sanitize their inputs, but you are the second gate. Follow `gates/sensitive-info-gate.md` at three points:
- **Input:** before using anything the user pastes or attaches. If you detect project or site locations, vendors, bidders, consultants, general contractors, construction managers, subcontractors, individuals, contract or solicitation numbers, or identifiable pricing, STOP and warn. Name the categories and where they are, not the values. Offer placeholders, private-only continuation, or cancel, and wait for the user's choice.
- **Data:** before adding any row to `data/comparables.csv`.
- **Output:** before writing any file that could leave the private workspace, and before any commit or push, run `python tools/scan_sensitive.py <those files>` and also read them yourself for plain-word names the scanner cannot see. Exit code 1 is a stop: report categories and line numbers, not values. Get an explicit yes for those specific files.
When the scan is clean, say it found nothing but that detection is not a guarantee.

## Using project records (the knowledge base)
Historical project documents (specs, drawings, CCN/CO/CI/CD/SI/EA) reach this kit only after the ingestion workflow in `ingestion/RULEBOOK.md` (stop rules on classification and tool authorization, conversion, sanitization with role placeholders, human review, chunking, index). To use them, read `kb/INDEX.md` in the project folder first, open only the chunks it points to, and cite them by chunk id. Never read from a project's `raw/`, `text/` or `private/` folders, and never treat an `inferred` link between change documents as fact. When asked to ingest a document, follow the rulebook, and stop at its stop rules.

## Using the public award data (`data/canadabuys-awards-ncr-construction.csv`)
Read `data/canadabuys-awards-ncr-construction.README.md` before using any number from it.
- The price is `total_contract_value` (cumulative, includes amendments, tax basis unstated). Never use `contract_amount_raw`.
- Use only rows whose `quality_flags` is empty. Rows flagged `total_zero`, `currency_blank`, `framework_not_a_price` (a supply arrangement or standing offer itself) or `cm_contract_total_may_include_trades` (a construction-management total that can include trade work) are not comparable prices; say so if the user asks about one.
- Call a comparable "market-tested" only when `competitive = yes` and `selection_criteria = Lowest Price`; otherwise state the criteria (price is mixed with quality).
- The data give the winning value only: no bids received, no bid range, no unit prices. Never present it as a range of bids or as a unit rate.
- A comparable needs a stated match on scope, size, date and conditions, and an inflation adjustment from a source you name (never invent an index).
- Group suppliers with `supplier_key` only after checking the variants.
- Cite `CANADABUYS-AWARD-DATA`, the contract number and the retrieval date (2026-09-21), and add the line "Contains information licensed under the Open Government Licence – Canada." to the justification when data from this file are used.
- Links in `data/canadabuys-tender-attachments-index.csv` lead to copyright-protected tender documents: never fetch them without the operator's instruction, never redistribute them, and run the ingestion rulebook (including its stop rules) before reading one.

## Using the price-fact corpus (`fair-price-corpus`, private companion repo, if cloned locally)
It sits beside this kit as a sibling folder (`../fair-price-corpus`); if it isn't there, skip this section — the kit still works without it.
- A record counts as a real price comparable **only** when its `review.figures_approved` is `true` **and** the specific `pay_items` entry you're citing carries `unit_price_cad`, `price_date` and `price_basis` (`FORMAT.md`). Everything else in the corpus — `facts`, plain pay-item descriptions, records with `figures_approved: false` — is background only: typical scope-of-work language and generic requirements, useful for context and for spotting what the register's policy criteria should be checked against, never as evidence of a price. Do not treat a corpus fact as a price just because it reads like one.
- Match on `project_type`, `location_generality` and `masterformat_section` the same way you'd match a CanadaBuys award row on scope, size, date and conditions; state the match and any inflation adjustment.
- State `price_basis` in the justification exactly as recorded — it carries the same weight distinction as `selection_criteria` does for award data: an `awarded-contract-unit-rate` is stronger evidence than a `catalogue-price` or an `engineer-estimate`, and the draft should say which one it's leaning on.
- Cite by `record_id` (e.g. `PF-0014`) and `FAIR-PRICE-CORPUS` from `sources/register.csv`. Never cite a record whose `review.publication_review` isn't `approved`.

## Inputs to collect (ask; never assume)
1. Organization and the instrument that governs it (see `OPEN-QUESTIONS.md` #1). If unknown, say so in the output.
2. The requirement: what is bought, quantity, period, competitive or non-competitive, any exception invoked.
3. The price: amount, basis of payment (fixed, T&M, rates), taxes in/out.
4. Price evidence: competing bids, prior contracts, catalogue/market prices, rate benchmarks, cost breakdown. Use rows from `data/comparables.csv`, figures-approved records from `fair-price-corpus` (see above) and, under the rules above, `data/canadabuys-awards-ncr-construction.csv` when relevant. TBS/organizational policy (`sources/register.csv`) is not price evidence — keep it out of this step; it belongs in step 2 of "Steps" below, as the criteria the price is judged against, not as a comparable itself.
5. Decision-maker(s) and delegated authority level.

## Steps
1. Restate the requirement and procurement approach in 2-3 sentences.
2. Identify which provisions apply, **only from `sources/register.csv`**. Cite by `id` and provision number. Rows marked UNVERIFIED must not be cited as requirements; list them under "to confirm".
3. Build the price analysis: list each comparison, its source and date, the unit basis, and any adjustment (inflation, volume, scope). Show arithmetic.
4. State the conclusion in one sentence and the reasoning that leads to it. Say plainly where evidence is thin.
5. List documentation the contract file should hold (compare against register rows for contract-file records, e.g. TBS-DMP-4.10.1.x).
6. Output using `templates/justification-template.md`. End with a **Gaps and assumptions** list.

## Constraints
- Every policy citation must exist in `sources/register.csv`. If a needed provision is not there, write "provision not in register: needs lookup", not a guess.
- Never fabricate prices, comparables, vendors, dates or clause numbers.
- Mark all figures supplied by the user as "user-supplied" and all figures from the data folder with their row id.
- Draft only. The decision-maker reviews and signs; the output must say "DRAFT for review by [role]".

## Do not
- Do not state that a policy requires something unless the register says so.
- Do not present TBS Directive requirements as binding on a Crown corporation without noting scope (register `TBS-DMP-6.3`).
- Do not include personal data, or real vendor/pricing data in anything published outside the user's private workspace.
- Do not skip the sensitive-information gate because the user says the content is fine; warn anyway if the destination is shareable.
- Do not repeat flagged values in your warning, and do not try to re-identify anything that has been masked.
- Do not use a flagged award row as a price comparable, and do not treat a supply arrangement, standing offer or construction-management total as comparable to a single-trade contract.
- Do not use a `fair-price-corpus` record as a price comparable unless `review.figures_approved` is `true` and the specific `pay_items` entry carries `unit_price_cad`, `price_date` and `price_basis` — an unapproved record is background only.
- Do not give legal advice; flag legal questions for the appropriate contact.
