#!/usr/bin/env python3
"""Regression tests for tools/canadabuys_filter.py. All rows are invented.
Run: python tools/test/test_canadabuys_filter.py"""
import csv
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import canadabuys_filter as cf  # noqa: E402

_DIRS = []  # temporary folders, removed at the end


def newdir():
    d = Path(tempfile.mkdtemp())
    _DIRS.append(d)
    return d


CAT, REG = "procurementCategory-categorieApprovisionnement", "regionsOfDelivery-regionsLivraison-eng"


def src_row(**kw):
    base = {s: "" for _, s in cf.MAP}
    base.update({CAT: "*CNST", REG: "National Capital Region (NCR)", "contractNumber-numeroContrat": "X-1",
                 "contractAwardDate-dateAttributionContrat": "2025-01-01", "totalContractValue-valeurTotaleContrat": "1000.00",
                 "contractCurrency-contratMonnaie": "CAD", "title-titre-eng": "Test project",
                 "procurementMethod-methodeApprovisionnement-eng": "Competitive - Open bidding",
                 "supplierLegalName-nomLegalFournisseur-eng": "Black & McDonald Limited"})
    base.update(kw)
    return base


def run(rows):
    d = newdir()
    src, out = d / "src.csv", d / "out.csv"
    cols = [s for _, s in cf.MAP] + [CAT, REG]
    with open(src, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    assert cf.main([str(src), str(out)]) == 0
    return {r["contract_number"]: r for r in csv.DictReader(open(out, encoding="utf-8-sig", newline=""))}


def main():
    bad = []
    rows = [
        src_row(**{"contractNumber-numeroContrat": "KEEP-NCR"}),
        src_row(**{"contractNumber-numeroContrat": "KEEP-OTTAWA", REG: "*Canada\n*Ottawa"}),
        src_row(**{"contractNumber-numeroContrat": "DROP-ONT", REG: "Ontario (except NCR)"}),
        src_row(**{"contractNumber-numeroContrat": "DROP-QC", REG: "Capitale-Nationale (Québec)"}),
        src_row(**{"contractNumber-numeroContrat": "DROP-GOODS", CAT: "*GD"}),
        src_row(**{"contractNumber-numeroContrat": "FW", "instrumentType-typeInstrument-eng": "Supply Arrangement",
                   "totalContractValue-valeurTotaleContrat": "0.00"}),
        src_row(**{"contractNumber-numeroContrat": "AGAINST-SA", "instrumentType-typeInstrument-eng": "Contract against SA"}),
        src_row(**{"contractNumber-numeroContrat": "CM", "title-titre-eng": "Construction  Management Services"}),
        src_row(**{"contractNumber-numeroContrat": "MULTI", "unspsc": "*72120000\n*72130000",
                   "tradeAgreements-accordsCommerciaux-eng": "*CFTA\n*CUSMA"}),
        src_row(**{"contractNumber-numeroContrat": "NOCUR", "contractCurrency-contratMonnaie": ""}),
    ]
    got = run(rows)
    if set(got) != {"KEEP-NCR", "KEEP-OTTAWA", "FW", "AGAINST-SA", "CM", "MULTI", "NOCUR"}:
        bad.append(("row selection", sorted(got)))
    fl = lambda k: set(filter(None, got[k]["quality_flags"].split(";")))
    if fl("FW") != {"total_zero", "framework_not_a_price"}:
        bad.append(("framework flag", fl("FW")))
    if "framework_not_a_price" in fl("AGAINST-SA"):
        bad.append(("a contract against a supply arrangement is not a framework", fl("AGAINST-SA")))
    if "cm_contract_total_may_include_trades" not in fl("CM"):
        bad.append(("construction management flag", fl("CM")))
    if fl("KEEP-NCR"):
        bad.append(("clean row must have no flags", fl("KEEP-NCR")))
    if fl("NOCUR") != {"currency_blank"}:
        bad.append(("currency flag", fl("NOCUR")))
    if got["MULTI"]["unspsc"] != "72120000; 72130000" or got["MULTI"]["trade_agreements"] != "CFTA; CUSMA":
        bad.append(("multi-value cleanup", got["MULTI"]["unspsc"], got["MULTI"]["trade_agreements"]))
    if got["KEEP-OTTAWA"]["regions_of_delivery"] != "Canada; Ottawa":
        bad.append(("regions cleanup", got["KEEP-OTTAWA"]["regions_of_delivery"]))
    # supplier key: spelling variants of one firm share a key; different firms do not
    same = ["Black & McDonald Limited", "BLACK AND MCDONALD LIMITED", "Black and McDonald Ltd."]
    if len({cf.supplier_key(n) for n in same}) != 1:
        bad.append(("supplier key variants", [cf.supplier_key(n) for n in same]))
    if cf.supplier_key("J.P Gravel Construction Inc.") != cf.supplier_key("JP Gravel Construction Inc."):
        bad.append(("single-letter join", None))
    if cf.supplier_key("Brawn Construction Ltd") == cf.supplier_key("Black & McDonald Limited"):
        bad.append(("different firms must differ", None))
    # enrich is idempotent and keeps the column set
    d = newdir()
    a, b = d / "a.csv", d / "b.csv"
    first = run(rows)
    with open(a, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cf.COLUMNS)
        w.writeheader()
        w.writerows(first.values())
    assert cf.main(["--enrich", str(a), str(b)]) == 0
    if a.read_text(encoding="utf-8-sig") != b.read_text(encoding="utf-8-sig") and \
            {r["contract_number"]: r for r in csv.DictReader(open(b, encoding="utf-8-sig"))} != first:
        bad.append(("enrich idempotent", None))
    for d in _DIRS:
        shutil.rmtree(d, ignore_errors=True)
    if bad:
        for x in bad:
            print("FAIL", x)
        return 1
    print("canadabuys_filter tests pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
