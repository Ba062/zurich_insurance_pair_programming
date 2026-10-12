"""HTTP server for the quote app.

Serves the frontend static files and handles POST /api/quote. The page and
the API share one address (localhost:5000), so no CORS is needed.
"""

import json
import sqlite3
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from db import init_db, list_quotes, save_quote
from pricing import calculate_monthly_price
from underwriting import assess_risk
from validate import validate_quote

HOST = "localhost"
PORT = 5000

FRONTEND_DIR = (Path(__file__).resolve().parent.parent / "frontend").resolve()
DB_PATH = Path(__file__).resolve().parent / "quotes.db"

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}

_connection = None
_db_path = DB_PATH


# One shared connection for the lifetime of the process (server is single-threaded)
def get_connection():
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(_db_path, check_same_thread=False)
        init_db(_connection)
    return _connection


# Maps a URL path to a file inside frontend/, or None if it is missing or
# would escape that folder
def resolve_static_path(url_path):
    if url_path in ("", "/"):
        url_path = "/index.html"

    relative = url_path.lstrip("/")
    candidate = (FRONTEND_DIR / relative).resolve()

    try:
        candidate.relative_to(FRONTEND_DIR)
    except ValueError:
        return None  # path traversal attempt, e.g. "../../secrets"

    if candidate.is_file():
        return candidate
    return None


def guess_mime_type(path):
    return MIME_TYPES.get(path.suffix, "application/octet-stream")


class QuoteRequestHandler(BaseHTTPRequestHandler):
    # Quiet the default per-request logging noise; keep the basics
    server_version = "QuoteServer/1.0"

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_method_not_allowed(self):
        self.send_json(405, {"error": "Method not allowed."})

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/quote":
            self.send_method_not_allowed()
            return

        if path == "/api/admin/quotes":
            self.handle_admin_quotes()
            return

        file_path = resolve_static_path(path)
        if file_path is None:
            self.send_json(404, {"error": "Not found."})
            return

        try:
            content = file_path.read_bytes()
        except OSError:
            self.send_json(500, {"error": "Internal server error."})
            return

        self.send_response(200)
        self.send_header("Content-Type", guess_mime_type(file_path))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/quote":
            self.handle_quote()
            return

        if path == "/api/admin/quotes":
            # GET-only route; POST here is a known path, wrong method
            self.send_method_not_allowed()
            return

        # A known static file hit with POST is a wrong method; anything
        # else is simply not a route we have
        if resolve_static_path(path) is not None:
            self.send_method_not_allowed()
        else:
            self.send_json(404, {"error": "Not found."})

    def handle_quote(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length) if length > 0 else b""

            try:
                data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_json(400, {"errors": {"body": "Invalid JSON."}})
                return

            if not isinstance(data, dict):
                self.send_json(400, {"errors": {"body": "Invalid JSON."}})
                return

            errors = validate_quote(data)
            if errors:
                self.send_json(400, {"errors": errors})
                return

            today = date.today()
            monthly_price = calculate_monthly_price(data, today)
            risk = assess_risk(data, today)
            save_quote(
                get_connection(),
                data,
                monthly_price,
                risk["decision"],
                risk["reasons"],
            )
            # Customer response is unchanged: the risk assessment is for
            # the admin view only, not shown to the person getting a quote
            self.send_json(200, {"monthly_price": monthly_price})
        except Exception:
            self.send_json(500, {"error": "Internal server error."})

    def handle_admin_quotes(self):
        try:
            quotes = list_quotes(get_connection())
            self.send_json(200, quotes)
        except Exception:
            self.send_json(500, {"error": "Internal server error."})

    # Only GET and POST are used by this app; every other method is a
    # wrong method on whatever path was requested
    def do_PUT(self):
        self.send_method_not_allowed()

    def do_DELETE(self):
        self.send_method_not_allowed()

    def do_PATCH(self):
        self.send_method_not_allowed()

    def do_HEAD(self):
        self.send_method_not_allowed()

    def do_OPTIONS(self):
        self.send_method_not_allowed()


# Builds and binds the HTTPServer without starting it, so callers (the
# normal entry point, or tests) can control when/how it runs. Also points
# get_connection() at the given db_path, resetting any cached connection
# so a fresh one is opened against it.
def make_server(host=HOST, port=PORT, db_path=DB_PATH):
    global _db_path, _connection
    _db_path = db_path
    _connection = None
    return HTTPServer((host, port), QuoteRequestHandler)


def run(host=HOST, port=PORT, db_path=DB_PATH):
    server = make_server(host, port, db_path)
    print(f"Serving on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    run()
