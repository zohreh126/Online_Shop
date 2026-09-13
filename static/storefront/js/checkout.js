const API_BASE = "/api/v1/";
const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const money = (value) => `${faNumber(Math.round(Number(value)))} تومان`;
const state = { cart: null, addresses: [], selectedAddress: null, order: null };
const latinizeDigits = (value) => String(value).replace(/[۰-۹]/g, (digit) => "۰۱۲۳۴۵۶۷۸۹".indexOf(digit)).replace(/[٠-٩]/g, (digit) => "٠١٢٣٤٥٦٧٨٩".indexOf(digit));
const normalizeText = (value) => String(value).normalize("NFC").replace(/[يى]/g, "ی").replace(/ك/g, "ک").replace(/\s+/g, " ").trim();
function setupTheme() { const root = document.documentElement; const button = document.querySelector("#theme-toggle"); if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark"); const update = () => { if (button) button.textContent = root.classList.contains("dark") ? "☼" : "☾"; }; button?.addEventListener("click", () => { root.classList.toggle("dark"); localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light"); update(); }); update(); }

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

async function request(path, options = {}) {
  const method = options.method || "GET";
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}) };
  if (method !== "GET") headers["X-CSRFToken"] = await csrf();
  const response = await fetch(`${API_BASE}${path}`, { ...options, method, headers, credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const messages = Object.entries(data)
      .flatMap(([field, value]) => (Array.isArray(value) ? value : [value]).map((message) => `${field}: ${message}`));
    throw Object.assign(new Error(messages.join(" | ") || data.detail || "عملیات انجام نشد."), { status: response.status, data });
  }
  return data;
}

function showAlert(message, kind = "error") {
  const alert = document.querySelector("#checkout-alert");
  alert.hidden = false;
  alert.className = `state-card checkout-alert ${kind}`;
  alert.innerHTML = `<span class="state-icon">${kind === "success" ? "✓" : "!"}</span><h3>${message}</h3><p>${kind === "error" ? "اطلاعات را بررسی کن و دوباره تلاش کن." : "سفارش شما با موفقیت ثبت شد."}</p>${kind === "error" && !state.cart?.items?.length ? "<a class=\"primary-button\" href=\"/\">بازگشت به فروشگاه</a>" : ""}`;
}

function clearFieldErrors(form) {
  form.querySelectorAll(".field-error").forEach((element) => element.remove());
  form.querySelectorAll("[aria-invalid=true]").forEach((element) => {
    element.removeAttribute("aria-invalid");
  });
}

function showFieldErrors(form, data) {
  clearFieldErrors(form);
  let displayed = false;
  Object.entries(data || {}).forEach(([field, messages]) => {
    const input = form.querySelector(`[name="${field}"]`);
    if (!input) return;
    const message = Array.isArray(messages) ? messages[0] : messages;
    input.setAttribute("aria-invalid", "true");
    const error = document.createElement("small");
    error.className = "field-error";
    error.textContent = message;
    input.insertAdjacentElement("afterend", error);
    displayed = true;
  });
  return displayed;
}

function renderAddresses() {
  const list = document.querySelector("#address-list");
  if (!state.addresses.length) {
    list.innerHTML = `<div class="empty-inline">هنوز آدرسی ثبت نکرده‌ای. یک آدرس جدید اضافه کن.</div>`;
    state.selectedAddress = null;
    return;
  }
  if (!state.selectedAddress) state.selectedAddress = state.addresses.find((address) => address.is_default)?.id || state.addresses[0].id;
  list.innerHTML = state.addresses.map((address) => `<div class="address-card"><label><input type="radio" name="address_id" value="${address.id}" ${address.id === state.selectedAddress ? "checked" : ""}><span><strong>${address.title}${address.is_default ? " · پیش‌فرض" : ""}</strong><small>${address.province}، ${address.city}، ${address.address_line}<br>${address.recipient_name} · ${address.recipient_phone}</small></span></label><div class="address-actions"><button class="address-action" data-address-action="edit" data-address-id="${address.id}" type="button">ویرایش</button><button class="address-action delete" data-address-action="delete" data-address-id="${address.id}" type="button">حذف</button></div></div>`).join("");
  list.querySelectorAll("input").forEach((input) => input.addEventListener("change", () => { state.selectedAddress = Number(input.value); }));
  list.querySelectorAll("[data-address-action]").forEach((button) => button.addEventListener("click", () => {
    const address = state.addresses.find((item) => item.id === Number(button.dataset.addressId));
    if (button.dataset.addressAction === "edit") beginAddressEdit(address);
    else deleteAddress(address);
  }));
}

function beginAddressEdit(address) {
  const form = document.querySelector("#address-form");
  form.hidden = false;
  form.dataset.addressId = address.id;
  document.querySelector("#address-form-title").textContent = "ویرایش آدرس";
  Object.entries(address).forEach(([key, value]) => { const input = form.querySelector(`[name="${key}"]`); if (input) input.value = value || ""; });
  form.classList.add("editing");
  form.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function deleteAddress(address) {
  if (!window.confirm(`آدرس «${address.title}» حذف شود؟`)) return;
  try {
    await request(`auth/addresses/${address.id}/`, { method: "DELETE" });
    state.addresses = state.addresses.filter((item) => item.id !== address.id);
    if (state.selectedAddress === address.id) state.selectedAddress = null;
    renderAddresses();
    showAlert("آدرس حذف شد.", "success");
  } catch (error) { showAlert(error.message); }
}

function renderCart() {
  document.querySelector("#checkout-items").innerHTML = state.cart.items.map((item) => `<div class="checkout-item"><span>${item.product.name} × ${faNumber(item.quantity)}</span><strong>${money(item.line_total)}</strong></div>`).join("");
  document.querySelector("#checkout-total").textContent = money(state.cart.total_amount ?? state.cart.subtotal);
}

async function load() {
  try {
    const [profile, cart, addresses] = await Promise.all([request("auth/profile/"), request("cart/"), request("auth/addresses/")]);
    state.cart = cart;
    state.addresses = addresses.results || addresses;
    if (!cart.items?.length) { showAlert("سبد خرید خالی است"); return; }
    document.querySelector("#checkout-content").hidden = false;
    renderAddresses(); renderCart();
  } catch (error) {
    if (error.status === 401) {
      showAlert("برای ادامه ابتدا وارد حساب کاربری شو.");
      document.querySelector("#checkout-alert").insertAdjacentHTML("beforeend", '<a class="primary-button" href="/account/?next=/checkout/">ورود یا ثبت‌نام <span>←</span></a>');
    }
    else showAlert(error.message);
  }
}

document.querySelector("#add-address").addEventListener("click", () => { const form = document.querySelector("#address-form"); form.hidden = false; form.dataset.addressId = ""; form.classList.remove("editing"); form.reset(); document.querySelector("#address-form-title").textContent = "افزودن آدرس جدید"; });
document.querySelector("#cancel-address").addEventListener("click", () => { const form = document.querySelector("#address-form"); form.reset(); form.hidden = true; form.dataset.addressId = ""; form.classList.remove("editing"); });
document.querySelector("#address-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  clearFieldErrors(form);
  const payload = Object.fromEntries(new FormData(form));
  payload.is_default = true;
  ["title", "province", "city", "address_line", "recipient_name", "recipient_phone"].forEach((field) => { payload[field] = normalizeText(payload[field]); });
  payload.postal_code = latinizeDigits(payload.postal_code).replace(/\s/g, "");
  payload.recipient_phone = latinizeDigits(payload.recipient_phone).replace(/\s/g, "");
  const submit = form.querySelector("button[type=submit]");
  submit.disabled = true;
  if (payload.postal_code.length !== 10 || !/^\d+$/.test(payload.postal_code)) {
    showFieldErrors(form, { postal_code: "کدپستی باید دقیقاً ۱۰ رقم باشد." });
    submit.disabled = false;
    return;
  }
  try {
    const addressId = form.dataset.addressId;
    const address = await request(addressId ? `auth/addresses/${addressId}/` : "auth/addresses/", { method: addressId ? "PATCH" : "POST", body: JSON.stringify(payload) });
    if (addressId) state.addresses = state.addresses.map((item) => item.id === Number(addressId) ? address : item);
    else state.addresses.unshift(address);
    state.selectedAddress = address.id;
    form.reset();
    form.hidden = true;
    form.dataset.addressId = "";
    form.classList.remove("editing");
    document.querySelector("#address-form-title").textContent = "افزودن آدرس جدید";
    renderAddresses();
    showAlert("آدرس با موفقیت ذخیره شد.", "success");
  } catch (error) {
    if (!showFieldErrors(form, error.data)) showAlert(error.message);
  }
  finally { submit.disabled = false; }
});
document.querySelector("#checkout-submit").addEventListener("click", async () => {
  if (!state.selectedAddress) { showAlert("یک آدرس ارسال انتخاب کن."); return; }
  const button = document.querySelector("#checkout-submit"); button.disabled = true;
  try {
    state.order = await request("cart/checkout/", { method: "POST", body: JSON.stringify({ address_id: state.selectedAddress }) });
    const paid = await request(`orders/${state.order.order_number}/mock-payment/`, { method: "POST", body: JSON.stringify({ result: "success" }) });
    document.querySelector("#checkout-content").hidden = true;
    showAlert(`سفارش ${paid.order_number} با موفقیت ثبت و پرداخت شد.`, "success");
  } catch (error) { showAlert(error.message); button.disabled = false; }
});
load();
setupTheme();
