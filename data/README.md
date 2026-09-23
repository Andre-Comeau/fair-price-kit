# Compliant-data folder

This is the seed of the database you plan to grow. Rules for every row in `comparables.csv`:

- **Public or authorized only.** Use published sources (e.g. PSPC/CanadaBuys award notices, proactive-disclosure contract data, published rate schedules, catalogue prices) or data you are permitted to use. Record where in `source_reference`.
- **One row = one price observation**, with date, unit and scope, so it can be adjusted and compared.
- `synthetic=yes` marks made-up rows used only for examples and tests. Never mix them into a real justification.
- `verified_by` = who checked the row against its source, and when.
- No personal data. Vendor names only if the source is public.

Public reference data lives beside it: `canadabuys-awards-ncr-construction.csv` (125 Ottawa-area construction awards from CanadaBuys open data; read its `.README.md` first, especially the cautions about which value column to use). It is contract-level evidence, not unit prices, so it is a reference table, not part of `comparables.csv`; a comparable row cites a contract number from it.

`canadabuys-tender-attachments-index.csv` lists the public tender-document links (specs, drawings, addenda) attached to those contracts' tender notices: 555 links, 115 of them for NCC. It is an index of links only; nothing was downloaded, the documents are copyright protected, and any you fetch stay private (see `SCOUTING-canadabuys.md`).

`statcan-ippi-construction.csv` (Statistics Canada Industrial Product Price Index, filtered to the
five construction-relevant commodity groups; read its `.README.md` first) is materials-cost movement
to inflation-adjust a comparable with, not a comparable itself — never cite it as a price.

Further public sources worth adding (with what each fills, licence and cautions) are surveyed in `SOURCES-candidates.md`.

Rows may also be derived from the sanitized knowledge base (`ingestion/`), e.g. amounts and unit prices in CO/CD/EA chunks. Cite the chunk id in `source_reference`, carry over the document's own `amount_type`, and never mix `pending` or unreviewed material into this table.

A companion repository, `fair-price-corpus` (private, separate from this one), is where generic facts extracted from sanitized project documents accumulate once they pass both the sensitive-information gate here and its own publication-review gate — section titles, generic pay-item descriptions, generalized requirements, not the source documents themselves (sanitizing for privacy does not clear copyright over the document's own wording; see that repo's `NOTICE.md`). This is separate from `comparables.csv` above and from the CanadaBuys data. Most of it is background context, not price evidence — sanitizing away a record's specific numbers is what makes it safe to publish, and that's also what makes it useless as a price comparable by default. A record can carry an actual reviewed unit price (`figures_approved: true`, see that repo's `FORMAT.md` and `gates/publication-review.md`), and only then is it used by `SKILL.md`'s drafting step as a real comparable, on the same footing as an award-data row.

Growth path: comparables -> rate cards by category -> cost-build-up templates (labour, materials, overhead, margin) -> estimating tool. Add each stage only after the previous one has been used on real files.
