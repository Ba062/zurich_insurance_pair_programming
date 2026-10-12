const test = require("node:test");
const assert = require("node:assert");
const v = require("./validate.js");

// Fixed "today" so tests do not depend on the real date
const TODAY = new Date(2026, 9, 12); // 12 Oct 2026

test("isBlank", () => {
  assert.strictEqual(v.isBlank(""), true);
  assert.strictEqual(v.isBlank("   "), true);
  assert.strictEqual(v.isBlank(undefined), true);
  assert.strictEqual(v.isBlank("a"), false);
});

test("calcAge", () => {
  assert.strictEqual(v.calcAge("2000-10-12", TODAY), 26); // birthday today
  assert.strictEqual(v.calcAge("2000-10-13", TODAY), 25); // birthday tomorrow
  assert.strictEqual(v.calcAge("not-a-date", TODAY), null);
  assert.strictEqual(v.calcAge("2000-02-31", TODAY), null);
  assert.strictEqual(v.calcAge("", TODAY), null);
});

test("validateName", () => {
  assert.strictEqual(v.validateName("Jane Doe"), "");
  assert.notStrictEqual(v.validateName(""), "");
  assert.notStrictEqual(v.validateName("a".repeat(101)), "");
});

test("validateDob", () => {
  assert.strictEqual(v.validateDob("1990-05-20", TODAY), "");
  assert.notStrictEqual(v.validateDob("2015-01-01", TODAY), ""); // too young
  assert.notStrictEqual(v.validateDob("2030-01-01", TODAY), ""); // future
  assert.notStrictEqual(v.validateDob("1800-01-01", TODAY), ""); // too old
  assert.notStrictEqual(v.validateDob("", TODAY), "");
});

test("validateEmail", () => {
  assert.strictEqual(v.validateEmail("jane@example.com"), "");
  assert.notStrictEqual(v.validateEmail(""), "");
  assert.notStrictEqual(v.validateEmail("jane@"), "");
  assert.notStrictEqual(v.validateEmail("jane example@x.com"), "");
});

test("validateRequiredText", () => {
  assert.strictEqual(v.validateRequiredText("Make", "Toyota", 50), "");
  assert.strictEqual(v.validateRequiredText("Make", "", 50), "Make is required.");
  assert.strictEqual(v.validateRequiredText("Make", "abcdef", 5), "Make is too long.");
});

test("validateYear", () => {
  assert.strictEqual(v.validateYear("2019", TODAY), "");
  assert.notStrictEqual(v.validateYear("", TODAY), "");
  assert.notStrictEqual(v.validateYear("abc", TODAY), "");
  assert.notStrictEqual(v.validateYear("1979", TODAY), "");
  assert.notStrictEqual(v.validateYear("2027", TODAY), "");
});

test("validateCoverageType", () => {
  assert.strictEqual(v.validateCoverageType("Standard"), "");
  assert.notStrictEqual(v.validateCoverageType("Gold"), "");
  assert.notStrictEqual(v.validateCoverageType(undefined), "");
});

test("collectErrors drops empty messages", () => {
  assert.deepStrictEqual(v.collectErrors({ a: "bad", b: "" }), { a: "bad" });
});

test("validateDriver", () => {
  const good = { full_name: "Jane Doe", dob: "1990-05-20", email: "jane@example.com" };
  assert.deepStrictEqual(v.validateDriver(good, TODAY), {});
  const errors = v.validateDriver({}, TODAY);
  assert.deepStrictEqual(Object.keys(errors), ["full_name", "dob", "email"]);
});

test("validateCar", () => {
  const good = { car_make: "Toyota", car_model: "Corolla", car_year: "2019" };
  assert.deepStrictEqual(v.validateCar(good, TODAY), {});
  const errors = v.validateCar({}, TODAY);
  assert.deepStrictEqual(Object.keys(errors), ["car_make", "car_model", "car_year"]);
});

test("validateCoverage", () => {
  assert.deepStrictEqual(v.validateCoverage({ coverage_type: "Basic" }), {});
  assert.deepStrictEqual(Object.keys(v.validateCoverage({})), ["coverage_type"]);
});

test("buildPayload keeps only known fields and makes year a number", () => {
  const payload = v.buildPayload({
    full_name: "Jane Doe",
    dob: "1990-05-20",
    email: "jane@example.com",
    car_make: "Toyota",
    car_model: "Corolla",
    car_year: "2019",
    coverage_type: "Standard",
    extra: "ignored",
  });
  assert.strictEqual(payload.car_year, 2019);
  assert.strictEqual("extra" in payload, false);
  assert.strictEqual(payload.coverage_type, "Standard");
});

test("isValidPrice", () => {
  assert.strictEqual(v.isValidPrice("84.50"), true);
  assert.strictEqual(v.isValidPrice("84.5"), false);
  assert.strictEqual(v.isValidPrice(84.5), false);
  assert.strictEqual(v.isValidPrice("-1.00"), false);
  assert.strictEqual(v.isValidPrice(undefined), false);
});
