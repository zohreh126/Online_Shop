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
    throw new Error(Array.isArray(detail) ? detail[0] : detail);
  }
  return data;
}

function showMessage(message, success = false) {
  const alert = document.querySelector("#account-alert");
  alert.hidden = false;
  alert.className = `account-alert ${success ? "success" : "error"}`;
  alert.textContent = message;
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
  try {
    const form = Object.fromEntries(new FormData(event.currentTarget));
    await request("auth/login/", "POST", form);
    window.location.href = "/checkout/";
  } catch (error) { showMessage(error.message); }
});
document.querySelector("#register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const form = Object.fromEntries(new FormData(event.currentTarget));
    await request("auth/register/", "POST", form);
    setMode(false);
    document.querySelector("#login-form [name=identifier]").value = form.username;
    showMessage("حساب ساخته شد؛ حالا وارد شو.", true);
  } catch (error) { showMessage(error.message); }
});
