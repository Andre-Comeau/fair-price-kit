#!/usr/bin/env python3
"""Filter the CanadaBuys award-notice open data to construction in Ottawa / Gatineau / NCR.

Usage:
  python tools/canadabuys_filter.py SOURCE.csv OUT.csv
  python tools/canadabuys_filter.py --enrich IN.csv OUT.csv [--source-file NAME]

SOURCE is awardNoticeComplete-avisAttributionComplet.csv (or a fiscal-year file) from
https://canadabuys.canada.ca/opendata/pub/ (Open Government Licence - Canada).

Keeps rows whose procurementCategory contains CNST AND whose regionsOfDelivery contains one of
'National Capital Region (NCR)', 'Ottawa', 'Gatineau' (exact match; 'Ontario (except NCR)' and
'Capitale-Nationale' are different places and are not matched).
Writes English fields only. It deliberately DROPS: all contactInfo* columns (named contact persons,
emails, phone numbers: personal information, excluded by the licence), French duplicates, supplier
street addresses and postal codes, and the free-text award description: in this file it is mostly bidding
boilerplate that embeds named contracting officers with their emails and phone numbers (personal information),
and names cannot be removed reliably by pattern. Scope is carried by the title and the UNSPSC/GSIN descriptions.
The price column is totalContractValue (cumulative, includes amendments). contractAmount is kept
only as `contract_amount_raw`: in this file it is 0.00 for most rows, so do not use it as a price.

--enrich recomputes the derived columns (amendment_count, competitive, is_ncc, supplier_key, quality_flags)
of an already filtered CSV with the same logic, so a curated file can be refreshed without re-downloading.

quality_flags (semicolon-separated; exclude flagged rows from price statistics unless you know why):
  total_blank / total_zero / total_negative   the total is missing, zero or negative
  currency_blank                              no currency stated
  framework_not_a_price                       a supply arrangement or standing offer itself (not a contract
                                              against one): its total is a ceiling, a placeholder or zero
  cm_contract_total_may_include_trades        title says "construction management": the total can include
                                              trade work paid through the manager, so it is not comparable
                                              to a single-trade contract
  garbled_text_in_source                      replacement characters in the text
"""
import csv
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

csv.field_size_limit(10**9)
WANT = {"National Capital Region (NCR)", "Ottawa", "Gatineau"}

# output column -> source column
MAP = [
    ("contract_number", "contractNumber-numeroContrat"),
    ("solicitation_number", "solicitationNumber-numeroSollicitation"),
    ("reference_number", "referenceNumber-numeroReference"),
    ("title", "title-titre-eng"),
    ("award_date", "contractAwardDate-dateAttributionContrat"),
    ("publication_date", "publicationDate-datePublication"),
    ("amendment_date", "amendmentDate-dateModification"),
    ("contract_start", "contractStartDate-contratDateDebut"),
    ("contract_end", "contractEndDate-dateFinContrat"),
    ("amendment_number", "amendmentNumber-numeroModification"),
    ("amendment_type", "amendmentType-typeModification-eng"),
    ("total_contract_value", "totalContractValue-valeurTotaleContrat"),
    ("contract_amount_raw", "contractAmount-montantContrat"),
    ("currency", "contractCurrency-contratMonnaie"),
    ("award_status", "awardStatus-attributionStatut-eng"),
    ("instrument_type", "instrumentType-typeInstrument-eng"),
    ("notice_type", "noticeType-avisType-eng"),
    ("procurement_method", "procurementMethod-methodeApprovisionnement-eng"),
    ("selection_criteria", "selectionCriteria-criteresSelection-eng"),
    ("limited_tendering_reason", "limitedTenderingReason-raisonAppelOffresLimite-eng"),
    ("trade_agreements", "tradeAgreements-accordsCommerciaux-eng"),
    ("regions_of_delivery", "regionsOfDelivery-regionsLivraison-eng"),
    ("unspsc", "unspsc"),
    ("unspsc_description", "unspscDescription-eng"),
    ("gsin", "gsin-nibs"),
    ("gsin_description", "gsinDescription-nibsDescription-eng"),
    ("supplier_legal_name", "supplierLegalName-nomLegalFournisseur-eng"),
    ("supplier_city", "supplierAddressCity-fournisseurAdresseVille-eng"),
    ("supplier_province", "supplierAddressProvince-fournisseurAdresseProvince-eng"),
    ("contracting_entity", "contractingEntityName-nomEntitContractante-eng"),
    ("end_user_entity", "endUserEntitiesName-nomEntitesUtilisateurFinal-eng"),
]
EXTRA = ["amendment_count", "competitive", "is_ncc", "supplier_key", "quality_flags", "source_file"]
COLUMNS = [o for o, _ in MAP] + EXTRA

_SUFFIX = {"inc", "incorporated", "ltd", "limited", "ltee", "corp", "corporation", "co", "company", "lp", "llp", "enr"}


def tokens(v):
    return [p.strip() for p in (v or "").replace("\r", "").split("*") if p.strip()]


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def clean(v):
    return " ".join((v or "").replace("\r", " ").replace("\n", " ").split())


def supplier_key(name):
    """Heuristic key for grouping spelling variants of one supplier: accents dropped, lower case, '&'/'and'/'et' and
    punctuation removed, legal suffixes dropped, adjacent single letters joined ("J. P." -> "jp").
    'Black & McDonald Limited' and 'BLACK AND MCDONALD LIMITED' share a key. It is a heuristic: check before merging."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s.replace("&", " and "))
    toks = [t for t in s.split() if t not in _SUFFIX and t not in {"and", "et"}]
    s = " ".join(toks)
    prev = None
    while prev != s:  # join runs of single letters
        prev, s = s, re.sub(r"\b([a-z0-9]) ([a-z0-9])\b", r"\1\2", s)
    return s


MULTI = ["unspsc", "unspsc_description", "gsin", "gsin_description", "trade_agreements", "limited_tendering_reason"]


def derive(row):
    """Set the derived columns from the already-mapped fields (also used by --enrich)."""
    for k in MULTI:  # the source separates several values with '*': make it a readable "a; b; c" (idempotent)
        if "*" in row.get(k, ""):
            row[k] = "; ".join(tokens(row[k]))
    try:
        row["amendment_count"] = int(row["amendment_number"])
    except (ValueError, KeyError):
        row["amendment_count"] = ""
    m = row["procurement_method"]
    row["competitive"] = ("yes" if m.startswith("Competitive") else "no" if m.startswith("Non-competitive")
                          else "advance-notice" if m.startswith("Advance") else "unknown")
    ents = (row["contracting_entity"] + " " + row["end_user_entity"]).lower()
    row["is_ncc"] = "yes" if "national capital commission" in ents else "no"
    flags = []
    t = num(row["total_contract_value"])
    if t is None:
        flags.append("total_blank")
    elif t == 0:
        flags.append("total_zero")
    elif t < 0:
        flags.append("total_negative")
    if not row["currency"]:
        flags.append("currency_blank")
    if row["instrument_type"] in ("Supply Arrangement", "Standing Offer") or \
            row["notice_type"] in ("Request for Supply Arrangement", "Request for Standing Offer"):
        flags.append("framework_not_a_price")
    if re.search(r"construction\s+management", row["title"], re.I):
        flags.append("cm_contract_total_may_include_trades")
    if any("�" in row[k] for k in ("title", "supplier_legal_name", "supplier_city")):
        flags.append("garbled_text_in_source")
    row["supplier_key"] = supplier_key(row["supplier_legal_name"])
    row["quality_flags"] = ";".join(flags)


def write(rows, out):
    rows.sort(key=lambda r: (r["award_date"], r["contract_number"]), reverse=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def enrich(argv):
    a = [x for x in argv if x != "--enrich"]
    source_file = None
    if "--source-file" in a:
        i = a.index("--source-file")
        source_file = a[i + 1]
        a = a[:i] + a[i + 2:]
    if len(a) != 2:
        print(__doc__)
        return 2
    with open(a[0], encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        derive(r)
        if source_file:
            r["source_file"] = source_file
    write(rows, a[1])
    print(f"enriched {len(rows)} rows -> {a[1]}")
    return 0


def main(argv):
    if "--enrich" in argv:
        return enrich(argv)
    if len(argv) != 2:
        print(__doc__)
        return 2
    src, out = Path(argv[0]), Path(argv[1])
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    kept, total = [], 0
    with open(src, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        missing = [s for _, s in MAP if s not in rd.fieldnames]
        if missing:
            print("error: source lacks expected columns:", missing, file=sys.stderr)
            return 2
        for r in rd:
            total += 1
            if "CNST" not in tokens(r["procurementCategory-categorieApprovisionnement"]):
                continue
            if not (WANT & set(tokens(r["regionsOfDelivery-regionsLivraison-eng"]))):
                continue
            row = {o: clean(r[s]) for o, s in MAP}
            row["regions_of_delivery"] = "; ".join(tokens(r["regionsOfDelivery-regionsLivraison-eng"]))
            row["source_file"] = src.name
            derive(row)
            kept.append(row)
    write(kept, out)
    print(f"source rows: {total}; kept: {len(kept)}; wrote {out}")
    print(f"source sha256: {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
