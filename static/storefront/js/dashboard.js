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
const dashboardRoleKey = (profile) => profile?.is_superuser || (profile?.is_staff && !profile?.role) ? "roleAdministrator" : (roleLabels[profile?.role] || "normalCustomer");
let dashboardOrders = [];
let dashboardSnapshot = null;
function setupTheme() { const root = document.documentElement; const button = document.querySelector("#theme-toggle"); if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark"); const update = () => { if (button) button.textContent = root.classList.contains("dark") ? "☼" : "☾"; }; button?.addEventListener("click", () => { root.classList.toggle("dark"); localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light"); update(); }); update(); }

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(data.detail || tr("operationFailed")), { status: response.status });
  return data;
}

function getCookie(name) { const cookie = (document.cookie ? document.cookie.split("; ") : []).find((value) => value.startsWith(`${name}=`)); return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null; }
async function csrf() { let token = getCookie("csrftoken"); if (token) return token; await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" }); return getCookie("csrftoken"); }
function showToast(message) { const toast = document.createElement("div"); toast.className = "toast-message"; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => toast.remove(), 3200); }

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
  list.innerHTML = orders.map((order) => `<article class="order-card"><button class="order-summary" data-order="${order.order_number}" type="button"><span><strong>${formatMessage("orderLabel", { number: String(order.order_number).slice(0, 8).toUpperCase() })}</strong><small>${new Date(order.created_at).toLocaleDateString(document.documentElement.lang === "en" ? "en-US" : "fa-IR")}</small></span><span><b>${money(order.total_amount)}</b><small class="status-${order.status}">${tr(statusLabels[order.status] || order.status)} · ${tr(paymentLabels[order.payment_status] || order.payment_status)}</small></span><i>⌄</i></button><div class="order-actions"><button class="order-reorder" data-reorder="${order.order_number}" type="button" title="${tr("reorderHint")}"><span aria-hidden="true">↻</span><span>${tr("reorder")}</span></button></div><div class="order-detail-slot" hidden></div></article>`).join("");
  list.querySelectorAll(".order-summary").forEach((button) => button.addEventListener("click", async () => {
    const slot = button.parentElement.querySelector(".order-detail-slot");
    if (!slot.hidden) { slot.hidden = true; return; }
    slot.innerHTML = `<div class="drawer-loading"><span class="loader"></span></div>`; slot.hidden = false;
    try { renderOrderDetail(slot, await request(`orders/${button.dataset.order}/`)); } catch (error) { slot.innerHTML = `<p class="field-error">${error.message}</p>`; }
  }));
  list.querySelectorAll(".order-reorder").forEach((button) => button.addEventListener("click", () => reorderOrder(button.dataset.reorder, button)));
}

function collectionCount(value) {
  if (Number.isFinite(Number(value?.count))) return Number(value.count);
  const items = value?.results || value;
  return Array.isArray(items) ? items.length : 0;
}

function renderDashboardOverview(snapshot) {
  const counts = {
    orders: snapshot.orders.length,
    addresses: collectionCount(snapshot.addresses),
    favorites: collectionCount(snapshot.favorites),
    rewards: Number(snapshot.rewards?.balance || 0),
  };
  const values = {
    "dashboard-stat-orders": counts.orders,
    "dashboard-stat-addresses": counts.addresses,
    "dashboard-stat-favorites": counts.favorites,
    "dashboard-stat-rewards": counts.rewards,
  };
  Object.entries(values).forEach(([id, value]) => {
    const element = document.querySelector(`#${id}`);
    if (element) element.textContent = localizedNumber(value);
  });
}

async function reorderOrder(orderNumber, button) {
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}orders/${encodeURIComponent(orderNumber)}/reorder/`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": await csrf() },
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      window.location.href = `/account/?next=${encodeURIComponent(window.location.pathname)}`;
      return;
    }
    if (!response.ok) throw new Error(data.detail || tr("reorderFailed"));
    const addedCount = (data.added || []).reduce((total, item) => total + Number(item.quantity || 0), 0);
    const skippedCount = (data.skipped || []).length;
    const notice = skippedCount ? formatMessage("reorderPartial", { added: localizedNumber(addedCount), skipped: localizedNumber(skippedCount) }) : formatMessage("reorderSuccess", { count: localizedNumber(addedCount) });
    sessionStorage.setItem("nexora-toast", notice);
    window.location.href = "/?cart=open";
  } catch (error) {
    showToast(error.message || tr("reorderFailed"));
    button.disabled = false;
  }
}

async function loadDashboard() {
  try {
    const [profile, orders, addresses, favorites, rewards] = await Promise.all([
      request("auth/profile/"),
      request("orders/?page_size=100"),
      request("auth/addresses/?page_size=100"),
      request("auth/favorites/?page_size=100"),
      request("auth/rewards/"),
    ]);
    document.querySelector("#dashboard-profile").textContent = `${profile.first_name || profile.username} · ${profile.email}`;
    document.querySelector("#dashboard-role").textContent = tr(dashboardRoleKey(profile));
    document.querySelector("#dashboard-content").hidden = false;
    dashboardOrders = orders.results || orders;
    dashboardSnapshot = { profile, orders: dashboardOrders, addresses, favorites, rewards };
    renderDashboardOverview(dashboardSnapshot);
    renderOrders(dashboardOrders);
  } catch (error) {
    showAlert(error.status === 401 ? tr("loginToDashboard") : error.message);
  }
}

window.addEventListener("nexora-language-changed", () => { if (dashboardSnapshot) renderDashboardOverview(dashboardSnapshot); if (dashboardSnapshot) renderOrders(dashboardOrders); });
loadDashboard();
setupTheme();
