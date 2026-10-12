const test = require("node:test");
const assert = require("node:assert");
const app = require("./app.js");
const checks = require("./validate.js");

// init() only wires events in the browser, so it is checked by hand.

test("showStep shows only the named screen", () => {
  const sections = [
    { dataset: { step: "a" }, hidden: true },
    { dataset: { step: "b" }, hidden: false },
  ];
  app.showStep(sections, "a");
  assert.strictEqual(sections[0].hidden, false);
  assert.strictEqual(sections[1].hidden, true);
});

test("showErrors writes messages and clears the rest", () => {
  const errorEls = [
    { dataset: { field: "email" }, textContent: "old" },
    { dataset: { field: "dob" }, textContent: "old" },
  ];
  app.showErrors(errorEls, { email: "Bad email" });
  assert.strictEqual(errorEls[0].textContent, "Bad email");
  assert.strictEqual(errorEls[1].textContent, "");
});

test("readFields trims values and skips unchecked radios", () => {
  const inputs = [
    { name: "full_name", type: "text", value: "  Jane  " },
    { name: "coverage_type", type: "radio", checked: false, value: "Basic" },
    { name: "coverage_type", type: "radio", checked: true, value: "Premium" },
  ];
  assert.deepStrictEqual(app.readFields(inputs), {
    full_name: "Jane",
    coverage_type: "Premium",
  });
});

test("resetFields clears inputs and errors", () => {
  const inputs = [
    { name: "email", type: "text", value: "a@b.com" },
    { name: "coverage_type", type: "radio", checked: true, value: "Basic" },
  ];
  const errorEls = [{ dataset: { field: "email" }, textContent: "Bad" }];
  app.resetFields(inputs, errorEls);
  assert.strictEqual(inputs[0].value, "");
  assert.strictEqual(inputs[1].checked, false);
  assert.strictEqual(errorEls[0].textContent, "");
});

test("submitQuote returns the price string on success", async () => {
  let call;
  const fakeFetch = async (url, options) => {
    call = { url, options };
    return { ok: true, json: async () => ({ monthly_price: "84.50" }) };
  };
  const price = await app.submitQuote({ full_name: "Jane" }, fakeFetch);
  assert.strictEqual(price, "84.50");
  assert.strictEqual(call.url, "/api/quote");
  assert.strictEqual(call.options.method, "POST");
});

test("submitQuote rejects on a server error", async () => {
  const fakeFetch = async () => ({ ok: false });
  await assert.rejects(app.submitQuote({}, fakeFetch));
});

test("submitQuote rejects on an invalid price", async () => {
  const fakeFetch = async () => ({ ok: true, json: async () => ({ monthly_price: 84.5 }) });
  await assert.rejects(app.submitQuote({}, fakeFetch));
});

test("renderQuote fills the summary with plain text", () => {
  const els = {
    price: {},
    market: {},
    name: {},
    email: {},
    car: {},
    coverage: {},
  };
  app.renderQuote(
    els,
    {
      full_name: "<b>Jane</b>",
      email: "jane@example.com",
      car_make: "Toyota",
      car_model: "Corolla",
      car_year: "2019",
      coverage_type: "Standard",
    },
    "84.50",
    "uk"
  );
  assert.strictEqual(els.price.textContent, "£84.50 / month");
  assert.strictEqual(els.name.textContent, "<b>Jane</b>"); // kept as text, not HTML
  assert.strictEqual(els.car.textContent, "Toyota Corolla, 2019");
  assert.strictEqual(els.coverage.textContent, "Third party, fire & theft");
  assert.strictEqual(els.market.textContent, "United Kingdom");
});

test("renderPlans fills titles and texts for the chosen market", () => {
  const titleEls = [
    { dataset: { planTitle: "Basic" }, textContent: "" },
    { dataset: { planTitle: "Premium" }, textContent: "" },
  ];
  const textEls = [{ dataset: { planText: "Standard" }, textContent: "" }];
  app.renderPlans(titleEls, textEls, checks.plansForMarket("swiss"));
  assert.strictEqual(titleEls[0].textContent, "Liability");
  assert.strictEqual(titleEls[1].textContent, "Full casco");
  assert.strictEqual(textEls[0].textContent, "Adds theft, fire and natural events.");
});
