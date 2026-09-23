# statcan-ippi-construction.csv: provenance and how to use it

Source: Statistics Canada, Industrial product price index, by product, monthly (table 18-10-0266-01), 2026-09.
Reproduced and distributed on an "as is" basis with the permission of Statistics Canada.

This is a filtered, reduced copy made by the kit's own script. It is not an official Statistics Canada
product; it may contain errors introduced by filtering, and it does not imply endorsement by
Statistics Canada. Check any figure against the source table before relying on it.

## What this is, and what it is not
The Industrial Product Price Index (IPPI) measures month-to-month **price change for a commodity**,
Canada-wide (e.g. "softwood lumber is up 4% since last quarter"). It is not the price of a building, a
project, or a specific material delivered to a specific site, and it carries no regional breakdown
(national only). Use it to **inflation-adjust a materials-cost component of an existing comparable**
(escalate an old catalogue price or quote forward, or deflate a recent one back, to compare like with
like) — never present an index value itself as a price, and never as a substitute for
`STATCAN-BCPI` (building construction price indexes, Ottawa–Gatineau, a different and complementary
series measuring what contractors charge to build, not what materials cost).

## Source
- Dataset: Statistics Canada, Industrial product price index, by product, monthly. Register id
  `STATCAN-IPPI`; licence register id `STATCAN-OPEN-LICENCE`.
- Table id 18-10-0266-01 (pid `18100266` in the Web Data Service API); table page
  <https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810026601>.
- Full table downloaded 2026-09-23 via the WDS API
  (`https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/18100266/en`), which returned
  `https://www150.statcan.gc.ca/n1/tbl/csv/18100266-eng.zip`; 2,149,078 bytes; the extracted data file
  `18100266.csv` is 20,531,947 bytes, SHA-256
  `bd4240a72e18341fd6f1c04696932474c07bdb89f2f24991df6168d6e842accf`; 125,382 rows, all products, all
  months back to 1956-01. (The source files were deleted after filtering; the hash lets you confirm a
  re-download.)
- Filter (script `tools/statcan_ippi_filter.py`): keeps every NAPCS product code that is, or
  descends from (per the table's own metadata hierarchy), one of five top-level groups: **P41**
  (lumber and other wood products), **P61** (primary ferrous metal products), **P62** (primary
  non-ferrous metal products), **P63** (fabricated metal products and construction materials), **P81**
  (cement, glass, and other non-metallic mineral products) — the groups StatCan's own release notes
  identify as construction-relevant. Rows before 2015-01 are dropped (the default `--min-date`); the
  earliest CanadaBuys award in this kit is from 2022, so 2015 gives several years of padding for
  adjusting an older comparable without carrying 70 years of history no comparable here will need.
- Result: **11,060 rows**, 79 distinct products (every level of aggregation StatCan publishes within
  the five groups, from the group total down to individual products — not leaves only), monthly,
  2015-01 to 2026-08 (release 2026-09-17).
- Reproduce or refresh: download the zip from the WDS URL above, extract both CSVs, then
  `python tools/statcan_ippi_filter.py 18100266.csv 18100266_MetaData.csv OUT.csv`.

## Columns
`ref_date` (YYYY-MM), `napcs_group` (P41/P61/P62/P63/P81), `napcs_group_name`, `product` (name and
NAPCS code, e.g. `"Softwood lumber (except tongue and groove and other edge worked lumber) [24112]"`
— note some rows are the group total itself, e.g. `"Lumber and other wood products [P41]"`, and others
are intermediate aggregates, not just bottom-level products; read the name), `uom` (always
`Index, 202001=100` in this file: base period January 2020 = 100), `value` (the index value; blank
means not available for that product/month), `vector` and `coordinate` (StatCan's own series
identifiers, for citing or re-querying a specific series via the WDS API), `status` (StatCan's data
quality symbol, usually blank; `E` = use with caution and similar codes are StatCan's own, not this
kit's), `terminated` (non-blank if StatCan stopped publishing that series; check before using a recent
month from a terminated series).

## How to use it for an inflation adjustment
1. Pick the product row closest to what the comparable is actually made of (e.g. a lumber-heavy
   scope: `napcs_group = P41`; structural steel: `P61` or `P63`). Prefer a specific product over the
   group total when one clearly fits; state which you used.
2. Find the index `value` at the comparable's own date and at the date you're adjusting to.
3. `adjusted_price = original_price * (value_at_target_date / value_at_original_date)`. Show this
   arithmetic in the justification (`SKILL.md` step 3), and name the exact product row and both dates
   used.
4. This adjusts materials-cost movement only — it does not capture labour, site conditions, scope
   changes or anything else that differs between the comparable and the current requirement. Say so.

## Cautions
1. **National index, not regional.** No Ottawa/Gatineau or Ontario breakdown exists in this table;
   `STATCAN-BCPI` is regional (11 CMAs including Ottawa–Gatineau) but measures a different thing
   (building price, not materials price). Neither substitutes for the other.
2. A row with a blank `value` means the series has no published value for that month (a gap, not
   zero) — do not treat a blank as 0.
3. Some products in this file appear only because StatCan's own hierarchy nests them under a
   construction-relevant group (e.g. certain waste/scrap and paperboard products nest under P41,
   `Lumber and other wood products`) — read the exact product name, not just which group it's in,
   before using it.
4. This is one component of cost movement. Do not present an IPPI adjustment as a complete escalation
   of a whole project price; state plainly that it covers materials only.

## Citing a row
Cite as `STATCAN-IPPI`, the exact product name and NAPCS code, the two dates compared, and the
retrieval date (2026-09-23). Keep the Statistics Canada Open Licence attribution at the top of this
page if you republish data from this file.
