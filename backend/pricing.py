"""Monthly price calculation for a quote.

Rules, applied in this order:
- base monthly price: 3% of vehicle_value / 12 when vehicle_value is given,
  otherwise a flat 40.00
- multiply by a coverage factor (Basic 1.0, Standard 1.3, Premium 1.6)
- multiply by an age factor from dob (under 25: 1.4, 25-69: 1.0, 70+: 1.2)
- apply a no claims discount of 5% per year, capped at 50%
- add a flat 5.00 surcharge if the car is more than 15 years old
- apply a minimum monthly premium of 20.00, last

The caller passes today's date so results are repeatable in tests.

price_breakdown() runs these same steps and returns one entry per step, so
it and calculate_monthly_price() can never disagree: calculate_monthly_price
simply reads the final step's amount.
"""

from decimal import Decimal, ROUND_HALF_UP

from validate import calc_age, normalize_no_claims_years, normalize_vehicle_value

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

VEHICLE_VALUE_RATE = Decimal("0.03")
MONTHS_PER_YEAR = Decimal("12")

MIN_PREMIUM = Decimal("20.00")

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


# The starting monthly price before any factors: 3% of vehicle_value / 12
# when given, otherwise the flat base price
def base_price(data):
    vehicle_value = normalize_vehicle_value(data.get("vehicle_value"))
    if vehicle_value is not None:
        return (vehicle_value * VEHICLE_VALUE_RATE) / MONTHS_PER_YEAR
    return BASE_PRICE


# Runs the pricing rules step by step, keeping the running total unrounded
# so later steps are not affected by display rounding. Each entry's amount
# is only rounded for display, once the value for that step is final.
def price_breakdown(data, today):
    steps = []

    price = base_price(data)
    steps.append(("Base price", price))

    coverage_type = data["coverage_type"]
    price = price * coverage_factor(coverage_type)
    steps.append((f"Coverage factor ({coverage_type})", price))

    age = calc_age(data["dob"], today)
    price = price * age_factor(age)
    steps.append(("Age factor", price))

    no_claims_years = normalize_no_claims_years(data.get("no_claims_years"))
    price = price * no_claims_discount_factor(no_claims_years)
    steps.append((f"No claims discount ({no_claims_years} years)", price))

    if is_old_car(data["car_year"], today):
        price = price + OLD_CAR_SURCHARGE
    steps.append(("Old car surcharge", price))

    if price < MIN_PREMIUM:
        price = MIN_PREMIUM
    steps.append(("Minimum premium", price))

    return [
        {"label": label, "amount": str(amount.quantize(CENTS, rounding=ROUND_HALF_UP))}
        for label, amount in steps
    ]


# The final monthly price as a string like "84.50"; always the last step of
# price_breakdown, so the two can never disagree
def calculate_monthly_price(data, today):
    return price_breakdown(data, today)[-1]["amount"]
