"""Business rules for the quote form, mirrored from frontend/validate.js.
The frontend checks these per step for fast feedback; here we check
everything at once since the whole payload arrives together."""

import re
import unicodedata
from datetime import date

QUOTE_RULES = {
    "MIN_AGE": 18,
    "MAX_AGE": 100,
    "MIN_CAR_YEAR": 1980,
    "MAX_NAME_LENGTH": 100,
    "MAX_TEXT_LENGTH": 50,
    "COVERAGES": ["Basic", "Standard", "Premium"],
}

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DOB_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
YEAR_RE = re.compile(r"^\d{4}$")


# True for anything that is not a string with visible characters
def is_blank(value):
    return not isinstance(value, str) or value.strip() == ""


# Whole years between a YYYY-MM-DD date and today, or None if the date is invalid
def calc_age(dob, today):
    match = DOB_RE.match(dob or "")
    if not match:
        return None

    year, month, day = (int(part) for part in match.groups())
    try:
        # date() itself rejects dates like 2000-02-31
        date(year, month, day)
    except ValueError:
        return None

    had_birthday = (today.month, today.day) >= (month, day)
    age = today.year - year
    return age if had_birthday else age - 1


# Names may be split into letter groups by one of these (e.g. "Anne-Marie O'Brien")
NAME_SEPARATORS = " '’-"


# Unicode letters and combining marks, so accented names like "Müller" pass
def is_name_char(char):
    return unicodedata.category(char)[0] in ("L", "M")


# Mirrors NAME_RE in frontend/validate.js: letters in groups split by single
# separators, with no leading, trailing or doubled separator
def has_valid_name_shape(text):
    previous_was_separator = True  # starting this way rejects a leading separator
    for char in text:
        if char in NAME_SEPARATORS:
            if previous_was_separator:
                return False
            previous_was_separator = True
        elif is_name_char(char):
            previous_was_separator = False
        else:
            return False
    return not previous_was_separator  # also rejects a trailing separator


# Each field validator returns an error message, or "" when the value is fine
def validate_name(value):
    if is_blank(value):
        return "Full name is required."
    if len(value.strip()) > QUOTE_RULES["MAX_NAME_LENGTH"]:
        return "Name is too long."
    if not has_valid_name_shape(value.strip()):
        return "Name can only contain letters, spaces, hyphens and apostrophes."
    return ""


def validate_dob(value, today):
    age = calc_age(value, today)
    if age is None or age > QUOTE_RULES["MAX_AGE"]:
        return "Enter a valid date of birth."
    if age < QUOTE_RULES["MIN_AGE"]:
        return f"You must be at least {QUOTE_RULES['MIN_AGE']} years old."
    return ""


def validate_email(value):
    if is_blank(value):
        return "Email is required."
    email = value.strip()
    if len(email) > 254 or not EMAIL_RE.match(email):
        return "Enter a valid email address."
    return ""


def validate_required_text(label, value, max_length):
    if is_blank(value):
        return f"{label} is required."
    if len(value.strip()) > max_length:
        return f"{label} is too long."
    return ""


def validate_year(value, today):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return "Year is required."
    text = str(value).strip()
    if not YEAR_RE.match(text):
        return "Enter a 4-digit year."
    year = int(text)
    max_year = today.year
    if year < QUOTE_RULES["MIN_CAR_YEAR"] or year > max_year:
        return f"Year must be between {QUOTE_RULES['MIN_CAR_YEAR']} and {max_year}."
    return ""


def validate_coverage_type(value):
    if value not in QUOTE_RULES["COVERAGES"]:
        return "Choose a coverage plan."
    return ""


# Turn {field: message} into {field: message} with the empty ones removed
def collect_errors(checks):
    return {field: message for field, message in checks.items() if message}


# Validate the whole payload at once; today defaults to the real date
def validate_quote(data, today=None):
    if today is None:
        today = date.today()

    return collect_errors({
        "full_name": validate_name(data.get("full_name")),
        "dob": validate_dob(data.get("dob"), today),
        "email": validate_email(data.get("email")),
        "car_make": validate_required_text(
            "Car Brand", data.get("car_make"), QUOTE_RULES["MAX_TEXT_LENGTH"]
        ),
        "car_model": validate_required_text(
            "Model", data.get("car_model"), QUOTE_RULES["MAX_TEXT_LENGTH"]
        ),
        "car_year": validate_year(data.get("car_year"), today),
        "coverage_type": validate_coverage_type(data.get("coverage_type")),
    })
