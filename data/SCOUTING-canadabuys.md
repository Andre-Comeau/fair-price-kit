# CanadaBuys scouting report (2026-09-21)

Goal: can public CanadaBuys data seed `comparables.csv` with Ottawa-area construction prices? Read-only scouting: website pages, the data dictionary and file headers. **Update: after the scouting the user approved one download; see the result section below.**

## What exists
| Source | What it holds | Notes |
|---|---|---|
| Open-data award notices (CSV) | one row per award or amendment: supplier, contract amount, total contract value, dates, method, selection criteria, region, category, UNSPSC/GSIN, description | Open Government Licence - Canada; updated daily; federal organizations incl. Crown corporations subject to trade agreements; 2012 to present; source: open.canada.ca "CanadaBuys award notices" |
| Open-data tender notices (CSV) | title, description, closing date, region, category, attachment links | no prices |
| Website "Contract history" tab | one row per contract or amendment (e.g. `CW2412616-007`): company, organization, date, amount | 510,110 records nationally; not yet checked whether a CSV of it exists |
| Website award pages | same fields as the CSV, one page per contract | shows "Amendment value" and "Total value of contract" |

Data dictionary: `https://donnees-data.tpsgc-pwgsc.gc.ca/ba2/ac-cb/achatscanada-canadabuys-dd.xml`. Key award fields: `contractAmount-montantContrat` (awarded value **including taxes**), `totalContractValue-valeurTotaleContrat` (initial value plus all amendments), `contractCurrency`, `contractAwardDate`, `amendmentNumber/Type/Date`, `numberOfRecords`, `supplierLegalName/OperatingName/StandardizedName`, `procurementCategory` (CNST = construction), `procurementMethod`, `selectionCriteria`, `limitedTenderingReason`, `regionsOfDelivery`, `gsin`, `unspsc`, `awardDescription`, `solicitationNumber` (use this to link tender and award), `contractNumber`, `contractingEntityName`, `endUserEntitiesName`.

## What does NOT exist
- **No bids received, no number of bidders, no losing bid amounts** in the data dictionary or on an award page checked (a PSPC construction award in the NCR). Only the awarded value is public here.
- No unit prices or itemized breakdowns: a contract-level total plus a short description.
- Amounts are CAD including taxes; other sources may exclude taxes.

## Volume (from the website, filters: Construction + Ottawa / Gatineau / National Capital Region)
Tender notices 1,616 (all statuses); award notices 130; contract-history records 54. The CSVs will hold more rows because each amendment is a row; exact counts need a download. Filter IDs used on the site: category Construction = 155; locations Ottawa = 2011, Gatineau = 2010, NCR = 1527.

## File sizes (header requests, base `https://canadabuys.canada.ca/opendata/pub/`)
| File | Size |
|---|---|
| `awardNoticeComplete-avisAttributionComplet.csv` (2022-08-08 onward) | 101 MB |
| `2012-2022-awardNoticeHistorical-avisAttributionHistorique.csv` | 271 MB |
| `2025-2026-awardNotice-avisAttribution.csv` | 29 MB |
| `2024-2025-...` / `2023-2024-...` / `2022-2023-...` / `2026-2027-...` | 24 / 20 / 20 / 14 MB |

## Fit for fair-and-reasonable work
Useful: market-tested totals for comparable scopes when `procurementMethod` is competitive and `selectionCriteria` is lowest price; amendment values (a proxy for change-order size); supplier and date for inflation adjustment. Weak: scope detail is one paragraph; no line items; a competitive award is the winning price, not the range of bids. Non-competitive rows (`limitedTenderingReason`) must be labelled, not treated as market-tested.
NCC: appears as an organization on award notices (older services notices seen); its recent construction volume is unverified.

## Plan and effort (the estimate made BEFORE the download; the results sections below supersede it)
1. Download `awardNoticeComplete...csv` once (101 MB); filter `procurementCategory` = CNST and `regionsOfDelivery` containing National Capital Region / Ottawa / Gatineau; keep only the filtered CSV (expected small); delete the big file. Machine time: minutes. Optional: the 271 MB historical file (legacy layout, check columns).
2. Extend `data/comparables.csv` columns (contract number, supplier, method, selection criteria, region, UNSPSC/GSIN, amendment flags, source URL, tax basis) and map rows. Public data: no sanitization needed, but keep `synthetic=no` and cite the file and retrieval date.
3. Quality rules: one row per contract with initial and total value separated; amendments kept as their own rows and flagged; competitive vs non-competitive flagged; currency checked; duplicates by `contractNumber` + amendment number removed.
4. Development plus checking: roughly a few hours of work, done here (Python is available on this machine), then the filtered CSV is carried to the target computer.

## Access without a login, and the rules (checked 2026-09-21)
**Data files (open data): public, no login.** The CSVs under `https://canadabuys.canada.ca/opendata/pub/` answered header requests normally. Licence: Open Government Licence - Canada (open.canada.ca). It allows copying, modifying, publishing and using the information for any lawful purpose, including commercial, if you include "Contains information licensed under the Open Government Licence - Canada." (or the provider's own statement); it excludes personal information, third-party rights and official marks, forbids implying government endorsement, and gives the data "as is".

**Notice pages on the website: viewable, but do not crawl.** `robots.txt` names only Googlebot and bingbot (with a crawl delay of 5 and disallowing the tender-notice and award-notice paths) and then says `User-agent: *` / `Disallow: /`, i.e. every other automated client is disallowed from the whole site. The Government of Canada terms page (canada.ca/en/transparency/terms.html) says nothing about scraping, but that does not override robots.txt. Use the open-data files (the official route) and, for a handful of pages, an ordinary browser.

**Tender documents (specs, drawings, addenda): mixed access, and copyright applies.**
- PSPC tenders (SAP Ariba, e.g. the Rideau Committee Room elevator notice): the notice says suppliers must register or log in; the document link leads to an Ariba login. **Not available without a login**, and creating an account is not something to do on your behalf.
- Other notices (`cb-...` type): attachments are direct links under `/sites/default/files/webform/tender_notice/...`. One was reachable with no login (HTTP 200, PDF, 1.6 MB; headers only, not downloaded). Reachable does not mean free to reuse.
- Each tender page says: notices carry the Open Government Licence - Canada; "Related solicitation documents and/or tender attachments are copyright protected". The canada.ca terms allow reproduction for non-commercial purposes with source attribution and require written permission for commercial redistribution, and note that third-party content can be under another party's copyright.
- Consequence: keep any downloaded tender documents private (like project documents), never put them in a public repository, and do not redistribute them. Internal use for price analysis is the low-risk use; confirm with your organization.

## Result of the approved download (2026-09-21)
Downloaded `awardNoticeComplete-avisAttributionComplet.csv` (101 MB, 28,198 rows), filtered to construction in Ottawa / Gatineau / NCR: **125 contracts** (15 NCC), reduced to `data/canadabuys-awards-ncr-construction.csv`; the big file was deleted. Details, caveats and provenance: `data/canadabuys-awards-ncr-construction.README.md`. Findings that change the plan above:
- The CSV is much smaller than the website counts (which cover 2012 onward): 125 rows, not thousands, so processing effort was minutes, not hours.
- `contractAmount` is 0.00 for most rows; the usable price is `totalContractValue` (cumulative, includes amendments). Original value and individual change amounts are not separable here.
- The free-text description embeds named contracting officers with emails and phone numbers, so it was dropped; contact columns were dropped too (personal information is outside the licence).
- The 2012-2022 historical file (271 MB) has not been downloaded.

## Matching check: do the 125 contracts have tender documents? (2026-09-21)
Downloaded `tenderNoticeComplete-avisAppelOffresComplet.csv` (183,077,895 bytes, 30,126 notices) and matched it to the 125 awards by `solicitationNumber` (reference numbers do not link the two files). **122 of 125 contracts (111 of 114 solicitation numbers) matched a tender notice.** The big file was then deleted; **no tender document was downloaded and no attachment link was requested** (robots.txt disallows bulk requests to the site), so file sizes and per-link access are unverified.

| Issuer | Contracts | Matched | With attachment links | Links |
|---|---|---|---|---|
| NCC | 15 | 15 | 15 | 115 (108 pdf, 5 zip, 2 xlsx) |
| National Research Council | 46 | 46 | 46 | 329 |
| Other departments | 22 | 22 | 22 | 111 |
| PSPC | 42 | 39 | 0 | 0 (documents are in SAP Ariba behind a supplier login) |

555 unique links in all, listed in `data/canadabuys-tender-attachments-index.csv` (contract, solicitation, issuer group, file name, type, heuristic hint, URL; public links only, no contact data).
- **NCC packages are real tender documents hosted on CanadaBuys itself** (`canadabuys.canada.ca/sites/default/files/webform/tender_notice/...`; the one link of this kind tested earlier answered without a login). By file name: addenda 42, RFP/ITT 10, forms 10, specification sections/specifications 15 (e.g. numbered Division 01/02 sections), drawings or issued-for-tender sets 12 (e.g. structural, electrical, landscape), surveys 2, geotechnical 1, environmental 2, one site instruction, 19 unclassified. 9 of 15 NCC contracts have spec- or drawing-named files; 3 contain a zip whose contents are unknown. Hints come from file names only.
- These are **pre-award** packages. Change documents that arise after award (CCN, CO, CI, CD, EA) are not published here; the only change-type document seen is a site instruction and addenda.
- Cautions: tender attachments are copyright protected (see above); drawings and reports can carry professional seals and names; specs and drawings still go through the classification-marking check (Gate 0) before any AI tool sees them; treat them as private material, not for the public workshop repo.

## Not checked
Whether a contract-history CSV exists; the file sizes of the 555 attachments and whether every link is reachable without a login (only one link, on a different notice, was tested); what the zip files contain; whether the NCC packages are good enough test material for the ingestion pipeline to justify the copyright and privacy handling.
