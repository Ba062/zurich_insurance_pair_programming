"""Tests for backend/pricing.py: one test per pricing rule, plus the
boundary values, with expected totals worked out by hand."""

from datetime import date

import pytest

from pricing import COVERAGE_FACTORS, calculate_monthly_price
from validate import QUOTE_RULES

TODAY = date(2024, 6, 15)

NEW_CAR_YEAR = "2014"  # 10 years old: no surcharge
OLD_CAR_YEAR = "2008"  # 16 years old: surcharge applies
CAR_AGE_15_YEAR = "2009"  # exactly 15 years old: no surcharge (not "more than")
CAR_AGE_16_YEAR = "2008"  # exactly 16 years old: surcharge applies

STANDARD_AGE_DOB = "1984-06-15"  # age 40 on TODAY
YOUNG_DOB = "2000-06-10"  # age 24 on TODAY (birthday already passed)
SENIOR_DOB = "1954-06-10"  # age 70 on TODAY
AGE_25_DOB = "1999-06-15"  # age exactly 25 on TODAY
AGE_69_DOB = "1955-06-10"  # age exactly 69 on TODAY
AGE_30_DOB = "1994-06-15"  # age exactly 30 on TODAY


def base_payload(**overrides):
    payload = {
        "dob": STANDARD_AGE_DOB,
        "coverage_type": "Basic",
        "car_year": NEW_CAR_YEAR,
    }
    payload.update(overrides)
    return payload


# --- base price / Basic coverage --------------------------------------------

def test_calculate_monthly_price_basic_coverage():
    # 40.00 * 1.0 (Basic) * 1.0 (standard age), new car: no surcharge
    price = calculate_monthly_price(base_payload(coverage_type="Basic"), TODAY)
    assert price == "40.00"


# --- coverage factor ----------------------------------------------------------

def test_calculate_monthly_price_standard_coverage():
    # 40.00 * 1.3 * 1.0 = 52.00
    price = calculate_monthly_price(base_payload(coverage_type="Standard"), TODAY)
    assert price == "52.00"


def test_calculate_monthly_price_premium_coverage():
    # 40.00 * 1.6 * 1.0 = 64.00
    price = calculate_monthly_price(base_payload(coverage_type="Premium"), TODAY)
    assert price == "64.00"


def test_calculate_monthly_price_unknown_coverage_raises():
    with pytest.raises(ValueError):
        calculate_monthly_price(base_payload(coverage_type="Gold"), TODAY)


# --- coverage types stay in sync with validate.py ----------------------------

def test_coverage_factors_match_validate_coverages():
    # Guards against the two rule lists drifting apart: a coverage type
    # accepted by validate_quote must have a price factor here, and vice versa
    assert set(COVERAGE_FACTORS.keys()) == set(QUOTE_RULES["COVERAGES"])


# --- age factor ----------------------------------------------------------------

def test_calculate_monthly_price_young_driver():
    # 40.00 * 1.0 * 1.4 = 56.00
    price = calculate_monthly_price(base_payload(dob=YOUNG_DOB), TODAY)
    assert price == "56.00"


def test_calculate_monthly_price_senior_driver():
    # 40.00 * 1.0 * 1.2 = 48.00
    price = calculate_monthly_price(base_payload(dob=SENIOR_DOB), TODAY)
    assert price == "48.00"


def test_calculate_monthly_price_boundary_age_25_is_standard():
    # Age exactly 25: still the 25-69 band, factor 1.0 -> 40.00
    price = calculate_monthly_price(base_payload(dob=AGE_25_DOB), TODAY)
    assert price == "40.00"


def test_calculate_monthly_price_boundary_age_69_is_standard():
    # Age exactly 69: still the 25-69 band, factor 1.0 -> 40.00
    price = calculate_monthly_price(base_payload(dob=AGE_69_DOB), TODAY)
    assert price == "40.00"


def test_calculate_monthly_price_boundary_age_70_is_senior():
    # Age exactly 70: senior band, factor 1.2 -> 48.00
    price = calculate_monthly_price(base_payload(dob=SENIOR_DOB), TODAY)
    assert price == "48.00"


# --- old car surcharge ------------------------------------------------------

def test_calculate_monthly_price_old_car_surcharge():
    # 40.00 * 1.0 * 1.0 + 5.00 surcharge = 45.00
    price = calculate_monthly_price(base_payload(car_year=OLD_CAR_YEAR), TODAY)
    assert price == "45.00"


def test_calculate_monthly_price_boundary_car_age_15_no_surcharge():
    # Exactly 15 years old is not "more than 15": no surcharge -> 40.00
    price = calculate_monthly_price(base_payload(car_year=CAR_AGE_15_YEAR), TODAY)
    assert price == "40.00"


def test_calculate_monthly_price_boundary_car_age_16_surcharge():
    # Exactly 16 years old: surcharge applies -> 45.00
    price = calculate_monthly_price(base_payload(car_year=CAR_AGE_16_YEAR), TODAY)
    assert price == "45.00"


# --- no claims discount -------------------------------------------------------

def test_calculate_monthly_price_no_claims_discount_worked_example():
    # Standard cover, age 30, newer car, 4 years no claims:
    # 40.00 * 1.3 * 1.0 = 52.00, 4 * 5% = 20% discount -> 52.00 * 0.8 = 41.60
    payload = base_payload(coverage_type="Standard", dob=AGE_30_DOB, no_claims_years="4")
    price = calculate_monthly_price(payload, TODAY)
    assert price == "41.60"


def test_calculate_monthly_price_no_claims_missing_defaults_to_zero():
    payload = base_payload()
    payload.pop("no_claims_years", None)
    price = calculate_monthly_price(payload, TODAY)
    assert price == "40.00"


def test_calculate_monthly_price_no_claims_boundary_zero_years_no_discount():
    price = calculate_monthly_price(base_payload(no_claims_years="0"), TODAY)
    assert price == "40.00"


def test_calculate_monthly_price_no_claims_boundary_ten_years_reaches_cap():
    # 10 * 5% = 50%, exactly the cap -> 40.00 * 0.5 = 20.00
    price = calculate_monthly_price(base_payload(no_claims_years="10"), TODAY)
    assert price == "20.00"


def test_calculate_monthly_price_no_claims_boundary_eleven_years_still_capped():
    # 11 * 5% = 55%, capped at 50% -> same as 10 years
    price = calculate_monthly_price(base_payload(no_claims_years="11"), TODAY)
    assert price == "20.00"


def test_calculate_monthly_price_no_claims_boundary_fifty_years_still_capped():
    price = calculate_monthly_price(base_payload(no_claims_years="50"), TODAY)
    assert price == "20.00"


def test_calculate_monthly_price_no_claims_discount_applies_before_old_car_surcharge():
    # 40.00 * 1.0 * 1.0 = 40.00, 50% cap -> 20.00, then + 5.00 surcharge = 25.00
    payload = base_payload(car_year=OLD_CAR_YEAR, no_claims_years="10")
    price = calculate_monthly_price(payload, TODAY)
    assert price == "25.00"


# --- combined rules ----------------------------------------------------------

def test_calculate_monthly_price_all_rules_combined():
    # 40.00 * 1.6 (Premium) * 1.4 (young) + 5.00 (old car) = 89.60 + 5.00 = 94.60
    payload = base_payload(
        coverage_type="Premium", dob=YOUNG_DOB, car_year=OLD_CAR_YEAR
    )
    price = calculate_monthly_price(payload, TODAY)
    assert price == "94.60"
