"""End-to-end tests for server.py.

Starts the real server from server.py on a free port in a background
thread, pointed at a temporary database file, so these tests never touch
the real quotes.db. Talks to it over HTTP using only the standard library.
"""

import json
import re
import sqlite3
import threading
import urllib.error
import urllib.request

import pytest

import server as server_module

PRICE_PATTERN = re.compile(r"^\d{1,7}\.\d{2}$")


@pytest.fixture
def running_server(tmp_path):
    db_path = tmp_path / "quotes.db"
    # port=0 asks the OS for a free port; the real one is bound immediately
    httpd = server_module.make_server(host="localhost", port=0, db_path=db_path)
    port = httpd.server_address[1]

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://localhost:{port}"
    yield base_url, db_path

    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)


def valid_payload(**overrides):
    payload = {
        "full_name": "Jane Doe",
        "dob": "1990-01-01",
        "email": "jane@example.com",
        "car_make": "Toyota",
        "car_model": "Corolla",
        "car_year": 2015,
        "coverage_type": "standard",
    }
    payload.update(overrides)
    return payload


# Makes one HTTP request and returns (status, body_bytes, headers).
# Non-2xx responses still come back here (via HTTPError) rather than
# raising, so tests can assert on error status codes directly.
def request(method, base_url, path, body=None):
    url = f"{base_url}{path}"
    data = None
    headers = {}

    if body is not None:
        if isinstance(body, (bytes, bytearray)):
            data = bytes(body)
        else:
            data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def test_valid_quote_returns_200_with_price_and_saves_row(running_server):
    base_url, db_path = running_server

    status, body_bytes, _ = request("POST", base_url, "/api/quote", valid_payload())

    assert status == 200
    body = json.loads(body_bytes)
    assert PRICE_PATTERN.match(body["monthly_price"])

    connection = sqlite3.connect(db_path)
    try:
        count = connection.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
    finally:
        connection.close()
    assert count == 1


def test_invalid_quote_returns_400_with_errors(running_server):
    base_url, _ = running_server

    payload = valid_payload(email="")
    status, body_bytes, _ = request("POST", base_url, "/api/quote", payload)

    assert status == 400
    body = json.loads(body_bytes)
    assert "errors" in body
    assert "email" in body["errors"]


def test_malformed_json_returns_400(running_server):
    base_url, _ = running_server

    status, body_bytes, _ = request("POST", base_url, "/api/quote", b"not json")

    assert status == 400
    body = json.loads(body_bytes)
    assert "errors" in body


def test_get_quote_returns_405(running_server):
    base_url, _ = running_server

    status, _, _ = request("GET", base_url, "/api/quote")

    assert status == 405


def test_unknown_path_returns_404(running_server):
    base_url, _ = running_server

    status, _, _ = request("GET", base_url, "/no-such-path")

    assert status == 404


def test_root_returns_index_html(running_server):
    base_url, _ = running_server

    status, body_bytes, headers = request("GET", base_url, "/")

    assert status == 200
    assert "text/html" in headers.get("Content-Type", "")
    assert b"<html" in body_bytes.lower()


def test_saved_quote_includes_suggested_decision_and_reasons(running_server):
    base_url, db_path = running_server

    # dob 1990-01-01 and car_year 2015 stay inside the accept rules for
    # the foreseeable future, so this does not trigger any referral rule
    status, _, _ = request("POST", base_url, "/api/quote", valid_payload())
    assert status == 200

    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "SELECT suggested_decision, reasons FROM quotes"
        ).fetchone()
    finally:
        connection.close()

    suggested_decision, reasons_json = row
    assert suggested_decision == "accept"
    assert json.loads(reasons_json) == ["No referral rules triggered"]


def test_admin_quotes_returns_saved_quote_with_right_fields(running_server):
    base_url, _ = running_server

    post_status, post_body_bytes, _ = request(
        "POST", base_url, "/api/quote", valid_payload()
    )
    assert post_status == 200
    monthly_price = json.loads(post_body_bytes)["monthly_price"]

    status, body_bytes, _ = request("GET", base_url, "/api/admin/quotes")

    assert status == 200
    quotes = json.loads(body_bytes)
    assert len(quotes) == 1

    quote = quotes[0]
    assert quote["full_name"] == "Jane Doe"
    assert quote["email"] == "jane@example.com"
    assert quote["car_make"] == "Toyota"
    assert quote["car_model"] == "Corolla"
    assert quote["car_year"] == 2015
    assert quote["coverage_type"] == "standard"
    assert quote["monthly_price"] == monthly_price
    assert quote["suggested_decision"] == "accept"
    assert quote["reasons"] == ["No referral rules triggered"]
    assert quote["status"] == "pending"
    assert quote["underwriter_note"] is None
    assert quote["created_at"]


def test_valid_quote_response_includes_breakdown_matching_monthly_price(running_server):
    base_url, _ = running_server

    status, body_bytes, _ = request("POST", base_url, "/api/quote", valid_payload())

    assert status == 200
    body = json.loads(body_bytes)
    assert "breakdown" in body
    assert isinstance(body["breakdown"], list)
    assert len(body["breakdown"]) == 6
    for step in body["breakdown"]:
        assert set(step.keys()) == {"label", "amount"}
        assert PRICE_PATTERN.match(step["amount"])
    assert body["breakdown"][-1]["amount"] == body["monthly_price"]


def test_valid_quote_with_vehicle_value_uses_it_for_base_price(running_server):
    base_url, _ = running_server

    payload = valid_payload(vehicle_value="12000")
    status, body_bytes, _ = request("POST", base_url, "/api/quote", payload)

    assert status == 200
    body = json.loads(body_bytes)
    assert body["breakdown"][0] == {"label": "Base price", "amount": "30.00"}
