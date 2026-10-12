"""SQLite storage for quotes.

The table is created here (no separate schema file) and all queries are
parameterised so request data is never spliced into SQL text.
"""

import sqlite3
from datetime import datetime, timezone

CREATE_QUOTES_TABLE = """
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    email TEXT NOT NULL,
    car_make TEXT NOT NULL,
    car_model TEXT NOT NULL,
    car_year INTEGER NOT NULL,
    coverage_type TEXT NOT NULL,
    monthly_price TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

INSERT_QUOTE = """
INSERT INTO quotes (
    full_name, dob, email, car_make, car_model, car_year,
    coverage_type, monthly_price, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# id DESC is used rather than created_at, since two rows saved in the same
# test (or the same instant) can share an identical timestamp
SELECT_QUOTES_NEWEST_FIRST = """
SELECT * FROM quotes ORDER BY id DESC
"""


# Creates the quotes table if it does not already exist
def init_db(connection):
    connection.execute(CREATE_QUOTES_TABLE)
    connection.commit()


# Inserts one quote row; created_at is set here, not by the caller
def save_quote(connection, data, monthly_price):
    created_at = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        INSERT_QUOTE,
        (
            data["full_name"],
            data["dob"],
            data["email"],
            data["car_make"],
            data["car_model"],
            int(data["car_year"]),
            data["coverage_type"],
            monthly_price,
            created_at,
        ),
    )
    connection.commit()
    return cursor.lastrowid


# Returns every saved quote as a list of dicts (one per row), newest first.
# Built from cursor.description rather than relying on connection.row_factory,
# since nothing else in this file sets that.
def list_quotes(connection):
    cursor = connection.execute(SELECT_QUOTES_NEWEST_FIRST)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
