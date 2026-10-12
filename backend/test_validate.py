"""Tests for backend/validate.py: one valid, one blank, one too-long and the
boundary values for each function, mirroring the rules in validate.py."""

from datetime import date
from decimal import Decimal

from validate import (
    QUOTE_RULES,
    calc_age,
    collect_errors,
    is_blank,
    normalize_no_claims_years,
    normalize_vehicle_value,
    validate_coverage_type,
    validate_dob,
    validate_email,
    validate_name,
    validate_no_claims_years,
    validate_quote,
    validate_required_text,
    validate_vehicle_value,
    validate_year,
)

TODAY = date(2024, 6, 15)


# --- is_blank ---------------------------------------------------------

def test_is_blank_valid():
    assert is_blank("Jane") is False


def test_is_blank_blank():
    assert is_blank("") is True
    assert is_blank("   ") is True


def test_is_blank_non_string():
    # Not a "too long" case for this function, but covers non-string input
    assert is_blank(None) is True
    assert is_blank(123) is True


def test_is_blank_boundary_single_char():
    assert is_blank("a") is False


# --- calc_age -----------------------------------------------------------

def test_calc_age_valid():
    assert calc_age("2000-01-01", TODAY) == 24


def test_calc_age_blank():
    assert calc_age("", TODAY) is None


def test_calc_age_invalid_date_rolls_over():
    # 2000-02-30 does not exist; must not silently roll over
    assert calc_age("2000-02-30", TODAY) is None


def test_calc_age_boundary_birthday_today():
    # Born exactly 18 years ago today: birthday has happened
    dob = f"{TODAY.year - 18:04d}-{TODAY.month:02d}-{TODAY.day:02d}"
    assert calc_age(dob, TODAY) == 18


def test_calc_age_boundary_day_before_birthday():
    # Birthday is tomorrow: one year has not yet elapsed
    tomorrow = date(TODAY.year, TODAY.month, TODAY.day + 1)
    dob = f"{TODAY.year - 18:04d}-{tomorrow.month:02d}-{tomorrow.day:02d}"
    assert calc_age(dob, TODAY) == 17


# --- validate_name --------------------------------------------------------

def test_validate_name_valid():
    assert validate_name("John Smith") == ""


def test_validate_name_blank():
    assert validate_name("") == "Full name is required."


def test_validate_name_too_long():
    name = "a" * (QUOTE_RULES["MAX_NAME_LENGTH"] + 1)
    assert validate_name(name) == "Name is too long."


def test_validate_name_boundary_max_length():
    name = "a" * QUOTE_RULES["MAX_NAME_LENGTH"]
    assert validate_name(name) == ""


# --- validate_dob ---------------------------------------------------------

def test_validate_dob_valid():
    dob = f"{TODAY.year - 30:04d}-{TODAY.month:02d}-{TODAY.day:02d}"
    assert validate_dob(dob, TODAY) == ""


def test_validate_dob_blank():
    assert validate_dob("", TODAY) == "Enter a valid date of birth."


def test_validate_dob_too_old():
    dob = f"{TODAY.year - (QUOTE_RULES['MAX_AGE'] + 1):04d}-{TODAY.month:02d}-{TODAY.day:02d}"
    assert validate_dob(dob, TODAY) == "Enter a valid date of birth."


def test_validate_dob_boundary_min_age():
    dob = f"{TODAY.year - QUOTE_RULES['MIN_AGE']:04d}-{TODAY.month:02d}-{TODAY.day:02d}"
    assert validate_dob(dob, TODAY) == ""


def test_validate_dob_boundary_below_min_age():
    dob = f"{TODAY.year - (QUOTE_RULES['MIN_AGE'] - 1):04d}-{TODAY.month:02d}-{TODAY.day:02d}"
    assert validate_dob(dob, TODAY) == (
        f"You must be at least {QUOTE_RULES['MIN_AGE']} years old."
    )


def test_validate_dob_boundary_max_age():
    dob = f"{TODAY.year - QUOTE_RULES['MAX_AGE']:04d}-{TODAY.month:02d}-{TODAY.day:02d}"
    assert validate_dob(dob, TODAY) == ""


# --- validate_email --------------------------------------------------------

def test_validate_email_valid():
    assert validate_email("jane@example.com") == ""


def test_validate_email_blank():
    assert validate_email("") == "Email is required."


def test_validate_email_too_long():
    # 254 chars is the limit; push it past that while keeping valid format
    local = "a" * 250
    email = f"{local}@b.com"
    assert len(email) > 254
    assert validate_email(email) == "Enter a valid email address."


def test_validate_email_boundary_max_length():
    # Build an email exactly 254 characters long with a valid shape
    domain = "@example.com"
    local = "a" * (254 - len(domain))
    email = f"{local}{domain}"
    assert len(email) == 254
    assert validate_email(email) == ""


# --- validate_required_text ------------------------------------------------

def test_validate_required_text_valid():
    assert validate_required_text("Make", "Toyota", QUOTE_RULES["MAX_TEXT_LENGTH"]) == ""


def test_validate_required_text_blank():
    assert validate_required_text("Make", "", QUOTE_RULES["MAX_TEXT_LENGTH"]) == "Make is required."


def test_validate_required_text_too_long():
    value = "a" * (QUOTE_RULES["MAX_TEXT_LENGTH"] + 1)
    assert validate_required_text("Make", value, QUOTE_RULES["MAX_TEXT_LENGTH"]) == "Make is too long."


def test_validate_required_text_boundary_max_length():
    value = "a" * QUOTE_RULES["MAX_TEXT_LENGTH"]
    assert validate_required_text("Make", value, QUOTE_RULES["MAX_TEXT_LENGTH"]) == ""


# --- validate_year ----------------------------------------------------------

def test_validate_year_valid():
    assert validate_year("2020", TODAY) == ""


def test_validate_year_blank():
    assert validate_year("", TODAY) == "Year is required."
    assert validate_year(None, TODAY) == "Year is required."


def test_validate_year_too_long():
    assert validate_year("20201", TODAY) == "Enter a 4-digit year."


def test_validate_year_boundary_min_year():
    assert validate_year(str(QUOTE_RULES["MIN_CAR_YEAR"]), TODAY) == ""


def test_validate_year_boundary_below_min_year():
    year = QUOTE_RULES["MIN_CAR_YEAR"] - 1
    assert validate_year(str(year), TODAY) == (
        f"Year must be between {QUOTE_RULES['MIN_CAR_YEAR']} and {TODAY.year}."
    )


def test_validate_year_boundary_current_year():
    assert validate_year(str(TODAY.year), TODAY) == ""


def test_validate_year_boundary_above_current_year():
    year = TODAY.year + 1
    assert validate_year(str(year), TODAY) == (
        f"Year must be between {QUOTE_RULES['MIN_CAR_YEAR']} and {TODAY.year}."
    )


# --- validate_coverage_type -------------------------------------------------

def test_validate_coverage_type_valid():
    assert validate_coverage_type("Basic") == ""


def test_validate_coverage_type_blank():
    assert validate_coverage_type("") == "Choose a coverage plan."
    assert validate_coverage_type(None) == "Choose a coverage plan."


def test_validate_coverage_type_invalid_value():
    assert validate_coverage_type("Gold") == "Choose a coverage plan."


def test_validate_coverage_type_boundary_each_option():
    for option in QUOTE_RULES["COVERAGES"]:
        assert validate_coverage_type(option) == ""


# --- validate_no_claims_years ------------------------------------------------

def test_validate_no_claims_years_missing_is_valid():
    assert validate_no_claims_years(None) == ""


def test_validate_no_claims_years_blank_is_valid():
    assert validate_no_claims_years("") == ""


def test_validate_no_claims_years_valid():
    assert validate_no_claims_years("4") == ""


def test_validate_no_claims_years_boundary_zero():
    assert validate_no_claims_years("0") == ""


def test_validate_no_claims_years_boundary_ten():
    assert validate_no_claims_years("10") == ""


def test_validate_no_claims_years_boundary_eleven():
    assert validate_no_claims_years("11") == ""


def test_validate_no_claims_years_boundary_max():
    assert validate_no_claims_years(str(QUOTE_RULES["MAX_NO_CLAIMS_YEARS"])) == ""


def test_validate_no_claims_years_boundary_above_max():
    year = QUOTE_RULES["MAX_NO_CLAIMS_YEARS"] + 1
    assert validate_no_claims_years(str(year)) == (
        f"Enter a whole number of years from 0 to {QUOTE_RULES['MAX_NO_CLAIMS_YEARS']}."
    )


def test_validate_no_claims_years_negative_invalid():
    assert validate_no_claims_years("-1") == (
        f"Enter a whole number of years from 0 to {QUOTE_RULES['MAX_NO_CLAIMS_YEARS']}."
    )


def test_validate_no_claims_years_non_integer_invalid():
    assert validate_no_claims_years("4.5") == (
        f"Enter a whole number of years from 0 to {QUOTE_RULES['MAX_NO_CLAIMS_YEARS']}."
    )


# --- normalize_no_claims_years -----------------------------------------------

def test_normalize_no_claims_years_missing_defaults_to_zero():
    assert normalize_no_claims_years(None) == 0


def test_normalize_no_claims_years_blank_defaults_to_zero():
    assert normalize_no_claims_years("") == 0


def test_normalize_no_claims_years_valid_string():
    assert normalize_no_claims_years("4") == 4


def test_normalize_no_claims_years_boundary_zero():
    assert normalize_no_claims_years("0") == 0


def test_normalize_no_claims_years_boundary_max():
    assert normalize_no_claims_years("50") == 50


# --- validate_vehicle_value --------------------------------------------------

def test_validate_vehicle_value_missing_is_valid():
    assert validate_vehicle_value(None) == ""


def test_validate_vehicle_value_blank_is_valid():
    assert validate_vehicle_value("") == ""


def test_validate_vehicle_value_valid():
    assert validate_vehicle_value("12000") == ""


def test_validate_vehicle_value_valid_number_type():
    assert validate_vehicle_value(12000) == ""
    assert validate_vehicle_value(12000.5) == ""


def test_validate_vehicle_value_boundary_min():
    assert validate_vehicle_value(str(QUOTE_RULES["MIN_VEHICLE_VALUE"])) == ""


def test_validate_vehicle_value_boundary_below_min():
    value = QUOTE_RULES["MIN_VEHICLE_VALUE"] - Decimal("0.01")
    assert validate_vehicle_value(str(value)) != ""


def test_validate_vehicle_value_boundary_max():
    assert validate_vehicle_value(str(QUOTE_RULES["MAX_VEHICLE_VALUE"])) == ""


def test_validate_vehicle_value_boundary_above_max():
    value = QUOTE_RULES["MAX_VEHICLE_VALUE"] + 0.01
    assert validate_vehicle_value(str(value)) != ""


def test_validate_vehicle_value_boundary_two_decimals():
    assert validate_vehicle_value("12000.12") == ""


def test_validate_vehicle_value_boundary_three_decimals_invalid():
    assert validate_vehicle_value("12000.123") != ""


def test_validate_vehicle_value_rejects_nan():
    assert validate_vehicle_value("NaN") != ""


def test_validate_vehicle_value_rejects_infinity():
    assert validate_vehicle_value("Infinity") != ""
    assert validate_vehicle_value("-Infinity") != ""


def test_validate_vehicle_value_rejects_non_numeric():
    assert validate_vehicle_value("abc") != ""


# --- normalize_vehicle_value --------------------------------------------------

def test_normalize_vehicle_value_missing_returns_none():
    assert normalize_vehicle_value(None) is None


def test_normalize_vehicle_value_blank_returns_none():
    assert normalize_vehicle_value("") is None


def test_normalize_vehicle_value_valid_string():
    assert normalize_vehicle_value("12000") == Decimal("12000")


def test_normalize_vehicle_value_valid_number_type():
    assert normalize_vehicle_value(12000) == Decimal("12000")


# --- collect_errors ----------------------------------------------------------

def test_collect_errors_valid_all_empty():
    assert collect_errors({"a": "", "b": ""}) == {}


def test_collect_errors_blank_entries_dropped():
    assert collect_errors({"a": "", "b": "Required."}) == {"b": "Required."}


def test_collect_errors_many_errors():
    checks = {"a": "Bad a.", "b": "Bad b.", "c": ""}
    assert collect_errors(checks) == {"a": "Bad a.", "b": "Bad b."}


def test_collect_errors_boundary_single_field():
    assert collect_errors({"only": "Bad."}) == {"only": "Bad."}


# --- validate_quote ----------------------------------------------------------

def valid_payload():
    return {
        "full_name": "Jane Doe",
        "dob": f"{TODAY.year - 30:04d}-{TODAY.month:02d}-{TODAY.day:02d}",
        "email": "jane@example.com",
        "car_make": "Toyota",
        "car_model": "Corolla",
        "car_year": "2020",
        "coverage_type": "Standard",
    }


def test_validate_quote_valid():
    assert validate_quote(valid_payload(), TODAY) == {}


def test_validate_quote_blank():
    errors = validate_quote({}, TODAY)
    assert set(errors.keys()) == {
        "full_name",
        "dob",
        "email",
        "car_make",
        "car_model",
        "car_year",
        "coverage_type",
    }


def test_validate_quote_too_long_name():
    payload = valid_payload()
    payload["full_name"] = "a" * (QUOTE_RULES["MAX_NAME_LENGTH"] + 1)
    errors = validate_quote(payload, TODAY)
    assert errors == {"full_name": "Name is too long."}


def test_validate_quote_boundary_values_all_pass():
    payload = valid_payload()
    payload["full_name"] = "a" * QUOTE_RULES["MAX_NAME_LENGTH"]
    payload["car_make"] = "a" * QUOTE_RULES["MAX_TEXT_LENGTH"]
    payload["car_model"] = "a" * QUOTE_RULES["MAX_TEXT_LENGTH"]
    payload["car_year"] = str(QUOTE_RULES["MIN_CAR_YEAR"])
    payload["dob"] = f"{TODAY.year - QUOTE_RULES['MIN_AGE']:04d}-{TODAY.month:02d}-{TODAY.day:02d}"
    assert validate_quote(payload, TODAY) == {}


def test_validate_quote_boundary_no_claims_years_max_passes():
    payload = valid_payload()
    payload["no_claims_years"] = str(QUOTE_RULES["MAX_NO_CLAIMS_YEARS"])
    assert validate_quote(payload, TODAY) == {}


def test_validate_quote_invalid_no_claims_years():
    payload = valid_payload()
    payload["no_claims_years"] = str(QUOTE_RULES["MAX_NO_CLAIMS_YEARS"] + 1)
    errors = validate_quote(payload, TODAY)
    assert "no_claims_years" in errors


def test_validate_quote_boundary_vehicle_value_passes():
    payload = valid_payload()
    payload["vehicle_value"] = "12000"
    assert validate_quote(payload, TODAY) == {}


def test_validate_quote_invalid_vehicle_value():
    payload = valid_payload()
    payload["vehicle_value"] = str(QUOTE_RULES["MAX_VEHICLE_VALUE"] + 1)
    errors = validate_quote(payload, TODAY)
    assert "vehicle_value" in errors
