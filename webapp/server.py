#!/usr/bin/env python3
"""Web UI for fair-price-kit. Stdlib only, no pip install.

Binds to 127.0.0.1 by default -- so by default, nothing here is reachable from another machine, and
the caller-auth layer below never comes into play (webapp/README.md's local workflow is unaffected).
--host lets an operator who has actually read ARCHITECTURE.md run this as a shared instance instead;
the server refuses to bind a non-loopback host unless a token roster is configured (webapp/auth.py),
so it cannot be exposed unauthenticated by accident.

Register lookup, award search and the commodity price index (data this repo already publishes
openly) never require a caller identity -- see gates/sensitive-info-gate.md's scope note. Scan and
draft touch a caller's own pasted input (and, for draft, the host's own ANTHROPIC_API_KEY), so they
require a resolved caller whenever auth is required (--require-auth / FAIR_PRICE_REQUIRE_AUTH=1).

Usage:  python webapp/server.py [--port 8420] [--host 127.0.0.1] [--require-auth]
"""
import json
import os
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auth  # noqa: E402
import engine  # noqa: E402

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

class LocalServer(ThreadingHTTPServer):
    # ThreadingHTTPServer defaults allow_reuse_address to True (SO_REUSEADDR), which on Windows can
    # let a second process silently bind the same port instead of failing -- two server instances
    # then answer requests unpredictably, and a restart can look successful while the old process
    # (with old code) keeps serving some or all traffic. Off, so a real conflict always surfaces as
    # the clean error below instead of silent, inconsistent double-binding.
    allow_reuse_address = False


STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    server_version = "fair-price-kit-webapp/0.1"

    def log_message(self, fmt, *args):  # quieter, one line per request, no client address noise
        print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, name: str, content_type: str):
        path = STATIC_DIR / name
        if not path.is_file():
            return self._json(404, {"error": f"static file not found: {name}"})
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _require_caller(self):
        """Returns the resolved caller label, or writes a 401 and returns None. Only called from
        routes that touch a caller's own input (scan, draft); register/awards/commodity-index/health
        never call this. When auth isn't required at all (the default), every caller resolves to the
        fixed label "local" without consulting auth.py -- this keeps the ordinary local, single-user
        workflow from ever depending on a token existing."""
        if not auth.auth_required():
            return "local"
        caller_id, reason = auth.resolve_caller(self.headers)
        if not caller_id:
            self._json(401, {"error": f"authentication required: {reason}"})
            return None
        return caller_id

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"bad JSON body: {e}") from None

    # ---------- routing ----------
    # do_GET/do_POST are thin wrappers that catch anything the route handlers below don't --
    # a bug, a missing file, whatever -- and turn it into a clean JSON 500 instead of the browser
    # seeing a hung or reset connection (indistinguishable, from the UI, from "server not running"
    # or "unable to connect", which is exactly the confusing state this replaces).

    def do_GET(self):
        try:
            return self._route_GET()
        except Exception as e:
            return self._json(500, {"error": f"internal error: {e}"})

    def do_POST(self):
        try:
            return self._route_POST()
        except Exception as e:
            return self._json(500, {"error": f"internal error: {e}"})

    def _route_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in STATIC_FILES:
            name, ctype = STATIC_FILES[parsed.path]
            return self._static(name, ctype)
        if parsed.path == "/api/health":
            auth_on = auth.auth_required()
            authenticated = bool(auth_on and auth.resolve_caller(self.headers)[0])
            return self._json(200, {
                "ok": True,
                "draft_enabled": engine.api_key_configured(),
                "auth_required": auth_on,
                "authenticated": authenticated if auth_on else True,
            })
        if parsed.path == "/api/register":
            return self._json(200, {"rows": engine.load_register()})
        if parsed.path == "/api/awards":
            q = urllib.parse.parse_qs(parsed.query)
            query = q.get("q", [""])[0]
            unflagged = q.get("unflagged", ["1"])[0] != "0"
            competitive = q.get("competitive", ["0"])[0] == "1"
            limit = int(q.get("limit", ["25"])[0])
            try:
                rows = engine.search_awards(query, unflagged, competitive, limit)
            except (ValueError, OSError) as e:
                return self._json(500, {"error": str(e)})
            return self._json(200, {"rows": rows})
        if parsed.path == "/api/commodity-index":
            q = urllib.parse.parse_qs(parsed.query)
            vector = q.get("vector", [""])[0]
            try:
                if vector:
                    result = engine.commodity_index_adjustment(vector, q.get("from", [""])[0], q.get("to", [""])[0])
                    return self._json(200, result)
                products = engine.search_commodity_products(q.get("q", [""])[0], int(q.get("limit", ["25"])[0]))
                return self._json(200, {"products": products})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
        return self._json(404, {"error": f"no such route: GET {parsed.path}"})

    def _route_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = self._read_json_body()
        except ValueError as e:
            return self._json(400, {"error": str(e)})

        if parsed.path == "/api/scan":
            if self._require_caller() is None:
                return
            return self._json(200, engine.scan_input(body.get("text", ""), allow=body.get("allow")))

        if parsed.path == "/api/validate":
            return self._json(200, engine.validate_citations(body.get("text", "")))

        if parsed.path == "/api/draft":
            if self._require_caller() is None:
                return
            # {"messages": [...]} continues an existing conversation (a reply to something the
            # draft raised); anything else is treated as the inputs for a fresh first draft.
            try:
                if "messages" in body:
                    result = engine.draft_with_llm(messages=body["messages"])
                else:
                    result = engine.draft_with_llm(inputs=body)
            except engine.DraftError as e:
                return self._json(400, {"error": str(e)})
            citations = engine.validate_citations(result["draft"])
            return self._json(200, {
                "draft": result["draft"],
                "citations": citations,
                "usage": result["usage"],
                "estimated_cost_usd": result["estimated_cost_usd"],
                "messages": result["messages"],
                "truncated": result["truncated"],
            })

        return self._json(404, {"error": f"no such route: POST {parsed.path}"})


def main(argv):
    port = 8420
    host = "127.0.0.1"
    if "--port" in argv:
        i = argv.index("--port")
        if i + 1 >= len(argv):
            print("error: --port needs a value", file=sys.stderr)
            return 2
        port = int(argv[i + 1])
    if "--host" in argv:
        i = argv.index("--host")
        if i + 1 >= len(argv):
            print("error: --host needs a value", file=sys.stderr)
            return 2
        host = argv[i + 1]
    if "--require-auth" in argv:
        os.environ["FAIR_PRICE_REQUIRE_AUTH"] = "1"

    if host not in LOOPBACK_HOSTS:
        # A non-loopback host is reachable from other machines -- refuse unless auth is actually
        # configured, so this can't be exposed unauthenticated just by someone passing --host without
        # having read ARCHITECTURE.md. --require-auth alone isn't enough either: it has to have a
        # roster to check against, or every caller is simply unresolved.
        if not auth.auth_required():
            print(f"error: refusing to bind {host} without --require-auth -- a non-loopback host is "
                  "reachable from other machines, and scan/draft would be open to anyone who finds "
                  "the URL. Add --require-auth (and configure webapp/tokens.txt -- see "
                  "webapp/tokens.txt.example) if this is meant to be a shared instance.", file=sys.stderr)
            return 2
        if not auth.roster_configured():
            print("error: --require-auth is set but no tokens are configured -- every caller would be "
                  "unresolved. Copy webapp/tokens.txt.example to webapp/tokens.txt and add at least "
                  "one token, or set FAIR_PRICE_TOKENS.", file=sys.stderr)
            return 2

    try:
        httpd = LocalServer((host, port), Handler)
    except OSError as e:
        print(f"error: could not start the server on {host}:{port}: {e}", file=sys.stderr)
        print("This usually means something is already using that port -- maybe the webapp is "
              "already running in another window (check for one before starting a new one). "
              f"Or run with a different port: python webapp/server.py --port {port + 1}", file=sys.stderr)
        return 1
    url = f"http://{host}:{port}"
    scope = "local only" if host in LOOPBACK_HOSTS else f"REACHABLE FROM OTHER MACHINES, auth required"
    print(f"fair-price-kit webapp: {url}  ({scope}; Ctrl+C to stop)")
    if not engine.api_key_configured():
        print("note: ANTHROPIC_API_KEY is not set in this window -- drafting will be disabled. "
              "Every other feature (scan, register, award search) still works. See webapp/README.md "
              "to set it, then restart.")
    try:
        webbrowser.open(url)
    except Exception:
        pass  # not fatal either way -- the URL above still works if nothing opens on its own
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()  # release the port immediately -- don't wait on process teardown/GC to
                               # do it, which is what let a stale process keep answering requests
                               # after a restart looked clean in an earlier version of this file
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
