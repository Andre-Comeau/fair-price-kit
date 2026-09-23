#!/usr/bin/env python3
"""Run every test in tools/test and report. Run from anywhere: python tools/test/run_all.py
Exit code 0 only if every test passes (a SKIP because pdftotext is missing counts as a pass but is shown)."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[1]
TESTS = [
    ("scanner patterns", ["test_scanner.py"]),
    ("spec page-header sectioning", ["test_spec_headers.py"]),
    ("CanadaBuys filter", ["test_canadabuys_filter.py"]),
    ("StatCan IPPI filter", ["test_statcan_ippi_filter.py"]),
    ("OCDS export", ["test_ocds_export.py"]),
    ("Power Automate reference logic", ["flow_reference.py", "selftest"]),
    ("end-to-end pipeline", ["test_pipeline.py"]),
    ("webapp engine", ["test_webapp.py"]),
    ("webapp auth", ["test_webapp_auth.py"]),
    ("webapp server", ["test_webapp_server.py"]),
]


def main():
    failed = []
    for name, cmd in TESTS:
        r = subprocess.run([sys.executable, str(HERE / cmd[0]), *cmd[1:]], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=KIT)
        last = (r.stdout.strip().splitlines() or [""])[-1]
        status = "ok  " if r.returncode == 0 else "FAIL"
        print(f"[{status}] {name}: {last}")
        if r.returncode != 0:
            failed.append(name)
            print(r.stdout[-1500:], r.stderr[-800:])
    print("\nAll tests passed." if not failed else f"\n{len(failed)} test group(s) failed: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
