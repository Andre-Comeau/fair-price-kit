# Compliant-data folder

This is the seed of the database you plan to grow. Rules for every row in `comparables.csv`:

- **Public or authorized only.** Use published sources (e.g. PSPC/CanadaBuys award notices, proactive-disclosure contract data, published rate schedules, catalogue prices) or data you are permitted to use. Record where in `source_reference`.
- **One row = one price observation**, with date, unit and scope, so it can be adjusted and compared.
- `synthetic=yes` marks made-up rows used only for examples and tests. Never mix them into a real justification.
- `verified_by` = who checked the row against its source, and when.
- No personal data. Vendor names only if the source is public.

Public reference data lives beside it: `canadabuys-awards-ncr-construction.csv` (125 Ottawa-area construction awards from CanadaBuys open data; read its `.README.md` first, especially the cautions about which value column to use). It is contract-level evidence, not unit prices, so it is a reference table, not part of `comparables.csv`; a comparable row cites a contract number from it.

`canadabuys-tender-attachments-index.csv` lists the public tender-document links (specs, drawings, addenda) attached to those contracts' tender notices: 555 links, 115 of them for NCC. It is an index of links only; nothing was downloaded, the documents are copyright protected, and any you fetch stay private (see `SCOUTING-canadabuys.md`).

Rows may also be derived from the sanitized knowledge base (`ingestion/`), e.g. amounts and unit prices in CO/CD/EA chunks. Cite the chunk id in `source_reference`, carry over the document's own `amount_type`, and never mix `pending` or unreviewed material into this table.

Growth path: comparables -> rate cards by category -> cost-build-up templates (labour, materials, overhead, margin) -> estimating tool. Add each stage only after the previous one has been used on real files.
