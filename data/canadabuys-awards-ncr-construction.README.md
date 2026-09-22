# canadabuys-awards-ncr-construction.csv: provenance and how to use it

Contains information licensed under the Open Government Licence – Canada.
This is a filtered, reduced copy made by the kit's own script. It is not an official Government of Canada product, it may contain errors introduced by filtering or by the source, and it does not imply endorsement by the Government of Canada, PSPC or any organization named in it. Check any figure against the source notice before relying on it.

## Source
- Dataset: CanadaBuys award notices (Public Services and Procurement Canada), open.canada.ca. Register id `CANADABUYS-AWARD-DATA`; licence register id `OGL-CANADA`.
- File: `awardNoticeComplete-avisAttributionComplet.csv` (all notices from 2022-08-08), downloaded 2026-09-21 from `https://canadabuys.canada.ca/opendata/pub/`; 101,408,154 bytes; SHA-256 `1f67eb5bb881d8fdd138236f8c05b49433492d8095cfc142a79b208570fc3b2c`; 28,198 rows, 80 columns. (The source file was deleted after filtering; the hash lets you confirm a re-download.)
- Filter (script `tools/canadabuys_filter.py`): `procurementCategory` contains CNST **and** `regionsOfDelivery` contains exactly one of "National Capital Region (NCR)", "Ottawa", "Gatineau". Not matched: "Ontario (except NCR)", "Capitale-Nationale (Québec)".
- Result: **125 rows** (one row per contract, showing that contract's latest state), 37 columns, awards 2022 to 2026 (2022: 1, 2023: 25, 2024: 30, 2025: 40, 2026: 29). Issuing entities: National Research Council 46, PSPC 42, NCC 15 (`is_ncc = yes`), others 22.
- Reproduce or refresh: `python tools/canadabuys_filter.py SOURCE.csv OUT.csv`. To recompute only the derived columns of this file: `python tools/canadabuys_filter.py --enrich data/canadabuys-awards-ncr-construction.csv OUT.csv`.

## What was removed, and why
- All `contactInfo*` columns: named contracting officers with email and phone (personal information; the licence excludes it).
- The free-text award description: in this file it is mostly bidding boilerplate that embeds named contracting officers with emails and phone numbers (36 of 125 rows contained an email or phone). Names cannot be removed reliably by pattern, so the whole field is dropped. The title and the UNSPSC/GSIN descriptions carry the scope.
- French duplicate columns, supplier street addresses and postal codes.
- After filtering, the kit's scanner found no email, phone, URL or postal code in the file. All 100 supplier names are businesses (some embed an owner's name in the company name, which is how the business is registered). The file cannot tell a sole proprietor from a company; if that matters to you, review the names before republishing.

## Columns you will use
`total_contract_value` (**the price field**: cumulative value including all amendments, CAD), `contract_number`, `solicitation_number`, `title`, `award_date`, `amendment_number` / `amendment_count` (0 = never amended), `instrument_type`, `notice_type`, `procurement_method`, `competitive`, `selection_criteria`, `limited_tendering_reason`, `regions_of_delivery`, `unspsc` + `unspsc_description`, `gsin` + `gsin_description`, `supplier_legal_name`, `supplier_key`, `supplier_city` / `supplier_province`, `contracting_entity`, `end_user_entity`, `is_ncc`, `quality_flags`, `source_file`.
`supplier_key` is a heuristic grouping key (lower case, accents and punctuation dropped, `&` and `and` removed, legal suffixes dropped, adjacent single letters joined). It merges eight sets of spelling variants (100 legal-name spellings become 90 keys), for example three spellings of one contractor. Check before merging suppliers in an analysis.

## Quality flags (`quality_flags`, semicolon-separated; 21 of 125 rows carry at least one)
| Flag | Rows | Meaning |
|---|---|---|
| `total_zero` | 14 | the total is 0.00: no usable value |
| `currency_blank` | 1 | no currency stated |
| `framework_not_a_price` | 14 | a supply arrangement or standing offer itself (not a contract against one): the total is a ceiling, a placeholder or zero. Contracts *against* a supply arrangement are ordinary contracts and are not flagged |
| `cm_contract_total_may_include_trades` | 6 | the title says "construction management": the total can include trade work paid through the manager (the two largest totals in the file, about 768.6 and 78.2 million, are of this kind), so it is not comparable to a single-trade contract |

The 104 unflagged rows are the usable population for price statistics.

## Cautions (read before using a number)
1. **`contract_amount_raw` is not a price.** The data dictionary says `contractAmount` is the contract's value including taxes, but in this file it is 0.00 for most rows (27 of the 32 never-amended rows). Use `total_contract_value`.
2. **`total_contract_value` is cumulative.** For an amended contract (`amendment_count` > 0) it includes every amendment, and this file does not give the original value or the individual change amounts. (The CanadaBuys website's "contract history" pages show per-amendment values but are not crawlable: see `SCOUTING-canadabuys.md`.)
3. **Tax basis of the total is not stated** in the dictionary; only `contractAmount` is described as including taxes. Treat the basis as unknown until confirmed.
4. **Winning value only.** No bids received, number of bidders or losing bids exist in the data.
5. **Some rows are not construction projects in the usual sense** even though they carry the construction category (e.g. a locksmith service, a standing offer for filters, water-treatment maintenance). Read the title before using a row.
6. Competitive method: 124 rows competitive, 1 advance contract award notice (an intended non-competitive award, `competitive = advance-notice`). Selection criteria: lowest price 73, highest combined rating of technical merit and price 24, not applicable 13, variations or combinations 11, blank 3, lowest cost-per-point 1. A lowest-price competitive award is the strongest market-tested signal (71 of the unflagged rows are competitive and lowest-price); other criteria mix price with quality.
7. Distribution of `total_contract_value` (CAD; nearest-rank quantiles, index `int(p*(n-1))`): the 111 rows above zero have 25th percentile 180,442, median 416,843, 75th percentile 1,399,300, maximum 768,607,087. The 104 unflagged rows have 25th percentile 173,484, median 393,584, 75th percentile 1,080,068, maximum 30,144,904.
8. Scope detail is thin (title and commodity codes). A comparable needs judgment: match on scope, size, date and conditions, then adjust for inflation.

## Citing a row
Cite as `CANADABUYS-AWARD-DATA` + contract number + retrieval date (2026-09-21), and carry the row's `competitive`, `selection_criteria` and `quality_flags` into any comparable you build in `comparables.csv`. If you republish data from this file, keep the attribution statement at the top of this page.
