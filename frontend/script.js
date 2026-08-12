
const API_BASE_URL = "https://voicekhata-backend.onrender.com/api";

const state = {
  customers: [],
  selectedCustomer: null,
  recognition: null,
  profile: null
};

const $ = (selector) => document.querySelector(selector);

const money = (value) =>
  `₹${Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  })}`;

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      data.detail || "The server could not complete that request."
    );
  }

  return response.json();
}

function show(screen) {
  document.querySelectorAll(".screen").forEach((item) => {
    item.classList.remove("active");
  });

  const target = document.getElementById(screen);

  if (target) {
    target.classList.add("active");
  }

  if (screen === "dashboard") {
    refreshDashboard();
  }

  if (screen === "customers") {
    loadCustomers();
  }

  if (screen === "reports") {
    loadReports();
  }

  if (screen === "profile") {
    loadProfile();
  }

  window.scrollTo(0, 0);
}

function toast(message) {
  const el = $("#toast");

  if (!el) return;

  el.textContent = message;
  el.className = "visible";

  setTimeout(() => {
    el.className = "";
  }, 3200);
}

function transactionRow(tx, clickable = false) {
  const positive = tx.transaction_type === "payment";

  return `
    <button
      class="list-item"
      ${clickable ? `data-customer-id="${tx.customer_id}"` : "type=\"button\""}
    >
      <span class="initial">
        ${(tx.customer_name || tx.item || "T")[0]}
      </span>

      <span class="item-copy">
        <b>${tx.customer_name || tx.item || "Transaction"}</b>
        <small>
          ${tx.item || "Transaction"} ·
          ${new Date(tx.created_at).toLocaleDateString("en-IN", {
            day: "numeric",
            month: "short"
          })}
        </small>
      </span>

      <b class="amount ${tx.transaction_type}">
        ${positive ? "+" : ""}${money(tx.amount)}
      </b>
    </button>
  `;
}

async function refreshDashboard() {
  const status = $("#api-status");

  if (status) {
    status.textContent = "Loading your khata…";
  }

  try {
    const report = await api("/reports/summary");

    if ($("#today-sales")) {
      $("#today-sales").textContent = money(report.today_sales);
    }

    if ($("#outstanding")) {
      $("#outstanding").textContent = money(report.outstanding_credit);
    }

    if ($("#customer-count")) {
      $("#customer-count").textContent = report.total_customers;
    }

    if ($("#recent-transactions")) {
      $("#recent-transactions").innerHTML =
        report.recent_transactions &&
        report.recent_transactions.length
          ? report.recent_transactions
              .map((t) => transactionRow(t, true))
              .join("")
          : `<p class="muted">No transactions yet.</p>`;
    }

    if (status) {
      status.textContent =
        "Your data is synced with the local database.";
    }
  } catch (error) {
    if (status) {
      status.textContent =
        `Backend unavailable: ${error.message}`;
    }

    if ($("#recent-transactions")) {
      $("#recent-transactions").innerHTML =
        `<p class="error">Start FastAPI, then refresh this page.</p>`;
    }
  }
}

async function loadCustomers() {
  const list = $("#customer-list");

  if (!list) return;

  list.innerHTML =
    `<p class="muted">Loading customers…</p>`;

  try {
    state.customers = await api("/customers");

    list.innerHTML = state.customers.length
      ? state.customers
          .map(
            (customer) => `
              <button
                type="button"
                class="list-item"
                data-customer-id="${customer.id}"
              >
                <span class="initial">
                  ${customer.name[0]}
                </span>

                <span class="item-copy">
                  <b>${customer.name}</b>
                  <small>${customer.phone}</small>
                </span>

                <b>
                  ${money(customer.outstanding_balance)}
                </b>
              </button>
            `
          )
          .join("")
      : `<p class="muted">No customers found.</p>`;
  } catch (error) {
    list.innerHTML =
      `<p class="error">${error.message}</p>`;
  }
}

async function openCustomer(id) {
  try {
    const [customer, transactions] =
      await Promise.all([
        api(`/customers/${id}`),
        api(`/customers/${id}/transactions`)
      ]);

    state.selectedCustomer = customer;

    if ($("#customer-detail")) {
      $("#customer-detail").innerHTML = `
        <div class="form-card">
          <div class="initial">
            ${customer.name[0]}
          </div>

          <h2>${customer.name}</h2>

          <p class="muted">
            ${customer.phone}
          </p>

          <small>
            Outstanding balance
          </small>

          <h2>
            ${money(customer.outstanding_balance)}
          </h2>

          <button
            type="button"
            class="primary"
            data-go="voice-transaction"
          >
            Add transaction
          </button>
        </div>
      `;
    }

    if ($("#customer-history")) {
      $("#customer-history").innerHTML =
        transactions.length
          ? transactions
              .map((t) => transactionRow(t))
              .join("")
          : `<p class="muted">No transactions yet.</p>`;
    }

    show("customer-details");
  } catch (error) {
    toast(error.message);
  }
}

async function loadReports() {
  try {
    const report =
      await api("/reports/summary");

    if ($("#report-daily")) {
      $("#report-daily").textContent =
        money(report.today_sales);
    }

    if ($("#report-weekly")) {
      $("#report-weekly").textContent =
        money(report.weekly_sales);
    }

    if ($("#report-payments")) {
      $("#report-payments").textContent =
        money(report.total_payments);
    }

    if ($("#sales-chart")) {
      const values = report.daily_sales || [];
      const max = Math.max(...values, 1);

      $("#sales-chart").innerHTML =
        values
          .map(
            (value, index) => `
              <div
                class="bar"
                style="height:${Math.max(
                  4,
                  (value / max) * 150
                )}px"
              >
                <span>${index + 1}d</span>
              </div>
            `
          )
          .join("");
    }
  } catch (error) {
    toast(error.message);
  }
}

function normalizeName(name) {
  return String(name || "")
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[“”"'.,!?]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function namesMatch(a, b) {
  const first = normalizeName(a);
  const second = normalizeName(b);

  if (!first || !second) {
    return false;
  }

  if (first === second) {
    return true;
  }

  const firstWords = first.split(" ");
  const secondWords = second.split(" ");

  if (
    firstWords.length === 1 &&
    secondWords.includes(first)
  ) {
    return true;
  }

  if (
    secondWords.length === 1 &&
    firstWords.includes(second)
  ) {
    return true;
  }

  return false;
}

async function fillCustomerSelect(extractedName = "") {
  state.customers = await api("/customers");

  const select = $("#confirm-customer");

  if (!select) return null;

  select.innerHTML = "";

  const placeholder =
    document.createElement("option");

  placeholder.value = "";
  placeholder.textContent =
    "Select an existing customer";

  select.appendChild(placeholder);

  let matchedCustomer = null;

  state.customers.forEach((customer) => {
    const option =
      document.createElement("option");

    option.value = customer.id;

    option.textContent =
      `${customer.name} · ${money(
        customer.outstanding_balance
      )}`;

    if (
      extractedName &&
      namesMatch(
        customer.name,
        extractedName
      )
    ) {
      matchedCustomer = customer;
      option.selected = true;
    }

    select.appendChild(option);
  });

  return matchedCustomer;
}

function openNewCustomer(name = "") {
  const fields =
    $("#new-customer-fields");

  const nameInput =
    $("#new-customer-name");

  const phoneInput =
    $("#new-customer-phone");

  const select =
    $("#confirm-customer");

  if (!fields || !nameInput || !phoneInput) {
    return;
  }

  fields.hidden = false;

  if (select) {
    select.value = "";
  }

  nameInput.value = name || "";
  phoneInput.value = "";

  if (name) {
    setTimeout(() => {
      nameInput.focus();
    }, 100);
  }
}

function closeNewCustomer() {
  const fields =
    $("#new-customer-fields");

  const nameInput =
    $("#new-customer-name");

  const phoneInput =
    $("#new-customer-phone");

  if (fields) {
    fields.hidden = true;
  }

  if (nameInput) {
    nameInput.value = "";
  }

  if (phoneInput) {
    phoneInput.value = "";
  }
}

async function extractText(text) {
  const cleanText =
    String(text || "").trim();

  if ($("#voice-error")) {
    $("#voice-error").textContent = "";
  }

  if (!cleanText) {
    if ($("#voice-error")) {
      $("#voice-error").textContent =
        "Speak or type a transaction first.";
    }

    return;
  }

  show("processing");

  try {
    const result = await api(
      "/voice/extract",
      {
        method: "POST",
        body: JSON.stringify({
          transcription: cleanText
        })
      }
    );

    const matchedCustomer =
      await fillCustomerSelect(
        result.customer_name
      );

    if (matchedCustomer) {
      closeNewCustomer();
    } else {
      openNewCustomer(
        result.customer_name || ""
      );
    }

    if ($("#confirm-amount")) {
      $("#confirm-amount").value =
        result.amount || "";
    }

    if ($("#confirm-item")) {
      $("#confirm-item").value =
        result.item || "Goods";
    }

    if ($("#confirm-type")) {
      $("#confirm-type").value =
        result.transaction_type || "credit";
    }

    if ($("#extraction-note")) {
      $("#extraction-note").textContent =
        result.explanation ||
        `Heard: "${cleanText}"`;
    }

    show("confirmation");
  } catch (error) {
    show("voice-transaction");

    if ($("#voice-error")) {
      $("#voice-error").textContent =
        error.message;
    }
  }
}

function startRecognition(target, callback) {
  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    if (target) {
      target.textContent =
        "Speech recognition is not supported. Use Chrome or Edge.";
    }

    return;
  }

  if (state.recognition) {
    state.recognition.stop();
    return;
  }

  const recognition =
    new SpeechRecognition();

  state.recognition = recognition;

  recognition.lang = "hi-IN";
  recognition.interimResults = true;
  recognition.continuous = false;

  let spoken = "";

  recognition.onstart = () => {
    const recordButton =
      $("#record-button");

    if (recordButton) {
      recordButton.classList.add(
        "recording"
      );
    }

    if (target) {
      target.textContent =
        "Listening…";
    }
  };

  recognition.onresult = (event) => {
    spoken = Array.from(event.results)
      .map(
        (result) =>
          result[0].transcript
      )
      .join(" ");

    if ($("#manual-transcription")) {
      $("#manual-transcription").value =
        spoken;
    }

    if (target) {
      target.textContent =
        "Heard: " + spoken;
    }
  };

  recognition.onerror = (event) => {
    if (target) {
      target.textContent =
        `Microphone error: ${event.error}`;
    }
  };

  recognition.onend = () => {
    state.recognition = null;

    const recordButton =
      $("#record-button");

    if (recordButton) {
      recordButton.classList.remove(
        "recording"
      );
    }

    if (spoken.trim() && callback) {
      callback(spoken.trim());
    }
  };

  recognition.start();
}

async function saveTransaction(event) {
  event.preventDefault();

  if ($("#save-error")) {
    $("#save-error").textContent = "";
  }

  try {
    let customerId = Number(
      $("#confirm-customer")?.value || 0
    );

    const newCustomerFields =
      $("#new-customer-fields");

    const creatingNewCustomer =
      newCustomerFields &&
      !newCustomerFields.hidden;

    if (creatingNewCustomer) {
      const name =
        $("#new-customer-name")?.value.trim();

      const phone =
        $("#new-customer-phone")?.value.trim();

      if (!name) {
        throw new Error(
          "Please enter the customer's name."
        );
      }

      if (!/^\d{10}$/.test(phone)) {
        throw new Error(
          "Please enter a valid 10-digit phone number."
        );
      }

      const duplicate = state.customers.find((customer) =>
        customer.phone === phone
      );

      if (duplicate) {
        customerId = duplicate.id;
      } else {
        const newCustomer = await api("/customers", {
          method: "POST",
          body: JSON.stringify({ name, phone })
        });
        customerId = newCustomer.id;
      }
    }

    if (!customerId) {
      throw new Error(
        "Please select an existing customer or add a new customer."
      );
    }

    const amount =
      Number($("#confirm-amount")?.value || 0);

    if (!amount || amount <= 0) {
      throw new Error(
        "Please enter a valid amount."
      );
    }

    await api(
      "/transactions",
      {
        method: "POST",
        body: JSON.stringify({
          customer_id: customerId,
          amount,
          item:
            $("#confirm-item")?.value ||
            "Goods",
          transaction_type:
            $("#confirm-type")?.value ||
            "credit",
          description:
            $("#confirm-description")?.value ||
            null
        })
      }
    );

    toast(
      "Transaction saved successfully."
    );

    if ($("#confirm-customer")) {
      $("#confirm-customer").value = "";
    }

    if ($("#confirm-amount")) {
      $("#confirm-amount").value = "";
    }

    if ($("#confirm-item")) {
      $("#confirm-item").value = "";
    }

    if ($("#confirm-description")) {
      $("#confirm-description").value = "";
    }

    closeNewCustomer();

    show("dashboard");
  } catch (error) {
    if ($("#save-error")) {
      $("#save-error").textContent =
        error.message;
    }
  }
}

function loadProfile() {
  const profile = state.profile || {
    name: "Harshika", store: "Harshika's Store", phone: ""
  };
  if ($("#profile-name")) $("#profile-name").value = profile.name;
  if ($("#profile-store-name")) $("#profile-store-name").value = profile.store;
  if ($("#profile-phone")) $("#profile-phone").value = profile.phone;
}

function saveProfile(event) {
  event.preventDefault();
  const name = $("#profile-name")?.value.trim();
  const store = $("#profile-store-name")?.value.trim();
  const phone = $("#profile-phone")?.value.trim();
  if (!name || !store || !/^\d{10}$/.test(phone || "")) {
    $("#profile-error").textContent = "Enter your name, store name, and a valid 10-digit phone number.";
    return;
  }
  state.profile = { name, store, phone };
  $("#profile-error").textContent = "";
  if ($("#profile-store-heading")) $("#profile-store-heading").textContent = store;
  if ($("#dashboard-avatar")) $("#dashboard-avatar").textContent = name[0].toUpperCase();
  if ($("#profile-avatar")) $("#profile-avatar").textContent = name[0].toUpperCase();
  toast("Profile saved.");
}

async function ask(question) {
  const cleanQuestion =
    String(question || "").trim();

  if (!cleanQuestion) {
    if ($("#assistant-error")) {
      $("#assistant-error").textContent =
        "Please ask a question.";
    }

    return;
  }

  if ($("#assistant-error")) {
    $("#assistant-error").textContent = "";
  }

  try {
    const data = await api(
      "/voice/query",
      {
        method: "POST",
        body: JSON.stringify({
          question: cleanQuestion
        })
      }
    );

    if ($("#assistant-answer")) {
      $("#assistant-answer").hidden = false;
      $("#assistant-answer").textContent =
        data.answer;
    }
  } catch (error) {
    if ($("#assistant-error")) {
      $("#assistant-error").textContent =
        error.message;
    }
  }
}

document.addEventListener(
  "click",
  (event) => {
    const navigation =
      event.target.closest("[data-go]");

    if (navigation) {
      event.preventDefault();
      show(navigation.dataset.go);
      return;
    }

    const customer =
      event.target.closest(
        "[data-customer-id]"
      );

    if (customer) {
      event.preventDefault();
      openCustomer(
        customer.dataset.customerId
      );
    }
  }
);

document.addEventListener(
  "change",
  (event) => {
    if (
      event.target.id ===
      "confirm-customer"
    ) {
      if (event.target.value) {
        closeNewCustomer();
      }
    }
  }
);

document.addEventListener(
  "click",
  (event) => {
    if (
      event.target.id ===
      "record-button"
    ) {
      startRecognition(
        $("#recording-status"),
        extractText
      );
    }

    if (
      event.target.id ===
      "extract-button"
    ) {
      extractText(
        $("#manual-transcription")?.value
      );
    }

    if (
      event.target.id ===
      "add-customer-toggle"
    ) {
      const fields =
        $("#new-customer-fields");

      if (fields) {
        fields.hidden =
          !fields.hidden;

        if (!fields.hidden) {
          $("#confirm-customer").value = "";
          $("#new-customer-name").focus();
        }
      }
    }

    if (
      event.target.id ===
      "ask-button"
    ) {
      ask(
        $("#assistant-question")?.value
      );
    }

    if (
      event.target.id ===
      "assistant-record"
    ) {
      startRecognition(
        $("#assistant-error"),
        (spoken) => {
          if ($("#assistant-question")) {
            $("#assistant-question").value =
              spoken;
          }

          ask(spoken);
        }
      );
    }
  }
);

document.addEventListener(
  "keydown",
  (event) => {
    if (
      event.target.id ===
        "assistant-question" &&
      event.key === "Enter"
    ) {
      event.preventDefault();

      ask(event.target.value);
    }
  }
);

const confirmationForm =
  $("#confirmation-form");

if (confirmationForm) {
  confirmationForm.addEventListener(
    "submit",
    saveTransaction
  );
}

const loginForm = $("#login-form");
if (loginForm) {
  loginForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const phone = $("#login-phone")?.value.trim() || "";
    if (!/^\d{10}$/.test(phone)) {
      $("#login-error").textContent = "Please enter a valid 10-digit mobile number.";
      return;
    }
    $("#login-error").textContent = "";
    show("dashboard");
  });
}

const profileForm = $("#profile-form");
if (profileForm) profileForm.addEventListener("submit", saveProfile);

show("splash");
