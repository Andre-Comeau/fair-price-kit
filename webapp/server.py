#!/usr/bin/env python3
"""Local-only web UI for fair-price-kit. Stdlib only, no pip install.

Binds to 127.0.0.1 -- deliberately, always, not configurable -- so nothing here is ever reachable
from another machine. Four of the five API routes never touch a network; only /api/draft calls the
Anthropic API, using ANTHROPIC_API_KEY from the environment, exactly as an AI assistant already
would. See webapp/README.md for what that means for privacy.

Usage:  python webapp/server.py [--port 8420]
"""
import json
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

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
            return self._json(200, {"ok": True, "draft_enabled": engine.api_key_configured()})
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
        return self._json(404, {"error": f"no such route: GET {parsed.path}"})

    def _route_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = self._read_json_body()
        except ValueError as e:
            return self._json(400, {"error": str(e)})

        if parsed.path == "/api/scan":
            return self._json(200, engine.scan_input(body.get("text", ""), allow=body.get("allow")))

        if parsed.path == "/api/validate":
            return self._json(200, engine.validate_citations(body.get("text", "")))

        if parsed.path == "/api/draft":
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
            })

        return self._json(404, {"error": f"no such route: POST {parsed.path}"})


def main(argv):
    port = 8420
    if "--port" in argv:
        i = argv.index("--port")
        if i + 1 >= len(argv):
            print("error: --port needs a value", file=sys.stderr)
            return 2
        port = int(argv[i + 1])
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)  # 127.0.0.1 only -- see module docstring
    except OSError as e:
        print(f"error: could not start the server on 127.0.0.1:{port}: {e}", file=sys.stderr)
        print("This usually means something is already using that port -- maybe the webapp is "
              "already running in another window (check for one before starting a new one). "
              f"Or run with a different port: python webapp/server.py --port {port + 1}", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{port}"
    print(f"fair-price-kit webapp: {url}  (local only; Ctrl+C to stop)")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
