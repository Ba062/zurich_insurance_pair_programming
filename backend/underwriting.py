"""Underwriting rules: decides whether a quote can be accepted automatically
or must be referred for manual review.
"""

from validate import calc_age

MIN_AGE = 21
MAX_AGE = 75
MAX_CAR_AGE = 20


# Returns {"decision": "accept" or "refer", "reasons": [...]}.
# Each triggered rule adds one plain-sentence reason; if none trigger, the
# decision is "accept" with a single reason explaining why.
def assess_risk(data, today):
    reasons = []

    age = calc_age(data.get("dob"), today)
    if age is not None and age < MIN_AGE:
        reasons.append(f"Driver is under {MIN_AGE}.")
    if age is not None and age > MAX_AGE:
        reasons.append(f"Driver is over {MAX_AGE}.")

    car_year = data.get("car_year")
    if car_year is not None:
        car_age = today.year - int(car_year)
        if car_age > MAX_CAR_AGE:
            reasons.append(f"Car is more than {MAX_CAR_AGE} years old.")

    if not reasons:
        return {"decision": "accept", "reasons": ["No referral rules triggered"]}

    return {"decision": "refer", "reasons": reasons}
