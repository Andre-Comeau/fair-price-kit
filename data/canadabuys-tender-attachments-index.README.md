# canadabuys-tender-attachments-index.csv: provenance and how to use it

Contains information licensed under the Open Government Licence – Canada.
This index lists links only. It contains **no tender documents**. It is not an official Government of Canada product and does not imply endorsement.

## What it is
For each of the 125 contracts in `canadabuys-awards-ncr-construction.csv` whose tender notice carries attachment links, one row per public attachment link: contract number, solicitation number, issuer group, title, award date, file name, file type, a heuristic document-type hint, and the URL. 555 links for 83 contracts (NCC 115 links / 15 contracts; National Research Council 329 / 46; other departments 111 / 22). The 42 PSPC contracts have none: PSPC tender documents are in SAP Ariba behind a supplier login.

## Source and method
- Source: `tenderNoticeComplete-avisAppelOffresComplet.csv` (all CanadaBuys tender notices from 2022-08-08; open.canada.ca "CanadaBuys tender notices", Open Government Licence – Canada), downloaded 2026-09-21 from `https://canadabuys.canada.ca/opendata/pub/`; 183,077,895 bytes; 30,126 rows; 67 columns. The file was deleted after use and **its hash was not recorded**, so unlike the awards file this cannot be checked against a re-download byte for byte.
- Method: each award was matched to its tender notice by `solicitationNumber` (reference numbers do not link the two files). 122 of 125 contracts (111 of 114 solicitation numbers) matched. Attachment URLs come from the notice's `attachment-piecesJointes-eng` field, de-duplicated per contract.
- `name_hint` comes from the file name only (addendum, specification section, drawing, survey, geotechnical, and so on); it is a guess, and about 30% of names are unclassified. A zip file's contents are unknown.

## Rules for using it (read before you fetch anything)
1. **The documents are copyright protected.** Each CanadaBuys tender page says notices carry the Open Government Licence – Canada but "related solicitation documents and/or tender attachments are copyright protected". Fetch only for your own internal use, never republish or redistribute them, and follow the Government of Canada terms (non-commercial reproduction with attribution; commercial redistribution needs permission).
2. **Do not crawl.** CanadaBuys `robots.txt` disallows all automated clients except Googlebot and Bingbot. Fetching a handful of files you actually need, by hand or with a single-file request, is a different thing from bulk retrieval; do not script bulk downloads.
3. **Links can go stale or need a login.** Only one attachment link (on another notice) was tested for open access; the others are unverified. PSPC/Ariba documents are not reachable without an account.
4. **Documents can carry personal information** (named staff, professional seals, signatures). Run the ingestion rulebook (`ingestion/RULEBOOK.md`), including its stop rules, before an AI tool sees them.
