const API_BASE = "/api/v1/";
let registerMode = false;

function getCookie(name) {
  const cookie = (document.cookie ? document.cookie.split("; ") : []).find((value) => value.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null;
}

async function csrf() {
  let token = getCookie("csrftoken");
  if (token) return token;
  const response = await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" });
  if (!response.ok) throw new Error("توکن امنیتی دریافت نشد.");
  token = getCookie("csrftoken");
  if (!token) throw new Error("توکن امنیتی دریافت نشد.");
  return token;
}

async function request(path, method, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": await csrf() },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail || Object.values(data).flat()?.[0] || "عملیات انجام نشد.";
    if (String(detail).toLowerCase().includes("no active account")) {
      throw Object.assign(new Error("نام کاربری/ایمیل یا رمز عبور صحیح نیست."), { data });
    }
    throw Object.assign(new Error(Array.isArray(detail) ? detail[0] : detail), { data });
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

function setMode(nextRegisterMode) {
  registerMode = nextRegisterMode;
  document.querySelector("#login-form").hidden = registerMode;
  document.querySelector("#register-form").hidden = !registerMode;
  document.querySelector("#account-title").textContent = registerMode ? "ساخت حساب" : "ورود به حساب";
  document.querySelector("#account-subtitle").textContent = registerMode ? "برای ثبت سفارش یک حساب رایگان بساز." : "برای ادامه‌ی خرید وارد حساب کاربری‌ات شو.";
  document.querySelector("#account-switch").textContent = registerMode ? "حساب دارم؛ وارد می‌شوم" : "حساب ندارم؛ ثبت‌نام می‌کنم";
  document.querySelector("#account-alert").hidden = true;
}

document.querySelector("#account-switch").addEventListener("click", () => setMode(!registerMode));
document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget;
  clearFieldErrors(formElement);
  try {
    const form = Object.fromEntries(new FormData(formElement));
    await request("auth/login/", "POST", form);
    window.location.href = "/checkout/";
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
    setMode(false);
    document.querySelector("#login-form [name=identifier]").value = form.username;
    showMessage("حساب ساخته شد؛ حالا وارد شو.", true);
  } catch (error) {
    if (!showFieldErrors(formElement, error.data)) showMessage(error.message);
  }
});
