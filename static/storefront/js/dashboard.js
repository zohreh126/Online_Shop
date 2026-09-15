const API_BASE = "/api/v1/";
const tr = (key) => window.NexoraI18n?.t(key) || key;
const productName = (item) => window.NexoraI18n?.productName({ sku: item.product_sku, product_name: item.product_name }) || item.product_name;
const formatMessage = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, value), tr(key));
const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const localizedNumber = (value) => new Intl.NumberFormat(document.documentElement.lang === "en" ? "en-US" : "fa-IR").format(value);
const money = (value) => `${localizedNumber(Math.round(Number(value)))} ${tr("toman")}`;
const statusLabels = { pending: "pending", confirmed: "confirmed", processing: "processing", shipped: "shipped", delivered: "delivered", cancelled: "cancelled", refunded: "refunded" };
const paymentLabels = { unpaid: "unpaid", pending: "pending", paid: "paid", failed: "failed", refunded: "refunded" };
const roleLabels = { product_manager: "roleProductManager", supervisor: "roleSupervisor", operator: "roleOperator" };
let dashboardOrders = [];
function setupTheme() { const root = document.documentElement; const button = document.querySelector("#theme-toggle"); if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark"); const update = () => { if (button) button.textContent = root.classList.contains("dark") ? "☼" : "☾"; }; button?.addEventListener("click", () => { root.classList.toggle("dark"); localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light"); update(); }); update(); }

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(data.detail || tr("operationFailed")), { status: response.status });
  return data;
}

function showAlert(message) {
  const alert = document.querySelector("#dashboard-alert");
  alert.hidden = false;
  alert.innerHTML = `<span class="state-icon">!</span><h3>${message}</h3><a class="primary-button" href="/account/">${tr("login")} <span>←</span></a>`;
}

function renderOrderDetail(container, order) {
  container.innerHTML = `<div class="order-detail"><div class="order-address"><strong>${tr("shippingAddressLabel")}</strong><p>${order.shipping_province}، ${order.shipping_city}، ${order.shipping_address_line}</p><small>${order.shipping_recipient_name} · ${order.shipping_recipient_phone}</small></div><div class="order-items">${order.items.map((item) => `<div class="checkout-item"><span>${productName(item)} × ${localizedNumber(item.quantity)}</span><strong>${money(item.line_total)}</strong></div>`).join("")}</div></div>`;
}

function renderOrders(orders) {
  const list = document.querySelector("#orders-list");
  document.querySelector("#order-count").textContent = formatMessage("orderCount", { count: localizedNumber(orders.length) });
  if (!orders.length) { list.innerHTML = `<div class="empty-inline">${tr("noOrders")}</div>`; return; }
  list.innerHTML = orders.map((order) => `<article class="order-card"><button class="order-summary" data-order="${order.order_number}" type="button"><span><strong>${formatMessage("orderLabel", { number: String(order.order_number).slice(0, 8).toUpperCase() })}</strong><small>${new Date(order.created_at).toLocaleDateString(document.documentElement.lang === "en" ? "en-US" : "fa-IR")}</small></span><span><b>${money(order.total_amount)}</b><small class="status-${order.status}">${tr(statusLabels[order.status] || order.status)} · ${tr(paymentLabels[order.payment_status] || order.payment_status)}</small></span><i>⌄</i></button><div class="order-detail-slot" hidden></div></article>`).join("");
  list.querySelectorAll(".order-summary").forEach((button) => button.addEventListener("click", async () => {
    const slot = button.nextElementSibling;
    if (!slot.hidden) { slot.hidden = true; return; }
    slot.innerHTML = `<div class="drawer-loading"><span class="loader"></span></div>`; slot.hidden = false;
    try { renderOrderDetail(slot, await request(`orders/${button.dataset.order}/`)); } catch (error) { slot.innerHTML = `<p class="field-error">${error.message}</p>`; }
  }));
}

async function loadDashboard() {
  try {
    const [profile, orders] = await Promise.all([request("auth/profile/"), request("orders/?page_size=100")]);
    document.querySelector("#dashboard-profile").textContent = `${profile.first_name || profile.username} · ${profile.email}`;
    document.querySelector("#dashboard-role").textContent = roleLabels[profile.role] ? tr(roleLabels[profile.role]) : tr("normalCustomer");
    document.querySelector("#dashboard-content").hidden = false;
    dashboardOrders = orders.results || orders;
    renderOrders(dashboardOrders);
  } catch (error) {
    showAlert(error.status === 401 ? tr("loginToDashboard") : error.message);
  }
}

window.addEventListener("nexora-language-changed", () => { if (dashboardOrders.length) renderOrders(dashboardOrders); });
loadDashboard();
setupTheme();
