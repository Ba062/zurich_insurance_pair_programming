"""Tests for backend/db.py using an in-memory SQLite database."""

import sqlite3

import pytest

from db import init_db, list_quotes, save_quote, update_decision


@pytest.fixture
def connection():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def sample_quote(**overrides):
    data = {
        "full_name": "Jane Doe",
        "dob": "1990-01-01",
        "email": "jane@example.com",
        "car_make": "Toyota",
        "car_model": "Corolla",
        "car_year": "2020",
        "coverage_type": "Standard",
    }
    data.update(overrides)
    return data


def test_init_db_creates_table(connection):
    cursor = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='quotes'"
    )
    assert cursor.fetchone() is not None


def test_init_db_is_idempotent(connection):
    # Calling init_db again must not raise or drop existing data
    save_quote(connection, sample_quote(), "40.00")
    init_db(connection)
    cursor = connection.execute("SELECT COUNT(*) FROM quotes")
    assert cursor.fetchone()[0] == 1


def test_save_quote_inserts_row(connection):
    row_id = save_quote(connection, sample_quote(), "84.50")
    cursor = connection.execute(
        "SELECT full_name, dob, email, car_make, car_model, car_year, "
        "coverage_type, monthly_price FROM quotes WHERE id = ?",
        (row_id,),
    )
    row = cursor.fetchone()
    assert row == (
        "Jane Doe",
        "1990-01-01",
        "jane@example.com",
        "Toyota",
        "Corolla",
        2020,
        "Standard",
        "84.50",
    )


def test_save_quote_sets_created_at(connection):
    row_id = save_quote(connection, sample_quote(), "40.00")
    cursor = connection.execute(
        "SELECT created_at FROM quotes WHERE id = ?", (row_id,)
    )
    created_at = cursor.fetchone()[0]
    assert created_at  # non-empty string
    assert "T" in created_at  # ISO format


def test_save_quote_stores_car_year_as_integer(connection):
    row_id = save_quote(connection, sample_quote(car_year="1999"), "40.00")
    cursor = connection.execute(
        "SELECT car_year FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] == 1999


def test_save_quote_returns_increasing_ids(connection):
    first_id = save_quote(connection, sample_quote(), "40.00")
    second_id = save_quote(
        connection, sample_quote(email="other@example.com"), "40.00"
    )
    assert second_id > first_id


def test_save_quote_multiple_rows_persist(connection):
    save_quote(connection, sample_quote(full_name="Alice"), "40.00")
    save_quote(connection, sample_quote(full_name="Bob"), "52.00")
    cursor = connection.execute("SELECT full_name FROM quotes ORDER BY id")
    names = [row[0] for row in cursor.fetchall()]
    assert names == ["Alice", "Bob"]


def test_save_quote_defaults_status_to_pending(connection):
    row_id = save_quote(connection, sample_quote(), "40.00")
    cursor = connection.execute(
        "SELECT status FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] == "pending"


def test_save_quote_defaults_underwriter_note_to_null(connection):
    row_id = save_quote(connection, sample_quote(), "40.00")
    cursor = connection.execute(
        "SELECT underwriter_note FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] is None


def test_save_quote_without_suggestion_stores_null_decision_and_empty_reasons(connection):
    row_id = save_quote(connection, sample_quote(), "40.00")
    cursor = connection.execute(
        "SELECT suggested_decision, reasons FROM quotes WHERE id = ?", (row_id,)
    )
    suggested_decision, reasons = cursor.fetchone()
    assert suggested_decision is None
    assert reasons == "[]"


def test_save_quote_stores_suggested_decision_and_reasons(connection):
    row_id = save_quote(
        connection,
        sample_quote(),
        "40.00",
        suggested_decision="refer",
        reasons=["Driver is under 21.", "Car is more than 20 years old."],
    )
    cursor = connection.execute(
        "SELECT suggested_decision, reasons FROM quotes WHERE id = ?", (row_id,)
    )
    suggested_decision, reasons_json = cursor.fetchone()
    assert suggested_decision == "refer"
    assert reasons_json == '["Driver is under 21.", "Car is more than 20 years old."]'


def test_save_quote_defaults_no_claims_years_to_zero_when_missing(connection):
    row_id = save_quote(connection, sample_quote(), "40.00")
    cursor = connection.execute(
        "SELECT no_claims_years FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] == 0


def test_save_quote_stores_no_claims_years(connection):
    row_id = save_quote(connection, sample_quote(no_claims_years="4"), "40.00")
    cursor = connection.execute(
        "SELECT no_claims_years FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] == 4


def test_save_quote_boundary_no_claims_years_zero(connection):
    row_id = save_quote(connection, sample_quote(no_claims_years="0"), "40.00")
    cursor = connection.execute(
        "SELECT no_claims_years FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] == 0


def test_save_quote_boundary_no_claims_years_ten(connection):
    row_id = save_quote(connection, sample_quote(no_claims_years="10"), "40.00")
    cursor = connection.execute(
        "SELECT no_claims_years FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] == 10


def test_save_quote_boundary_no_claims_years_eleven(connection):
    row_id = save_quote(connection, sample_quote(no_claims_years="11"), "40.00")
    cursor = connection.execute(
        "SELECT no_claims_years FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] == 11


def test_save_quote_boundary_no_claims_years_fifty(connection):
    row_id = save_quote(connection, sample_quote(no_claims_years="50"), "40.00")
    cursor = connection.execute(
        "SELECT no_claims_years FROM quotes WHERE id = ?", (row_id,)
    )
    assert cursor.fetchone()[0] == 50


def test_list_quotes_empty_table_returns_empty_list(connection):
    assert list_quotes(connection) == []


def test_list_quotes_one_quote_returns_every_column(connection):
    row_id = save_quote(
        connection,
        sample_quote(),
        "84.50",
        suggested_decision="accept",
        reasons=["No referral rules triggered"],
    )

    rows = list_quotes(connection)

    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == row_id
    assert row["full_name"] == "Jane Doe"
    assert row["dob"] == "1990-01-01"
    assert row["email"] == "jane@example.com"
    assert row["car_make"] == "Toyota"
    assert row["car_model"] == "Corolla"
    assert row["car_year"] == 2020
    assert row["coverage_type"] == "Standard"
    assert row["no_claims_years"] == 0
    assert row["monthly_price"] == "84.50"
    assert row["suggested_decision"] == "accept"
    assert row["status"] == "pending"
    assert row["underwriter_note"] is None
    assert row["created_at"]  # non-empty string


def test_list_quotes_decodes_reasons_as_list(connection):
    save_quote(
        connection,
        sample_quote(),
        "40.00",
        suggested_decision="refer",
        reasons=["Driver is under 21.", "Car is more than 20 years old."],
    )

    rows = list_quotes(connection)

    assert rows[0]["reasons"] == ["Driver is under 21.", "Car is more than 20 years old."]


def test_list_quotes_handles_empty_reasons_list(connection):
    save_quote(connection, sample_quote(), "40.00")

    rows = list_quotes(connection)

    assert rows[0]["reasons"] == []


def test_list_quotes_several_quotes_returns_newest_first(connection):
    first_id = save_quote(connection, sample_quote(full_name="Alice"), "40.00")
    second_id = save_quote(connection, sample_quote(full_name="Bob"), "52.00")
    third_id = save_quote(connection, sample_quote(full_name="Carol"), "60.00")

    rows = list_quotes(connection)

    assert [row["id"] for row in rows] == [third_id, second_id, first_id]
    assert [row["full_name"] for row in rows] == ["Carol", "Bob", "Alice"]


def test_update_decision_sets_status_and_note(connection):
    row_id = save_quote(connection, sample_quote(), "40.00")

    update_decision(connection, row_id, "approved", "Looks fine.")

    rows = list_quotes(connection)
    row = rows[0]
    assert row["status"] == "approved"
    assert row["underwriter_note"] == "Looks fine."


def test_update_decision_allows_null_note(connection):
    row_id = save_quote(connection, sample_quote(), "40.00")

    update_decision(connection, row_id, "declined", None)

    rows = list_quotes(connection)
    assert rows[0]["status"] == "declined"
    assert rows[0]["underwriter_note"] is None


def test_update_decision_only_affects_targeted_row(connection):
    first_id = save_quote(connection, sample_quote(full_name="Alice"), "40.00")
    second_id = save_quote(connection, sample_quote(full_name="Bob"), "52.00")

    update_decision(connection, first_id, "approved", "Fine.")

    rows = {row["id"]: row for row in list_quotes(connection)}
    assert rows[first_id]["status"] == "approved"
    assert rows[second_id]["status"] == "pending"


def test_update_decision_on_missing_id_does_not_raise(connection):
    # No row with this id exists; the UPDATE simply affects zero rows
    update_decision(connection, 999, "approved", "Fine.")
    assert list_quotes(connection) == []
