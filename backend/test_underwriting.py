"""Tests for backend/underwriting.py."""

from datetime import date

from underwriting import assess_risk


def base_payload(**overrides):
    today = date(2024, 6, 15)
    data = {
        "dob": date(today.year - 40, today.month, today.day).isoformat(),
        "car_year": today.year - 5,
    }
    data.update(overrides)
    return data


TODAY = date(2024, 6, 15)


def dob_for_age(age, today=TODAY):
    # Same month/day as today so calc_age treats the birthday as "today",
    # giving exactly `age` years (matches validate.calc_age's own boundary rule)
    return date(today.year - age, today.month, today.day).isoformat()


def test_assess_risk_accepts_when_no_rules_triggered():
    data = base_payload()
    result = assess_risk(data, TODAY)
    assert result == {"decision": "accept", "reasons": ["No referral rules triggered"]}


def test_assess_risk_refers_young_driver():
    data = base_payload(dob=dob_for_age(19))
    result = assess_risk(data, TODAY)
    assert result["decision"] == "refer"
    assert "Driver is under 21." in result["reasons"]


def test_assess_risk_boundary_age_20_refers():
    data = base_payload(dob=dob_for_age(20))
    result = assess_risk(data, TODAY)
    assert result["decision"] == "refer"
    assert "Driver is under 21." in result["reasons"]


def test_assess_risk_boundary_age_21_accepts():
    data = base_payload(dob=dob_for_age(21))
    result = assess_risk(data, TODAY)
    assert result == {"decision": "accept", "reasons": ["No referral rules triggered"]}


def test_assess_risk_refers_senior_driver():
    data = base_payload(dob=dob_for_age(80))
    result = assess_risk(data, TODAY)
    assert result["decision"] == "refer"
    assert "Driver is over 75." in result["reasons"]


def test_assess_risk_boundary_age_75_accepts():
    data = base_payload(dob=dob_for_age(75))
    result = assess_risk(data, TODAY)
    assert result == {"decision": "accept", "reasons": ["No referral rules triggered"]}


def test_assess_risk_boundary_age_76_refers():
    data = base_payload(dob=dob_for_age(76))
    result = assess_risk(data, TODAY)
    assert result["decision"] == "refer"
    assert "Driver is over 75." in result["reasons"]


def test_assess_risk_refers_old_car():
    data = base_payload(car_year=TODAY.year - 25)
    result = assess_risk(data, TODAY)
    assert result["decision"] == "refer"
    assert "Car is more than 20 years old." in result["reasons"]


def test_assess_risk_boundary_car_age_20_accepts():
    data = base_payload(car_year=TODAY.year - 20)
    result = assess_risk(data, TODAY)
    assert result == {"decision": "accept", "reasons": ["No referral rules triggered"]}


def test_assess_risk_boundary_car_age_21_refers():
    data = base_payload(car_year=TODAY.year - 21)
    result = assess_risk(data, TODAY)
    assert result["decision"] == "refer"
    assert "Car is more than 20 years old." in result["reasons"]


def test_assess_risk_multiple_reasons_when_several_rules_triggered():
    data = base_payload(dob=dob_for_age(19), car_year=TODAY.year - 25)
    result = assess_risk(data, TODAY)
    assert result["decision"] == "refer"
    assert "Driver is under 21." in result["reasons"]
    assert "Car is more than 20 years old." in result["reasons"]
    assert len(result["reasons"]) == 2
