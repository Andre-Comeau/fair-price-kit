"""Tests for webapp/server.py's HTTP layer itself -- routing, malformed input, and the catch-all
error handling -- as opposed to test_webapp.py, which tests engine.py's functions directly without
an HTTP server at all. Starts a real server on an OS-assigned free port in a background thread for
the duration of this process; no fixture files, no subprocess, no network beyond 127.0.0.1."""
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "webapp"))
import engine  # noqa: E402
import server  # noqa: E402

BASE = None  # set by _start_server()
_httpd = None


def _start_server():
    global BASE, _httpd
    _httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)  # port 0 -> OS picks a free one
    port = _httpd.server_address[1]
    thread = threading.Thread(target=_httpd.serve_forever, daemon=True)
    thread.start()
    BASE = f"http://127.0.0.1:{port}"


def _stop_server():
    _httpd.shutdown()
    _httpd.server_close()


def _get(path):
    """Returns (status, parsed_json) for a GET, whether it succeeds or fails -- so a 404/500 can
    be asserted on directly instead of the test having to catch HTTPError itself each time."""
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def _post(path, body_bytes):
    req = urllib.request.Request(BASE + path, data=body_bytes, method="POST",
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def test_health_reports_ok_and_draft_enabled_state(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    status, data = _get("/api/health")
    assert status == 200 and data["ok"] is True and data["draft_enabled"] is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-testing-only")
    try:
        status, data = _get("/api/health")
        assert data["draft_enabled"] is True
    finally:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_unknown_route_is_a_clean_404_not_a_crash():
    status, data = _get("/no/such/route")
    assert status == 404
    assert "error" in data


def test_malformed_json_body_is_a_clean_400():
    status, data = _post("/api/scan", b"not json at all {{{")
    assert status == 400
    assert "error" in data


def test_scan_route_finds_something_end_to_end():
    status, data = _post("/api/scan", json.dumps({"text": "Call ACME Construction Ltd. today."}).encode("utf-8"))
    assert status == 200
    assert data["clean"] is False


class _FakeAPIResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_draft_route_passes_truncated_through_to_the_response(monkeypatch):
    # End-to-end version of test_webapp.py's truncated-flag test -- through the actual HTTP route,
    # not just the engine function -- so a future change to server.py's response dict can't drop the
    # field without a test noticing.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-for-testing-only")
    fake_payload = {
        "content": [{"type": "text", "text": "cut off mid-sen"}],
        "usage": {"input_tokens": 10, "output_tokens": 4000},
        "stop_reason": "max_tokens",
    }
    # engine.urllib.request IS the same module object test_webapp_server.py's own _post()/_get()
    # import -- replacing urlopen globally would fake out our own test-client requests to the local
    # server too, so the fake delegates to the real urlopen for anything that isn't the Anthropic call.
    real_urlopen = engine.urllib.request.urlopen

    def fake_urlopen(req, timeout=60):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.anthropic.com" in url:
            return _FakeAPIResponse(fake_payload)
        return real_urlopen(req, timeout=timeout)

    monkeypatch.setattr(engine.urllib.request, "urlopen", fake_urlopen)
    try:
        status, data = _post("/api/draft", json.dumps({"organization": "test"}).encode("utf-8"))
        assert status == 200
        assert data["truncated"] is True
    finally:
        monkeypatch.undo()
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_unexpected_internal_error_is_a_clean_500_not_a_hang(monkeypatch):
    # Simulates a real bug in a route handler -- engine.load_register raising instead of returning
    # a list -- and confirms the catch-all in do_GET turns it into JSON, not a dropped connection
    # (which is what looked, from the browser, indistinguishable from "server not running").
    def boom():
        raise RuntimeError("simulated failure")
    monkeypatch.setattr(engine, "load_register", boom)
    try:
        status, data = _get("/api/register")
        assert status == 500
        assert "internal error" in data["error"]
    finally:
        monkeypatch.undo()


def main():
    _start_server()
    try:
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
            print(f"\n{failed} of {len(tests)} webapp server tests failed")
            return 1
        print(f"\nall {len(tests)} webapp server tests passed")
        return 0
    finally:
        _stop_server()


class _FakeMonkeypatch:
    """Minimal stand-in so these tests can run outside pytest, matching test_webapp.py's harness."""

    def __init__(self):
        self._sets = []  # (obj, name, had_attr, old_value)

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
