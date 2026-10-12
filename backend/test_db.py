"""Tests for backend/db.py using an in-memory SQLite database."""

import sqlite3

import pytest

from db import init_db, save_quote


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
