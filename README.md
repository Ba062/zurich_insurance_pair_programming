# Zurich_Insurance_pair_programming

A small car insurance app built in one day by two people pair programming with Aider. A customer fills in a form and gets a monthly price. The backend also runs simple underwriting rules on every quote, saves it to a database, and suggests whether to accept it or refer it to a person.

Everything uses the Python standard library and plain HTML, CSS and JavaScript. There is nothing to install to run it.

## Run it

You need Python 3. From the main folder of the repo:

```
python backend/server.py
```

Then open http://localhost:5000 in a browser. The server serves the page and the API from that one address.

To see the saved quotes (the database entries), open http://localhost:5000/api/admin/quotes while the server is running. It lists every quote, newest first, with the suggested decision and the reasons.

The database file `backend/quotes.db` is created on first use and is not committed. If you ever change the table columns, delete that file and restart.

## Try it

Fill in the form with invented details, for example a driver born in 1996 with a 2018 Ford Fiesta and Standard cover. Leave the no claims box at 0 and the price is 52.00 a month. A driver under 21, over 75, or a car more than 20 years old is referred for review instead of accepted, and the reason is shown at the admin address.

The backend prices a no claims discount from a field called `no_claims_years`, but the form currently sends `no_claims_discount`, so the form's box does not change the price yet. The pricing tests cover the discount working.

## Run the tests

```
pip install pytest
python -m pytest backend
node --test
```

The first command runs the backend tests (pricing, validation, underwriting, database and the real server over HTTP, using a temporary database). The last runs the frontend tests and needs Node.

## How it is laid out

* `backend/server.py` serves the files in `frontend/`, takes `POST /api/quote` and answers `GET /api/admin/quotes`
* `backend/validate.py` checks the input, mirroring `frontend/validate.js`
* `backend/pricing.py` works out the monthly price
* `backend/underwriting.py` decides accept or refer and gives the reasons
* `backend/db.py` stores quotes in SQLite
* `frontend/` is the quote form
* `SPEC.md` says what we set out to build and `CONVENTIONS.md` is the coding rules we gave Aider

## Rules in one place

Pricing starts from a base price, then applies the coverage factor (Basic 1.0, Standard 1.3, Premium 1.6), the age factor (under 25 is 1.4, 70 or over is 1.2), a no claims discount of 5 percent per year capped at 50 percent, a surcharge for cars over 15 years old, and a minimum premium. Money uses Decimal and is rounded once at the end. `SPEC.md` has the exact order.

Underwriting refers a quote when the driver is under 21 or over 75, or the car is more than 20 years old. Otherwise it accepts. Every rule that triggers adds one plain sentence to the reasons.

## What is not finished

* There is no workbench page or navbar yet. The saved quotes are visible through the admin address above, not a screen.
* The admin address has no login. It is for local use with invented data only.
* The form's no claims field and the backend's no claims years need to use the same name and meaning.
* The prices and thresholds are placeholders agreed for the day, not real Zurich figures.

## How we worked

One person on the backend, database and tests, one on the form. Each of us used our own branch, merged `main` into it before a pull request, and kept `main` passing the tests. Aider made small commits as it went, and the chat history in `.aider.chat.history.md` is the record of the prompts.

All customer data is invented demo data. No keys or secrets are stored in the repo.
