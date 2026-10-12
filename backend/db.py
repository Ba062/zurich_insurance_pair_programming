"""SQLite storage for quotes.

The table is created here (no separate schema file) and all queries are
parameterised so request data is never spliced into SQL text.
"""

import json
import sqlite3
from datetime import datetime, timezone

from validate import normalize_no_claims_years, normalize_vehicle_value

CREATE_QUOTES_TABLE = """
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    email TEXT NOT NULL,
    car_make TEXT NOT NULL,
    car_model TEXT NOT NULL,
    car_year INTEGER NOT NULL,
    vehicle_value TEXT,
    coverage_type TEXT NOT NULL,
    no_claims_years INTEGER NOT NULL DEFAULT 0,
    monthly_price TEXT NOT NULL,
    suggested_decision TEXT,
    reasons TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    underwriter_note TEXT,
    created_at TEXT NOT NULL
)
"""

INSERT_QUOTE = """
INSERT INTO quotes (
    full_name, dob, email, car_make, car_model, car_year, vehicle_value,
    coverage_type, no_claims_years, monthly_price, suggested_decision, reasons,
    status, underwriter_note, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

UPDATE_DECISION = """
UPDATE quotes SET status = ?, underwriter_note = ? WHERE id = ?
"""

# id DESC is used rather than created_at, since two rows saved in the same
# test (or the same instant) can share an identical timestamp
SELECT_QUOTES_NEWEST_FIRST = """
SELECT * FROM quotes ORDER BY id DESC
"""

DEFAULT_STATUS = "pending"


# Creates the quotes table if it does not already exist
def init_db(connection):
    connection.execute(CREATE_QUOTES_TABLE)
    connection.commit()


# Inserts one quote row; created_at and status are set here, not by the
# caller. suggested_decision/reasons come from underwriting.assess_risk,
# but are optional so callers that have not run that check yet still work.
# no_claims_years defaults to 0, and vehicle_value is stored as text (or
# NULL when missing), both using the same rules validate.py uses when
# checking those fields.
def save_quote(connection, data, monthly_price, suggested_decision=None, reasons=None):
    created_at = datetime.now(timezone.utc).isoformat()
    reasons_json = json.dumps(reasons or [])
    no_claims_years = normalize_no_claims_years(data.get("no_claims_years"))
    vehicle_value = normalize_vehicle_value(data.get("vehicle_value"))
    vehicle_value_text = str(vehicle_value) if vehicle_value is not None else None
    cursor = connection.execute(
        INSERT_QUOTE,
        (
            data["full_name"],
            data["dob"],
            data["email"],
            data["car_make"],
            data["car_model"],
            int(data["car_year"]),
            vehicle_value_text,
            data["coverage_type"],
            no_claims_years,
            monthly_price,
            suggested_decision,
            reasons_json,
            DEFAULT_STATUS,
            None,
            created_at,
        ),
    )
    connection.commit()
    return cursor.lastrowid


# Sets the underwriter's decision on a quote. Silently affects zero rows if
# quote_id does not exist, same as a plain UPDATE would.
def update_decision(connection, quote_id, status, note):
    connection.execute(UPDATE_DECISION, (status, note, quote_id))
    connection.commit()


# Returns every saved quote as a list of dicts (one per row), newest first.
# Built from cursor.description rather than relying on connection.row_factory,
# since nothing else in this file sets that. The stored reasons JSON text is
# decoded back into a list for callers.
def list_quotes(connection):
    cursor = connection.execute(SELECT_QUOTES_NEWEST_FIRST)
    columns = [description[0] for description in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    for row in rows:
        row["reasons"] = json.loads(row["reasons"]) if row["reasons"] else []
    return rows
