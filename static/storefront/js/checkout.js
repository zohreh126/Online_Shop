const API_BASE = "/api/v1/";
const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const money = (value) => `${faNumber(Math.round(Number(value)))} تومان`;
const state = { cart: null, addresses: [], selectedAddress: null, order: null };

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
  if (!response.ok) throw Object.assign(new Error(data.detail || data.address_id?.[0] || "عملیات انجام نشد."), { status: response.status, data });
  return data;
}

function showAlert(message, kind = "error") {
  const alert = document.querySelector("#checkout-alert");
  alert.hidden = false;
  alert.className = `state-card checkout-alert ${kind}`;
  alert.innerHTML = `<span class="state-icon">${kind === "success" ? "✓" : "!"}</span><h3>${message}</h3><p>${kind === "error" ? "اطلاعات را بررسی کن و دوباره تلاش کن." : "سفارش شما با موفقیت ثبت شد."}</p>${kind === "error" && !state.cart?.items?.length ? "<a class=\"primary-button\" href=\"/\">بازگشت به فروشگاه</a>" : ""}`;
}

function renderAddresses() {
  const list = document.querySelector("#address-list");
  if (!state.addresses.length) {
    list.innerHTML = `<div class="empty-inline">هنوز آدرسی ثبت نکرده‌ای. یک آدرس جدید اضافه کن.</div>`;
    state.selectedAddress = null;
    return;
  }
  if (!state.selectedAddress) state.selectedAddress = state.addresses.find((address) => address.is_default)?.id || state.addresses[0].id;
  list.innerHTML = state.addresses.map((address) => `<label class="address-card"><input type="radio" name="address_id" value="${address.id}" ${address.id === state.selectedAddress ? "checked" : ""}><span><strong>${address.title}${address.is_default ? " · پیش‌فرض" : ""}</strong><small>${address.province}، ${address.city}، ${address.address_line}<br>${address.recipient_name} · ${address.recipient_phone}</small></span></label>`).join("");
  list.querySelectorAll("input").forEach((input) => input.addEventListener("change", () => { state.selectedAddress = Number(input.value); }));
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
    if (error.status === 401) showAlert("برای ادامه ابتدا وارد حساب کاربری شو.");
    else showAlert(error.message);
  }
}

document.querySelector("#add-address").addEventListener("click", () => { document.querySelector("#address-form").hidden = false; });
document.querySelector("#address-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  try { const address = await request("auth/addresses/", { method: "POST", body: JSON.stringify(payload) }); state.addresses.unshift(address); state.selectedAddress = address.id; event.currentTarget.reset(); event.currentTarget.hidden = true; renderAddresses(); }
  catch (error) { showAlert(error.message); }
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
