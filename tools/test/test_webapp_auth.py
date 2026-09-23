"""Tests for webapp/auth.py -- caller resolution in isolation, no HTTP server. See
test_webapp_server.py for the end-to-end version (routes actually refusing an unresolved caller)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "webapp"))
import auth  # noqa: E402


class _Headers(dict):
    """Minimal stand-in for BaseHTTPRequestHandler.headers -- auth.py only calls .get(name)."""
    pass


def test_auth_required_reads_env(monkeypatch):
    monkeypatch.delenv("FAIR_PRICE_REQUIRE_AUTH", raising=False)
    assert auth.auth_required() is False
    monkeypatch.setenv("FAIR_PRICE_REQUIRE_AUTH", "1")
    try:
        assert auth.auth_required() is True
    finally:
        monkeypatch.delenv("FAIR_PRICE_REQUIRE_AUTH", raising=False)


def test_resolve_caller_with_no_token_supplied(monkeypatch):
    monkeypatch.setattr(auth, "TOKENS_FILE", Path("/no/such/file"))
    monkeypatch.setenv("FAIR_PRICE_TOKENS", "abc123:alice")
    try:
        caller_id, reason = auth.resolve_caller(_Headers())
        assert caller_id is None
        assert "no token" in reason
    finally:
        monkeypatch.delenv("FAIR_PRICE_TOKENS", raising=False)
        monkeypatch.undo()


def test_resolve_caller_with_a_valid_bearer_token(monkeypatch):
    monkeypatch.setattr(auth, "TOKENS_FILE", Path("/no/such/file"))
    monkeypatch.setenv("FAIR_PRICE_TOKENS", "abc123:alice")
    try:
        caller_id, reason = auth.resolve_caller(_Headers(Authorization="Bearer abc123"))
        assert caller_id == "alice"
        assert reason is None
    finally:
        monkeypatch.delenv("FAIR_PRICE_TOKENS", raising=False)
        monkeypatch.undo()


def test_resolve_caller_with_the_x_header_alternative(monkeypatch):
    monkeypatch.setattr(auth, "TOKENS_FILE", Path("/no/such/file"))
    monkeypatch.setenv("FAIR_PRICE_TOKENS", "abc123:alice")
    try:
        caller_id, reason = auth.resolve_caller(_Headers(**{"X-Fair-Price-Token": "abc123"}))
        assert caller_id == "alice"
    finally:
        monkeypatch.delenv("FAIR_PRICE_TOKENS", raising=False)
        monkeypatch.undo()


def test_resolve_caller_rejects_a_wrong_token(monkeypatch):
    monkeypatch.setattr(auth, "TOKENS_FILE", Path("/no/such/file"))
    monkeypatch.setenv("FAIR_PRICE_TOKENS", "abc123:alice")
    try:
        caller_id, reason = auth.resolve_caller(_Headers(Authorization="Bearer wrong-token"))
        assert caller_id is None
        assert "not recognized" in reason
    finally:
        monkeypatch.delenv("FAIR_PRICE_TOKENS", raising=False)
        monkeypatch.undo()


def test_roster_merges_file_and_env(monkeypatch, tmp_path):
    tokens_file = tmp_path / "tokens.txt"
    tokens_file.write_text("# comment\nfile-token,bob\n\n", encoding="utf-8")
    monkeypatch.setattr(auth, "TOKENS_FILE", tokens_file)
    monkeypatch.setenv("FAIR_PRICE_TOKENS", "env-token:carol")
    try:
        assert auth.roster_configured() is True
        bob_id, _ = auth.resolve_caller(_Headers(Authorization="Bearer file-token"))
        carol_id, _ = auth.resolve_caller(_Headers(Authorization="Bearer env-token"))
        assert bob_id == "bob"
        assert carol_id == "carol"
    finally:
        monkeypatch.delenv("FAIR_PRICE_TOKENS", raising=False)
        monkeypatch.undo()


def test_roster_configured_is_false_when_empty(monkeypatch):
    monkeypatch.setattr(auth, "TOKENS_FILE", Path("/no/such/file"))
    monkeypatch.delenv("FAIR_PRICE_TOKENS", raising=False)
    try:
        assert auth.roster_configured() is False
    finally:
        monkeypatch.undo()


def main():
    import tempfile
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        params = t.__code__.co_varnames[:t.__code__.co_argcount]
        try:
            args = []
            if "monkeypatch" in params:
                args.append(_FakeMonkeypatch())
            if "tmp_path" in params:
                args.append(Path(tempfile.mkdtemp()))
            t(*args)
            print(f"[ok  ] {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    if failed:
        print(f"\n{failed} of {len(tests)} webapp auth tests failed")
        return 1
    print(f"\nall {len(tests)} webapp auth tests passed")
    return 0


class _FakeMonkeypatch:
    def __init__(self):
        self._sets = []

    def delenv(self, name, raising=True):
        import os
        os.environ.pop(name, None)

    def setenv(self, name, value):
        import os
        os.environ[name] = value

    def setattr(self, obj, name, value):
        had = hasattr(obj, name)
        old = getattr(obj, name, None)
        self._sets.append((obj, name, had, old))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, had, old in reversed(self._sets):
            if had:
                setattr(obj, name, old)
            else:
                delattr(obj, name)
        self._sets.clear()


if __name__ == "__main__":
    raise SystemExit(main())
