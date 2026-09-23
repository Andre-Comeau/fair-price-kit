# Notices: copyright, data licences and disclaimers

Read this before you use, copy or redistribute anything in this repository.

## 1. What the MIT license covers, and what it does not
The original code, documents and templates written for this repository are © 2026 Andre-Comeau and licensed under the MIT License (`LICENSE`). Parts of this repository were drafted with the assistance of an AI model (Claude, by Anthropic); everything in it should be reviewed by a person before you rely on it.

The MIT license does **not** cover the third-party material described below. It stays under the terms of its owners.

## 2. CanadaBuys data (Open Government Licence – Canada)
The files `data/canadabuys-awards-ncr-construction.csv` and `data/canadabuys-tender-attachments-index.csv` are derived from the CanadaBuys open-data files published by Public Services and Procurement Canada:
- CanadaBuys award notices: <https://open.canada.ca/data/en/dataset/a1acb126-9ce8-40a9-b889-5da2b1dd20cb>
- CanadaBuys tender notices: <https://open.canada.ca/data/en/dataset/6abd20d4-7a1c-4b38-baa2-9525d0bb2fd2>

**Contains information licensed under the Open Government Licence – Canada** (<https://open.canada.ca/en/open-government-licence-canada>).

The licence lets you copy, modify, publish and use the information for any lawful purpose, including commercially, provided you keep this attribution. It excludes personal information, third-party rights and official marks, and it forbids implying government endorsement.

Changes made here: the data were filtered (construction, Ottawa / Gatineau / National Capital Region), reduced (contact-person columns, free-text descriptions, French duplicates, supplier street addresses and postal codes were removed because they can contain personal information) and extended with derived columns (for example `quality_flags`, `supplier_key`, `competitive`). This is not an official Government of Canada product, it may contain errors introduced by filtering or present in the source, and it does not imply endorsement by the Government of Canada, PSPC or any organization named in it. Details and cautions: `data/canadabuys-awards-ncr-construction.README.md` and `data/canadabuys-tender-attachments-index.README.md`.

## 3. Tender documents are not included and are copyright protected
This repository contains **links only** (`data/canadabuys-tender-attachments-index.csv`), never the tender documents (specifications, drawings, addenda, reports) themselves. CanadaBuys states on its notices that "related solicitation documents and/or tender attachments are copyright protected". Their copyright belongs to the issuing organizations and their consultants. If you download any, use them for your own internal purposes, do not republish or redistribute them, and follow the Government of Canada terms (<https://www.canada.ca/en/transparency/terms.html>): non-commercial reproduction is allowed with attribution and the source; commercial redistribution needs prior written permission. CanadaBuys' `robots.txt` disallows automated crawling of the site: do not script bulk downloads.

## 4. Statistics Canada data (Statistics Canada Open Licence)
`data/statcan-ippi-construction.csv` is derived from the Statistics Canada Industrial Product Price
Index (table 18-10-0266-01): <https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810026601>.

Source: Statistics Canada, Industrial product price index, by product, monthly, 2026-09. Reproduced
and distributed on an "as is" basis with the permission of Statistics Canada
(<https://www.statcan.gc.ca/en/reference/licence>).

The licence lets you use, reproduce, publish, distribute or sell the information and value-added
products, provided you keep this attribution, reproduce it accurately, don't misrepresent it or its
source, and don't use it in a way that suggests Statistics Canada endorses you or your use of it.
Changes made here: the full table (all products, all months back to 1956) was filtered to five
construction-relevant NAPCS product groups and to 2015-01 onward. Details and cautions:
`data/statcan-ippi-construction.README.md`.

## 5. Government of Canada policy text
`sources/register.csv` records short paraphrases and section references from Treasury Board of Canada Secretariat instruments (Directive on the Management of Procurement, Standard on Security Categorization, Guide on the use of generative artificial intelligence), with the title, section, URL and the date each was read. The originals are © His Majesty the King in right of Canada, as represented by the President of the Treasury Board (or the Government of Canada), and are cited under the Government of Canada terms for non-commercial reproduction (title, author and source URL given). These paraphrases are **not the official text and may be out of date**: always read the source. If you intend commercial redistribution of policy text, obtain permission first.

## 6. Names, marks and affiliations
This repository is independent. It is not affiliated with, endorsed by or sponsored by the Government of Canada, the National Capital Commission, Public Services and Procurement Canada, Treasury Board, Microsoft, Anthropic, GitHub or the authors of any tool it mentions. The National Capital Commission (a federal Crown corporation) appears as a **worked example**, using only public information; nothing here states or implies that any person works for, with or on behalf of it. CanadaBuys, NCC, Government of Canada marks, Microsoft, Copilot, Power Automate, SharePoint, Outlook, Teams, Claude, GitHub and MasterFormat (a publication and mark of the Construction Specifications Institute and Construction Specifications Canada) belong to their respective owners.

## 7. External tools
No third-party software is bundled. The scripts are pure Python (standard library) and call `pdftotext` (poppler) only if you have installed it; `pypdf` is used only if you have installed it. Their own licences apply.

## 8. Disclaimer
This repository is a working draft. It is not legal, procurement, security or financial advice. Outputs it helps produce are drafts for review by the accountable person. Nothing here has been approved by any organization's security, privacy or legal function. You are responsible for checking your organization's rules, and for the classification, privacy and copyright of every document you process.
