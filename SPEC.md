# SPEC: Car insurance quote and underwriting workbench

## Purpose
A customer gets a monthly car insurance quote. An underwriter reviews the saved quotes on a workbench page and sees a suggested decision with reasons.

## Data (one quote)
id, full_name, dob, email, car_make, car_model, car_year, coverage_type (Basic, Standard or Premium), no_claims_years (optional, default 0), vehicle_value (optional), monthly_price, suggested_decision (accept or refer), reasons (list of sentences), status (pending, approved, declined or referred), underwriter_note, created_at

## Database
SQLite table quotes with the columns above, created in backend/db.py. The database file is not committed.

## Backend
- POST /api/quote: validates, prices, assesses risk, saves, and returns {"monthly_price": "84.50", "breakdown": [{"label": "...", "amount": "..."}]}. Returns 400 with an errors object for bad input
- GET /api/admin/quotes: every saved quote, newest first, with all columns. reasons is a list
- The server also serves the files in the frontend folder, so the page and the API share one address (http://localhost:5000)

## UI
- Navbar on every page: Get a quote, Workbench
- index.html: three step quote form and a result page showing the price and the breakdown
- workbench.html: a table of saved quotes with suggested decision, reasons and status. Every value is shown with textContent so nothing typed by a user runs as HTML

## Rules
Pricing, in this order, in Decimal, rounded half up to 2 places once at the end:
1. Base monthly price: 3 percent of vehicle_value divided by 12 when vehicle_value is given, otherwise a flat 40.00
2. Coverage factor: Basic 1.0, Standard 1.3, Premium 1.6
3. Age factor from date of birth: under 25 is 1.4, 25 to 69 is 1.0, 70 or over is 1.2
4. No claims discount: 5 percent per year, capped at 50 percent
5. Add 5.00 if the car is more than 15 years old
6. Minimum monthly premium of 20.00, applied last

Underwriting (backend/underwriting.py): refer if the driver is under 21, over 75, or the car is more than 20 years old. Otherwise accept. Each rule that triggers adds one reason sentence.

## Edge cases
Empty or wrong input returns 400 and never crashes. Invalid JSON returns 400. Unknown paths return 404. Wrong methods return 405. Optional fields left blank behave as if they were not sent. no_claims_years must be a whole number from 0 to 50. vehicle_value must be a real number from 500 to 200000 with at most 2 decimals, never NaN or infinity.

## Constraints
Python standard library only, plain HTML, CSS and JavaScript, few files, invented demo data only.

## Who owns what
Jethro: backend, database, tests. Partner: frontend, navbar and workbench page.

## Done means
1. A customer submits the form and sees a price with a breakdown
2. The quote appears on the workbench with a suggested decision and reasons
3. The no claims discount changes the price as the rules say
4. All tests pass: python -m pytest backend and node --test frontend
