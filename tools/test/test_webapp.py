"""Tests for webapp/engine.py -- the deterministic functions only. No real network: draft_with_llm()
is exercised for its no-API-key and cost-ceiling error paths without any call at all, and for its
response-parsing behaviour (the truncated flag) against a fake urlopen standing in for the API."""
import json
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


def test_scan_input_offsets_locate_the_real_match():
    # lowercase lead-in: the company-name pattern is deliberately greedy about a run of
    # capitalized words (see tools/scan_sensitive.py), so a sentence-initial capital would be
    # swept into the match too -- not a bug, just not what this test is checking.
    text = "please call ACME Construction Ltd. today."
    r = engine.scan_input(text)
    hit = next(f for f in r["findings"] if f["category"] == "company-name")
    line = text.splitlines()[hit["line"] - 1]
    assert line[hit["start"]:hit["end"]] == "ACME Construction Ltd."


def test_scan_input_allow_suppresses_a_specific_match_only():
    text = "Call ACME Construction Ltd. at (613)555-0123 for details."
    first = engine.scan_input(text)
    cats_before = {f["category"] for f in first["findings"]}
    assert {"company-name", "phone"} <= cats_before
    # accept only the company name (as the UI would, using the offsets to read the real text)
    hit = next(f for f in first["findings"] if f["category"] == "company-name")
    line = text.splitlines()[hit["line"] - 1]
    accepted_text = line[hit["start"]:hit["end"]]
    second = engine.scan_input(text, allow=[accepted_text])
    cats_after = {f["category"] for f in second["findings"]}
    assert "company-name" not in cats_after  # accepted, no longer flagged
    assert "phone" in cats_after  # NOT accepted -- still flagged, allow is per-item, not global


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


def test_build_system_blocks_is_cacheable_and_holds_the_fixed_context():
    blocks = engine.build_system_blocks()
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "TBS-DMP-3.1" in blocks[0]["text"]  # the register really is in there
    assert "When to use" in blocks[0]["text"]  # so is SKILL.md


def test_build_user_message_carries_inputs_not_fixed_context():
    msg = engine.build_user_message({"organization": "Test Org", "price": "$1"})
    assert "Test Org" in msg
    assert "TBS-DMP-3.1" not in msg  # the register belongs in the cached system block, not here


def test_estimate_cost_usd_matches_hand_calculation():
    usage = {"input_tokens": 1000, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 500}
    cost = engine.estimate_cost_usd(usage, "claude-sonnet-5")
    expected = (1000 * 2.00 + 500 * 10.00) / 1_000_000
    assert abs(cost - expected) < 1e-9


def test_estimate_cost_usd_unknown_model_returns_none():
    assert engine.estimate_cost_usd({"input_tokens": 1}, "not-a-real-model") is None


def test_draft_with_llm_refuses_before_calling_network_when_over_ceiling(monkeypatch):
    # A fake key gets past the "is a key set" check; the cost ceiling must still stop it before
    # any request is built, so this never touches the network even with fake credentials.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-testing-only")
    try:
        engine.draft_with_llm({"organization": "test"}, max_cost_usd=0.0000001)
        assert False, "expected DraftError from the cost ceiling"
    except engine.DraftError as e:
        assert "ceiling" in str(e)
    finally:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_draft_with_llm_requires_inputs_or_messages(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-testing-only")
    try:
        engine.draft_with_llm()
        assert False, "expected DraftError when neither inputs nor messages is given"
    except engine.DraftError as e:
        assert "inputs" in str(e) and "messages" in str(e)
    finally:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_draft_with_llm_cost_ceiling_applies_to_messages_path_too(monkeypatch):
    # A long-running conversation should be sized (and stopped by the ceiling) from the whole
    # messages list, not just a fresh inputs dict -- confirms the messages branch is covered too.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-testing-only")
    long_history = [
        {"role": "user", "content": "x" * 1000},
        {"role": "assistant", "content": "y" * 1000},
        {"role": "user", "content": "z" * 1000},
    ]
    try:
        engine.draft_with_llm(messages=long_history, max_cost_usd=0.0000001)
        assert False, "expected DraftError from the cost ceiling"
    except engine.DraftError as e:
        assert "ceiling" in str(e)
    finally:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


class _FakeAPIResponse:
    """Stands in for the object urllib.request.urlopen() returns -- a context manager with .read()
    returning bytes, same as the real one."""
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_draft_with_llm_reports_truncated_when_stop_reason_is_max_tokens(monkeypatch):
    # Regression test for a real failure seen in live testing: a draft was cut off mid-table with no
    # error at all, and the only way to tell was noticing a missing template section by hand. This
    # locks in that draft_with_llm() surfaces it itself instead of relying on that kind of noticing.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-testing-only")
    fake_payload = {
        "content": [{"type": "text", "text": "# Price justification\n\n(cut off mid-sent"}],
        "usage": {"input_tokens": 10, "output_tokens": 4000},
        "stop_reason": "max_tokens",
    }
    original_urlopen = engine.urllib.request.urlopen
    engine.urllib.request.urlopen = lambda req, timeout=60: _FakeAPIResponse(fake_payload)
    try:
        result = engine.draft_with_llm({"organization": "test"})
        assert result["truncated"] is True
    finally:
        engine.urllib.request.urlopen = original_urlopen
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_draft_with_llm_reports_not_truncated_on_a_normal_finish(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-testing-only")
    fake_payload = {
        "content": [{"type": "text", "text": "a complete draft, finished normally"}],
        "usage": {"input_tokens": 10, "output_tokens": 50},
        "stop_reason": "end_turn",
    }
    original_urlopen = engine.urllib.request.urlopen
    engine.urllib.request.urlopen = lambda req, timeout=60: _FakeAPIResponse(fake_payload)
    try:
        result = engine.draft_with_llm({"organization": "test"})
        assert result["truncated"] is False
    finally:
        engine.urllib.request.urlopen = original_urlopen
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_max_output_tokens_has_headroom_for_the_full_template():
    # Regression guard for a real truncation seen in live testing: the old cap (4000) was fully used
    # and cut the draft off mid-table in section 3 of 7, well before the conclusion, documentation
    # list or sources section. This doesn't catch every truncation, just a revert back toward that.
    assert engine.MAX_OUTPUT_TOKENS >= 6000


def test_api_key_configured_reads_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert engine.api_key_configured() is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-testing-only")
    try:
        assert engine.api_key_configured() is True
    finally:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


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

    def setenv(self, name, value):
        import os
        os.environ[name] = value


if __name__ == "__main__":
    raise SystemExit(main())
