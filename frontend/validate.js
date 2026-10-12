// Business rules for the quote form live here, in one place.
// The server must repeat these checks; this file only gives faster feedback.
const QUOTE_RULES = Object.freeze({
  MIN_AGE: 18,
  MAX_AGE: 100,
  MIN_CAR_YEAR: 1980,
  MAX_NAME_LENGTH: 100,
  MAX_TEXT_LENGTH: 50,
  COVERAGES: Object.freeze(["Basic", "Standard", "Premium"]),
});

// Plan names differ per market, but each one maps onto a server tier
// (Basic, Standard, Premium), so server validation and pricing stay the same.
const MARKET_PLANS = Object.freeze({
  uk: Object.freeze({
    name: "United Kingdom",
    currency: "£",
    plans: Object.freeze({
      Basic: Object.freeze({ title: "Third-party only", text: "Covers damage to others." }),
      Standard: Object.freeze({ title: "Third party, fire & theft", text: "Adds theft and fire." }),
      Premium: Object.freeze({ title: "Comprehensive", text: "Adds your own car's damage." }),
    }),
  }),
  swiss: Object.freeze({
    name: "Switzerland",
    currency: "CHF ",
    plans: Object.freeze({
      Basic: Object.freeze({ title: "Liability", text: "Covers damage to others." }),
      Standard: Object.freeze({ title: "Partial casco", text: "Adds theft, fire and natural events." }),
      Premium: Object.freeze({ title: "Full casco", text: "Adds your own car's damage." }),
    }),
  }),
});

// Letters (any alphabet, with accents) in groups separated by one space, hyphen or apostrophe
const NAME_RE = /^[\p{L}\p{M}]+(?:[ '’-][\p{L}\p{M}]+)*$/u;

// True for anything that is not a string with visible characters
function isBlank(value) {
  return typeof value !== "string" || value.trim() === "";
}

// Whole years between a YYYY-MM-DD date and today, or null if the date is invalid
function calcAge(dob, today) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dob || "");
  if (!match) return null;

  const [year, month, day] = match.slice(1).map(Number);
  const date = new Date(year, month - 1, day);
  // Reject dates like 2000-02-31 that JS would silently roll over
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null;
  }

  const hadBirthday =
    today.getMonth() > month - 1 ||
    (today.getMonth() === month - 1 && today.getDate() >= day);
  const age = today.getFullYear() - year;
  return hadBirthday ? age : age - 1;
}

// Each field validator returns an error message, or "" when the value is fine
function validateName(value) {
  if (isBlank(value)) return "Full name is required.";
  if (value.trim().length > QUOTE_RULES.MAX_NAME_LENGTH) return "Name is too long.";
  if (!NAME_RE.test(value.trim())) {
    return "Name can only contain letters, spaces, hyphens and apostrophes.";
  }
  return "";
}

function validateDob(value, today) {
  const age = calcAge(value, today);
  if (age === null || age > QUOTE_RULES.MAX_AGE) return "Enter a valid date of birth.";
  if (age < QUOTE_RULES.MIN_AGE) {
    return `You must be at least ${QUOTE_RULES.MIN_AGE} years old.`;
  }
  return "";
}

function validateEmail(value) {
  if (isBlank(value)) return "Email is required.";
  const email = value.trim();
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return "Enter a valid email address.";
  }
  return "";
}

function validateRequiredText(label, value, maxLength) {
  if (isBlank(value)) return `${label} is required.`;
  if (value.trim().length > maxLength) return `${label} is too long.`;
  return "";
}

function validateYear(value, today) {
  if (isBlank(value)) return "Year is required.";
  if (!/^\d{4}$/.test(value.trim())) return "Enter a 4-digit year.";
  const year = Number(value);
  const maxYear = today.getFullYear();
  if (year < QUOTE_RULES.MIN_CAR_YEAR || year > maxYear) {
    return `Year must be between ${QUOTE_RULES.MIN_CAR_YEAR} and ${maxYear}.`;
  }
  return "";
}

function validateCoverageType(value) {
  if (!QUOTE_RULES.COVERAGES.includes(value)) return "Choose a coverage plan.";
  return "";
}

// Turn { field: message } into { field: message } with the empty ones removed
function collectErrors(checks) {
  const errors = {};
  Object.keys(checks).forEach((field) => {
    if (checks[field]) errors[field] = checks[field];
  });
  return errors;
}

// Step validators: take the form data, return an errors object ({} means valid)
function validateDriver(data, today) {
  return collectErrors({
    full_name: validateName(data.full_name),
    dob: validateDob(data.dob, today),
    email: validateEmail(data.email),
  });
}

function validateCar(data, today) {
  return collectErrors({
    car_make: validateRequiredText("Car Brand", data.car_make, QUOTE_RULES.MAX_TEXT_LENGTH),
    car_model: validateRequiredText("Model", data.car_model, QUOTE_RULES.MAX_TEXT_LENGTH),
    car_year: validateYear(data.car_year, today),
  });
}

function validateCoverage(data) {
  return collectErrors({ coverage_type: validateCoverageType(data.coverage_type) });
}

// Send only known fields; names match the future database columns
function buildPayload(data) {
  return {
    full_name: data.full_name,
    dob: data.dob,
    email: data.email,
    car_make: data.car_make,
    car_model: data.car_model,
    car_year: Number(data.car_year),
    coverage_type: data.coverage_type,
  };
}

// The server sends money as a string like "84.50"; we never parse it as a float
function isValidPrice(value) {
  return typeof value === "string" && /^\d{1,7}\.\d{2}$/.test(value);
}

// True only for a market key we have plans for ("uk" or "swiss")
function isValidMarket(value) {
  return Object.prototype.hasOwnProperty.call(MARKET_PLANS, value);
}

function getMarket(market) {
  if (!isValidMarket(market)) throw new Error(`Unknown market: ${market}`);
  return MARKET_PLANS[market];
}

// Plans for a market, keyed by server tier: { Basic: { title, text }, ... }
function plansForMarket(market) {
  return getMarket(market).plans;
}

function marketName(market) {
  return getMarket(market).name;
}

// Price text with the market's currency, e.g. "£52.00 / month" or "CHF 52.00 / month".
// The price stays a string; we only add the symbol in front of it.
function formatPrice(market, price) {
  return `${getMarket(market).currency}${price} / month`;
}

// The market's display name for a server tier; falls back to the tier itself
function coverageLabel(market, coverageType) {
  const plans = plansForMarket(market);
  if (!Object.prototype.hasOwnProperty.call(plans, coverageType)) return coverageType;
  return plans[coverageType].title;
}

// Lets the same file run in the browser (globals) and in Node (tests)
if (typeof module !== "undefined") {
  module.exports = {
    QUOTE_RULES,
    isBlank,
    calcAge,
    validateName,
    validateDob,
    validateEmail,
    validateRequiredText,
    validateYear,
    validateCoverageType,
    collectErrors,
    validateDriver,
    validateCar,
    validateCoverage,
    buildPayload,
    isValidPrice,
    MARKET_PLANS,
    isValidMarket,
    plansForMarket,
    marketName,
    formatPrice,
    coverageLabel,
  };
}
