# Candidate public data sources (survey of 2026-09-21)

Goal: find public, reusable data to add to the kit's database beyond the 125 CanadaBuys awards. Nothing here was downloaded or ingested; this is a survey. "Verified" means I read the source page or queried the live API on 2026-09-21; "search only" means the fact comes from a search-result summary and must be checked at the source before use. Register ids are in `sources/register.csv`.

## What the current data lacks, and which source fills it
| Gap in the current data | Source that fills it | Verified? |
|---|---|---|
| Change-order (amendment) values, separate from the original value | Federal proactive contracts dataset (`original_value`, `amendment_value`, `contract_value`); CanadaBuys contract history (a row per contract or amendment) | verified |
| Number of bids received | Federal proactive contracts dataset (`number_of_bids`, populated in recent quarters) | verified (live API) |
| Escalation: adjusting an old price to today | Statistics Canada building construction price indexes (table 18-10-0289-01) | table id and coverage from search results; active table page not read |
| Labour rates | Statistics Canada construction union wage rates (18-10-0139-01) and index (18-10-0140-01); Job Bank wages (ESDC) | verified pages |
| Equipment rates | Ontario MTO OPSS.PROV 127 rental-rate schedule | search only |
| Bid amounts (not just counts) | none found openly (see "Assessed and not recommended") | |

## Ranked candidates

### 1. Federal "Proactive Publication – Contracts" (contracts over $10,000): **highest value**
- What: one row per contract or amendment reported by federal entities; quarterly; Open Government Licence – Canada; over 100,000 rows. Dataset: <https://open.canada.ca/data/en/dataset/d8f85d91-7dec-4fd1-8055-483b77225d8b>. Register id `FED-PROACTIVE-CONTRACTS`.
- Fields (read from the live API, 2026-09-21): `reference_number`, `procurement_id`, `vendor_name`, `vendor_postal_code`, `buyer_name`, `contract_date`, `economic_object_code`, `description_en`, `contract_period_start`, `delivery_date`, **`contract_value`**, **`original_value`**, **`amendment_value`** (negative for reductions), `commodity_type` (the value `C` appears on rows described as buildings, roads and construction services; the dictionary lists Good, Service or Construction), `commodity_code`, `solicitation_procedure` (coded, e.g. TC, TN), `limited_tendering_reason`, `award_criteria` (coded), **`number_of_bids`**, `instrument_type`, `standing_offer_number`, `trade_agreement`, `contracting_entity`, `reporting_period`, `owner_org`, `owner_org_title`, and others.
- Fit: amendment values give the size of changes; bid counts show how competitive an award was. Test query: 20,886 records with `owner_org = pwgsc-tpsgc` and `commodity_type = C`; the newest (2026-2027 Q1) show bid counts of 0 to 3 and separate original, amendment and total values.
- Cautions: the publisher states the data are unaudited with no warranty. `description_en` is an economic-object description ("Office buildings", "Highways, roads and streets"), not a project title. There is **no project location field** (only the vendor's postal code), so "Ottawa area" cannot be filtered directly. Older rows have no bid count. The `award_criteria` and `solicitation_procedure` codes need the data dictionary (<https://open.canada.ca/data/recombinant-published-dictionary/contracts>, not read). A free-text search is disabled on this large table; use filters (institution codes such as `pwgsc-tpsgc`).
- NCC: a filter on the code `ncc-ccn` returned 0 records. That may be the wrong code or may mean Crown corporations are not in this dataset; NCC's own disclosure page (<https://ncc-ccn.gc.ca/proactive-disclosure>) showed no contracts section in the text I could read. **Unresolved.** NCC's competitive awards do appear in the CanadaBuys awards already in the kit.
- Effort (estimate): a filtered extract by institution and commodity type through the API, a small script, a data README with cautions: a few hours. The largest work is deciding which institutions and periods to include.

### 2. CanadaBuys contract history (PSPC-awarded contracts, per amendment)
- What: contracts PSPC awarded for departments since January 2009; monthly; Open Government Licence – Canada; CSV files: `contractHistoryComplete-contratsOctroyesComplet.csv` (from 2023-06-01), a legacy file for 2009 to 2023-05, and fiscal-year files, all under `https://canadabuys.canada.ca/opendata/pub/`. Dataset: <https://open.canada.ca/data/en/dataset/4fe645a1-ffcd-40c1-9385-2c771be956a4>. Register id `CANADABUYS-CONTRACT-HISTORY`.
- Fit: this is the per-amendment record that the awards file lacks (the website's "contract history" tab, 510,110 records). It would let the kit split a contract's total into its original value and each change, and would match the 125 awards by contract number.
- Cautions: compiled from several procurement systems, so some fields are blank; only PSPC-awarded contracts (not NCC's own). File sizes not checked. The same rules as the awards data apply (Open Government Licence attribution; no bulk crawling of the site pages; use the published files).
- Effort (estimate): download, filter to the 125 contract numbers, add a derived table of amendments: about a day, mostly checking data quality.

### 3. Statistics Canada: Building construction price indexes (escalation)
- What: quarterly indexes of the prices contractors charge to build several residential and non-residential building types, by type of building and construction division, for 11 metropolitan areas including **Ottawa–Gatineau (Ontario part)**. The active table is **18-10-0289-01** (base 2023 = 100, quarterly from Q1 1981, releases through Q2 2026), with a percent-change table 18-10-0289-02; older tables 18-10-0135-01 and 18-10-0276-01 are archived. Page: <https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810028901>. Register id `STATCAN-BCPI`.
- Fit: this is the "inflation adjustment from a source you name" that `SKILL.md` requires and that the kit does not yet have. It adjusts an old award to a current price level by building type in the local market.
- Cautions: Statistics Canada indexes measure price change for a set of model buildings, not the price of a specific project. Confirm the licence wording (Statistics Canada Open Licence) and the exact building types on the table page (I read the archived table's page and the search summaries, not the active page).
- Effort (estimate): small: a CSV of the Ottawa–Gatineau non-residential series plus a README: an hour or two.

### 4. Statistics Canada: construction union wage rates and index (labour)
- What: hourly collective-agreement wage rates for construction trades by census metropolitan area, monthly from January 1971 (table **18-10-0139-01**, latest release 2026-07-17), and an index (**18-10-0140-01**, base reported as 2015 = 100). Page read: <https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810013901>. Register id `STATCAN-CUWR`.
- Fit: labour-rate reference and a labour escalation series. The page's visible text did not list which metropolitan areas or trades are included; confirm that Ottawa–Gatineau and the trades you need are present.

### 5. Job Bank wages (Employment and Social Development Canada)
- What: minimum, median and maximum wage estimates by National Occupational Classification occupation and region, annual, 2012 to 2025, CSV; Open Government Licence – Canada. Dataset: <https://open.canada.ca/data/en/dataset/adad580f-76b0-4502-bd05-20c125de9116>. Register id `JOBBANK-WAGES`.
- Fit: a market wage check for trades and professionals (all sectors, not only union). Cautions: estimates from survey data, regional rather than project-specific.

### 6. Ontario MTO OPSS.PROV 127 "Schedule of Rental Rates for Construction Equipment" (equipment)
- What: hourly rental rates for more than 175 equipment categories, used for time-and-material payment on MTO contracts; a public PDF, July 2025 edition (search results). Register id `OPSS-127` (search only).
- Fit: an equipment-rate benchmark for time-and-material or cost-plus pricing. Cautions: copyright is Ontario's; confirm reuse terms before copying any table into the repository (linking is safe). Not verified beyond search results.

### 7. Infrastructure programme project data (Housing, Infrastructure and Communities Canada)
- What: approved projects from the Investing in Canada Infrastructure Program with location, funding stream and total eligible cost, updated weekly, published on the Open Government Portal (search results). The dataset id was not confirmed.
- Fit: whole-project cost benchmarks by project type and location. Cautions: eligible cost is not contract price; verify the dataset and fields before use.

## Assessed and not recommended (or unresolved)
- **City of Ottawa bid results:** unofficial bid results are posted when tenders close (construction adjusted results on MERX); older results are available on request by email. No open dataset was found. A "Contracts of significant public interest" page lists only a handful of large contracts. Delegation-of-authority reports for awards over $25,000 exist but their format and licence were not checked. Low fit.
- **MERX, Biddingo and similar portals:** registration or paid access; not open data.
- **CanadaBuys standing offers and supply arrangements:** lists the holders, not their rates.
- **Ontario MTO tender results with bidder amounts:** a search found none.
- **Bid amounts:** none of the sources above publishes losing bid amounts. Bid counts (source 1) are the closest.

## Known but not checked (labelled so you do not mistake them for findings)
Statistics Canada consumer price index and industrial product price indexes (general and materials inflation); Government of Canada "Guide to Proactive Publication" (<https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32763>) for the meaning of the coded fields.

## Suggested order
1. Federal proactive contracts (bids and amendments) and CanadaBuys contract history (per-amendment values for the awards already in the kit).
2. The Statistics Canada Ottawa–Gatineau construction price series (escalation).
3. Labour rates (union wage table, Job Bank).
4. Equipment rates and infrastructure project data after their reuse terms and fields are confirmed.

Before any of this is loaded: read each source's licence and terms, keep the attribution statement required by the Open Government Licence – Canada, exclude personal information (vendor names of sole proprietors, contact fields), and update `NOTICE.md`, `sources/register.csv` and the kit's data README for each file added.
