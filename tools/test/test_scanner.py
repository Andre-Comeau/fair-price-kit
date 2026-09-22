#!/usr/bin/env python3
"""Regression tests for tools/scan_sensitive.py patterns. Run: python tools/test/test_scanner.py
Every string is synthetic. Exit 0 = all pass."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scan_sensitive as ss  # noqa: E402

P = dict(ss.PATTERNS)

# (category, text, should_match)
CASES = [
    ("street-address", "Project at 123 Example Street, Ottawa", True),
    ("street-address", "45 Main St.", True),
    ("street-address", "45 rue Principale", True),
    ("street-address", "3.1 Place concrete in one pour.", False),
    ("street-address", "2.1 Drive piles to refusal.", False),
    ("street-address", "1.1 Way of working is described in Part 2.", False),
    ("signature-line", "Prepared by: A. Person", True),
    ("signature-line", "Prepared by: [PERSON]", False),
    ("signature-line", "Approved by: [OWNER-PM]", False),
    ("contract-id", "Contract No: ABC-2026-0042", True),
    ("contract-id", "PO 12-345", True),
    ("contract-id", "see policy-notice/2007-4.html", False),
    ("contract-id", "Provision TBS-DMP-4.10.1.5 requires", False),
    ("company-name", "awarded to Northwind Traders Inc.", True),
    ("email", "write to jane.doe@example.com", True),
    ("email", "write to jane.doe@example- other.ca", True),
    ("email", "the ratio a @ b is 2", False),
    ("phone", "call (613) 555-0123", True),
    ("phone", "613-555-0123", True),
    ("phone", "Tel: 613 555 0123", True),
    ("phone", "Concrete: 32 MPa at 28 days", False),
    ("phone", "REBAR SPACING 300 300 2500", False),
    ("phone", "VARIES 450 450 450 300 300 250", False),
    ("sin-like", "VARIES 450 450 450 300 300 250", False),
    ("sin-like", "123-456-789", True),
    ("sin-like", "SIN 123 456 789", True),
    ("postal-code", "K1A 0B1", True),
    ("coordinates", "45.42153, -75.69719", True),
    ("business-number", "123456789 RT0001", True),
    ("person-title", "Contact Mr. Smith", True),
    ("person-title", "Attention: M. Tremblay", True),
    ("person-title", "Alex Doe, M.Sc., P.Eng. July 9, 2020", False),
    ("person-title", "Rm 193 H/M Lab Retrofit", False),
    ("person-title", "Report dated July 9, 2020 by the engineer", False),
    ("marked-restricted", "This document is Protected B.", True),
]


def main():
    bad = []
    for cat, text, want in CASES:
        got = bool(P[cat].search(text))
        if got != want:
            bad.append((cat, text, want))
    # reviewed-exceptions list: literals (substring of the match) and re: regexes silence only matching text
    ss.ALLOW.clear()
    ss.ALLOW.extend([("lit", "laboratory accreditation inc"), ("re", re.compile(r"^tender \d{4}-\d{2}-\d{2}$", re.I))])
    for text, want in [("Laboratory Accreditation Inc.", True), ("Northwind Traders Inc.", False),
                       ("TENDER 2025-03-28", True), ("Contract No: ABC-2026-0042", False)]:
        m = next((mm for _, rx in ss.PATTERNS for mm in rx.finditer(text)), None)
        got = bool(m) and ss.is_allowed(m.group(0))
        if got != want:
            bad.append(("allowlist", text, want))
    ss.ALLOW.clear()
    for u, want in [("https://www.canada.ca/x", True), ("https://acme-builders.example.org/team", False), ("https://laws-lois.justice.gc.ca/", True)]:
        if ss.is_public_url(u) != want:
            bad.append(("is_public_url", u, want))
    if bad:
        for b in bad:
            print("FAIL", b)
        return 1
    print(f"all {len(CASES) + 3} scanner cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
