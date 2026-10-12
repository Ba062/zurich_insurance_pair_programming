"""Monthly price calculation for a quote.

Rules:
- base price 40.00 per month
- multiply by a coverage factor (Basic 1.0, Standard 1.3, Premium 1.6)
- multiply by an age factor from dob (under 25: 1.4, 25-69: 1.0, 70+: 1.2)
- apply a no claims discount of 5% per year, capped at 50%, after the
  coverage and age factors and before the old car surcharge
- add a flat 5.00 surcharge if the car is more than 15 years old

The caller passes today's date so results are repeatable in tests.
"""

from decimal import Decimal, ROUND_HALF_UP

from validate import calc_age, normalize_no_claims_years

BASE_PRICE = Decimal("40.00")

COVERAGE_FACTORS = {
    "Basic": Decimal("1.0"),
    "Standard": Decimal("1.3"),
    "Premium": Decimal("1.6"),
}

YOUNG_DRIVER_AGE = 25
SENIOR_DRIVER_AGE = 70
YOUNG_DRIVER_FACTOR = Decimal("1.4")
STANDARD_DRIVER_FACTOR = Decimal("1.0")
SENIOR_DRIVER_FACTOR = Decimal("1.2")

NO_CLAIMS_DISCOUNT_PER_YEAR = Decimal("0.05")
MAX_NO_CLAIMS_DISCOUNT = Decimal("0.50")

OLD_CAR_AGE_YEARS = 15
OLD_CAR_SURCHARGE = Decimal("5.00")

CENTS = Decimal("0.01")


# Looks up the coverage factor, or raises if the coverage type is unknown
def coverage_factor(coverage_type):
    try:
        return COVERAGE_FACTORS[coverage_type]
    except KeyError:
        raise ValueError(f"Unknown coverage type: {coverage_type}")


# Works out the age factor for a driver's age
def age_factor(age):
    if age < YOUNG_DRIVER_AGE:
        return YOUNG_DRIVER_FACTOR
    if age >= SENIOR_DRIVER_AGE:
        return SENIOR_DRIVER_FACTOR
    return STANDARD_DRIVER_FACTOR


# Multiplier for the no claims discount: 5% per year, capped at 50% off
def no_claims_discount_factor(years):
    discount = min(Decimal(years) * NO_CLAIMS_DISCOUNT_PER_YEAR, MAX_NO_CLAIMS_DISCOUNT)
    return Decimal("1") - discount


# True when the car is older than the surcharge threshold
def is_old_car(car_year, today):
    return (today.year - int(car_year)) > OLD_CAR_AGE_YEARS


# Combine the rules above into a monthly price string like "84.50"
def calculate_monthly_price(data, today):
    coverage = coverage_factor(data["coverage_type"])
    driver = age_factor(calc_age(data["dob"], today))

    price = BASE_PRICE * coverage * driver

    no_claims_years = normalize_no_claims_years(data.get("no_claims_years"))
    price *= no_claims_discount_factor(no_claims_years)

    if is_old_car(data["car_year"], today):
        price += OLD_CAR_SURCHARGE

    price = price.quantize(CENTS, rounding=ROUND_HALF_UP)
    return str(price)
