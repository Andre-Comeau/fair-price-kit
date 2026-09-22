"""Tests for webapp/engine.py -- the deterministic functions only. No server, no network:
draft_with_llm() is exercised only for its no-API-key error path, never for a real call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "webapp"))
import engine  # noqa: E402


def test_scan_input_clean():
    r = engine.scan_input("This spec section covers general concrete requirements.")
    assert r["clean"] is True
    assert r["count"] == 0


def test_scan_input_finds_company_and_phone():
    r = engine.scan_input("Call ACME Construction Ltd. at (613)555-0123 for details.")
    assert r["clean"] is False
    cats = {f["category"] for f in r["findings"]}
    assert "company-name" in cats
    assert "phone" in cats
    # values must be masked, never printed in full
    for f in r["findings"]:
        assert "ACME Construction Ltd." not in f["masked"] or len(f["masked"]) < len("ACME Construction Ltd.")


def test_scan_input_does_not_flag_dimension_lists():
    r = engine.scan_input("Rebar spacing: 450 450 450 mm typical.")
    assert r["clean"] is True


def test_register_loads_and_has_known_ids():
    ids = engine.register_ids()
    assert "TBS-DMP-3.1" in ids
    assert "CANADABUYS-AWARD-DATA" in ids
    assert len(ids) >= 20


def test_search_awards_excludes_flagged_by_default():
    rows = engine.search_awards("", unflagged_only=True, limit=1000)
    assert rows, "expected some unflagged rows"
    assert all(not r["quality_flags"] for r in rows)


def test_search_awards_query_filters_by_title():
    rows = engine.search_awards("elevator", unflagged_only=True, limit=1000)
    assert rows, "expected at least one elevator-related unflagged award"
    assert all("elevator" in r["title"].lower() for r in rows)


def test_search_awards_competitive_only():
    rows = engine.search_awards("", unflagged_only=True, competitive_only=True, limit=1000)
    assert rows
    assert all(r["competitive"] == "yes" for r in rows)


def test_validate_citations_known_and_unknown():
    draft = "Cites TBS-DMP-3.1 and also FAKE-MADE-UP-ID which does not exist."
    result = engine.validate_citations(draft)
    assert "TBS-DMP-3.1" in result["used"]
    assert "FAKE-MADE-UP-ID" in result["unknown"]
    assert result["ok"] is False


def test_validate_citations_all_known_is_ok():
    draft = "Cites TBS-DMP-3.1 and TBS-DMP-4.3.1 only."
    result = engine.validate_citations(draft)
    assert result["unknown"] == []
    assert result["ok"] is True


def test_draft_with_llm_fails_clearly_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        engine.draft_with_llm({"organization": "test"})
        assert False, "expected DraftError when no API key is set"
    except engine.DraftError as e:
        assert "ANTHROPIC_API_KEY" in str(e)


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            if "monkeypatch" in t.__code__.co_varnames[:t.__code__.co_argcount]:
                t(_FakeMonkeypatch())
            else:
                t()
            print(f"[ok  ] {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    if failed:
        print(f"\n{failed} of {len(tests)} webapp tests failed")
        return 1
    print(f"\nall {len(tests)} webapp tests passed")
    return 0


class _FakeMonkeypatch:
    def delenv(self, name, raising=True):
        import os
        os.environ.pop(name, None)


if __name__ == "__main__":
    raise SystemExit(main())
