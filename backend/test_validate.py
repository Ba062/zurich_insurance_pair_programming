"""Tests for backend/validate.py: one valid, one blank, one too-long and the
boundary values for each function, mirroring the rules in validate.py."""

from datetime import date

from validate import (
    QUOTE_RULES,
    calc_age,
    collect_errors,
    has_valid_name_shape,
    is_blank,
    validate_coverage_type,
    validate_dob,
    validate_email,
    validate_name,
    validate_quote,
    validate_required_text,
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


NAME_SHAPE_ERROR = "Name can only contain letters, spaces, hyphens and apostrophes."


def test_validate_name_allows_separators_and_accents():
    assert validate_name("Anne-Marie O'Brien") == ""
    assert validate_name("Fran\u00e7ois M\u00fcller") == ""
    assert validate_name("O\u2019Brien") == ""  # curly apostrophe
    assert validate_name("  Jane Doe  ") == ""  # trimmed before checking


def test_validate_name_rejects_digits_and_symbols():
    assert validate_name("Jane123") == NAME_SHAPE_ERROR
    assert validate_name("Jane@Doe") == NAME_SHAPE_ERROR
    assert validate_name("<b>Jane</b>") == NAME_SHAPE_ERROR
    assert validate_name("123") == NAME_SHAPE_ERROR


def test_validate_name_rejects_bad_separators():
    assert validate_name("Jane  Doe") == NAME_SHAPE_ERROR  # doubled space
    assert validate_name("-Jane") == NAME_SHAPE_ERROR  # leading
    assert validate_name("Jane-") == NAME_SHAPE_ERROR  # trailing
    assert validate_name("Jane--Doe") == NAME_SHAPE_ERROR


# --- has_valid_name_shape ---------------------------------------------------

def test_has_valid_name_shape_valid():
    assert has_valid_name_shape("Jane Doe") is True
    assert has_valid_name_shape("Anne-Marie") is True


def test_has_valid_name_shape_blank():
    assert has_valid_name_shape("") is False


def test_has_valid_name_shape_invalid_characters():
    assert has_valid_name_shape("Jane1") is False
    assert has_valid_name_shape("Jane_Doe") is False


def test_has_valid_name_shape_boundary_single_letter():
    assert has_valid_name_shape("a") is True
    assert has_valid_name_shape("-") is False


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


def test_validate_quote_blank_car_brand_uses_car_brand_label():
    payload = valid_payload()
    payload["car_make"] = ""
    errors = validate_quote(payload, TODAY)
    assert errors == {"car_make": "Car Brand is required."}


def test_validate_quote_rejects_digits_in_name():
    payload = valid_payload()
    payload["full_name"] = "Jane123"
    errors = validate_quote(payload, TODAY)
    assert errors == {
        "full_name": "Name can only contain letters, spaces, hyphens and apostrophes."
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
