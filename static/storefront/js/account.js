const API_BASE = "/api/v1/";
const tr = (key) => window.NexoraI18n?.t(key) || key;
let registerMode = false;
let loginOTPEmail = "";

function setupTheme() {
  const root = document.documentElement;
  const button = document.querySelector("#theme-toggle");
  if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark");
  const update = () => {
    if (button) button.textContent = root.classList.contains("dark") ? "☼" : "☾";
  };
  button?.addEventListener("click", () => {
    root.classList.toggle("dark");
    localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light");
    update();
  });
  update();
}

function getCookie(name) {
  const cookie = (document.cookie ? document.cookie.split("; ") : [])
    .find((value) => value.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null;
}

async function csrf() {
  let token = getCookie("csrftoken");
  if (token) return token;
  const response = await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" });
  if (!response.ok) throw new Error(tr("securityTokenFailed"));
  token = getCookie("csrftoken");
  if (!token) throw new Error(tr("securityTokenFailed"));
  return token;
}

async function request(path, method, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": await csrf(),
    },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const codeMessage = data.error_code === "email_delivery_failed"
      ? tr("emailDeliveryFailed")
      : "";
    const messages = Object.entries(data).flatMap(([field, value]) => (
      Array.isArray(value) ? value : [value]
    ).map((item) => `${field}: ${item}`));
    throw Object.assign(
      new Error(codeMessage || messages.join(" | ") || data.detail || tr("operationFailed")),
      { data, status: response.status },
    );
  }
  return data;
}

function showMessage(message, success = false) {
  const alert = document.querySelector("#account-alert");
  alert.hidden = false;
  alert.className = `account-alert ${success ? "success" : "error"}`;
  alert.textContent = message;
}

function clearFieldErrors(form) {
  form.querySelectorAll(".field-error").forEach((element) => element.remove());
  form.querySelectorAll("[aria-invalid=true]").forEach((element) => element.removeAttribute("aria-invalid"));
}

function showFieldErrors(form, data) {
  clearFieldErrors(form);
  let displayed = false;
  Object.entries(data || {}).forEach(([field, messages]) => {
    const input = form.querySelector(`[name="${field}"]`);
    if (!input) return;
    const error = document.createElement("small");
    error.className = "field-error";
    error.textContent = Array.isArray(messages) ? messages[0] : messages;
    input.setAttribute("aria-invalid", "true");
    input.insertAdjacentElement("afterend", error);
    displayed = true;
  });
  return displayed;
}

function roleDestination(user) {
  const next = new URLSearchParams(window.location.search).get("next");
  if (next && next.startsWith("/")) return next;
  if (user.is_staff || user.is_superuser) return "/admin/";
  return "/profile/";
}

function finishLogin(response) {
  window.dispatchEvent(new CustomEvent("nexora-logged-in", { detail: { user: response.user } }));
  window.location.href = roleDestination(response.user);
}

function setMode(nextRegisterMode) {
  registerMode = nextRegisterMode;
  document.querySelector("#login-form").hidden = registerMode;
  document.querySelector("#login-otp-form").hidden = true;
  document.querySelector("#register-form").hidden = !registerMode;
  document.querySelector("#account-title").textContent = tr(registerMode ? "registerTitle" : "loginTitle");
  document.querySelector("#account-subtitle").textContent = tr(registerMode ? "registerSubtitle" : "loginStepSubtitle");
  document.querySelector("#account-switch").textContent = tr(registerMode ? "hasAccount" : "noAccount");
  document.querySelector("#account-alert").hidden = true;
  if (!registerMode) document.querySelector("#login-form [name=password]").value = "";
}

function showOTPForm(email) {
  loginOTPEmail = email;
  const loginForm = document.querySelector("#login-form");
  loginForm.hidden = true;
  loginForm.querySelector("[name=password]").value = "";
  document.querySelector("#login-otp-form").hidden = false;
  document.querySelector("#login-otp-email").textContent = email;
  document.querySelector("#account-title").textContent = tr("otpTitle");
  document.querySelector("#account-subtitle").textContent = tr("otpSubtitle");
  document.querySelector("#login-otp-form [name=code]").focus();
}

document.querySelector("#account-switch").addEventListener("click", () => setMode(!registerMode));
document.querySelector("#login-otp-back").addEventListener("click", () => setMode(false));

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget;
  clearFieldErrors(formElement);
  try {
    const form = Object.fromEntries(new FormData(formElement));
    const response = await request("auth/login/", "POST", form);
    finishLogin(response);
  } catch (error) {
    if (!showFieldErrors(formElement, error.data)) showMessage(error.message);
  }
});

document.querySelector("#request-login-otp").addEventListener("click", async () => {
  const formElement = document.querySelector("#login-form");
  clearFieldErrors(formElement);
  const email = String(new FormData(formElement).get("identifier") || "").trim();
  if (!email || !email.includes("@")) {
    showFieldErrors(formElement, { identifier: tr("otpEmailOnly") });
    return;
  }
  const button = document.querySelector("#request-login-otp");
  button.disabled = true;
  try {
    const response = await request("auth/login/otp/request/", "POST", { email });
    showOTPForm(response.email);
    showMessage(tr("otpSent"), true);
  } catch (error) {
    if (!showFieldErrors(formElement, error.data)) showMessage(error.message);
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#login-otp-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget;
  clearFieldErrors(formElement);
  try {
    const form = Object.fromEntries(new FormData(formElement));
    const response = await request("auth/login/otp/verify/", "POST", {
      email: loginOTPEmail,
      code: form.code,
    });
    finishLogin(response);
  } catch (error) {
    if (!showFieldErrors(formElement, error.data)) showMessage(error.message);
  }
});

document.querySelector("#register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget;
  clearFieldErrors(formElement);
  try {
    const form = Object.fromEntries(new FormData(formElement));
    await request("auth/register/", "POST", form);
    const loginForm = document.querySelector("#login-form");
    setMode(false);
    loginForm.reset();
    loginForm.querySelector("[name=identifier]").value = form.username;
    loginForm.querySelector("[name=password]").focus();
    showMessage(tr("accountCreated"), true);
  } catch (error) {
    if (!showFieldErrors(formElement, error.data)) showMessage(error.message);
  }
});

setupTheme();
