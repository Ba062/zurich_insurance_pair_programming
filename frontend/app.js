// In Node (tests) load the validators; in the browser they are globals from validate.js
const quoteChecks = typeof require !== "undefined" ? require("./validate.js") : globalThis;

// Show one screen and hide the rest
function showStep(sections, name) {
  sections.forEach((section) => {
    section.hidden = section.dataset.step !== name;
  });
}

// Write each field's error text; fields without an error are cleared
function showErrors(errorEls, errors) {
  errorEls.forEach((el) => {
    el.textContent = errors[el.dataset.field] || "";
  });
}

// Collect trimmed values by input name; unchecked radios are skipped
function readFields(inputs) {
  const data = {};
  inputs.forEach((input) => {
    if (input.type === "radio" && !input.checked) return;
    data[input.name] = input.value.trim();
  });
  return data;
}

// Clear every input and error message
function resetFields(inputs, errorEls) {
  inputs.forEach((input) => {
    if (input.type === "radio") {
      input.checked = false;
    } else {
      input.value = "";
    }
  });
  showErrors(errorEls, {});
}

// Ask the server for a price. Throws on any failure so the caller shows one message.
async function submitQuote(payload, fetchFn) {
  const response = await fetchFn("/api/quote", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Quote request failed");

  const body = await response.json();
  if (!quoteChecks.isValidPrice(body.monthly_price)) throw new Error("Invalid price");
  return body.monthly_price;
}

// Fill each plan card with the title and text for the chosen market's plans
function renderPlans(titleEls, textEls, plans) {
  titleEls.forEach((el) => {
    el.textContent = plans[el.dataset.planTitle].title;
  });
  textEls.forEach((el) => {
    el.textContent = plans[el.dataset.planText].text;
  });
}

// textContent (never innerHTML) so user input cannot inject HTML
function renderQuote(els, data, price, market) {
  els.price.textContent = quoteChecks.formatPrice(market, price);
  els.market.textContent = quoteChecks.marketName(market);
  els.name.textContent = data.full_name;
  els.email.textContent = data.email;
  els.car.textContent = `${data.car_make} ${data.car_model}, ${data.car_year}`;
  els.coverage.textContent = quoteChecks.coverageLabel(market, data.coverage_type);
}

// Wire the page together (browser only)
function init() {
  const sections = Array.from(document.querySelectorAll("[data-step]"));
  const inputs = Array.from(document.querySelectorAll("input"));
  const errorEls = Array.from(document.querySelectorAll("[data-field]"));
  const serverError = document.getElementById("server-error");
  const submitBtn = document.getElementById("submit-btn");
  const planTitleEls = Array.from(document.querySelectorAll("[data-plan-title]"));
  const planTextEls = Array.from(document.querySelectorAll("[data-plan-text]"));
  let market = null; // "uk" or "swiss", chosen on the landing screen
  const resultEls = {
    price: document.getElementById("result-price"),
    market: document.getElementById("result-market"),
    name: document.getElementById("result-name"),
    email: document.getElementById("result-email"),
    car: document.getElementById("result-car"),
    coverage: document.getElementById("result-coverage"),
  };
  const stepValidators = {
    driver: quoteChecks.validateDriver,
    car: quoteChecks.validateCar,
    coverage: quoteChecks.validateCoverage,
  };

  // Validate the current step (if asked) before moving on
  function handleGo(button) {
    const step = button.dataset.check;
    if (step) {
      const errors = stepValidators[step](readFields(inputs), new Date());
      showErrors(errorEls, errors);
      if (Object.keys(errors).length > 0) return;
    }
    if (button.dataset.market) {
      market = button.dataset.market;
      renderPlans(planTitleEls, planTextEls, quoteChecks.plansForMarket(market));
    }
    showStep(sections, button.dataset.go);
  }

  async function handleSubmit() {
    const data = readFields(inputs);
    const errors = quoteChecks.validateCoverage(data);
    showErrors(errorEls, errors);
    if (Object.keys(errors).length > 0) return;

    serverError.hidden = true;
    submitBtn.disabled = true; // stops double submits
    try {
      const price = await submitQuote(quoteChecks.buildPayload(data), fetch);
      renderQuote(resultEls, data, price, market);
      showStep(sections, "result");
    } catch (err) {
      console.error(err);
      serverError.hidden = false;
    } finally {
      submitBtn.disabled = false;
    }
  }

  document.querySelectorAll("button[data-go]").forEach((button) => {
    button.addEventListener("click", () => handleGo(button));
  });
  submitBtn.addEventListener("click", handleSubmit);
  document.getElementById("restart-btn").addEventListener("click", () => {
    resetFields(inputs, errorEls);
    market = null;
    showStep(sections, "landing");
  });

  showStep(sections, "landing");
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", init);
}

if (typeof module !== "undefined") {
  module.exports = {
    showStep,
    showErrors,
    readFields,
    resetFields,
    submitQuote,
    renderPlans,
    renderQuote,
  };
}
