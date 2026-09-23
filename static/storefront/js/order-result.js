const API_BASE = "/api/v1/";
const tr = (key) => window.NexoraI18n?.t(key) || key;
const formatMessage = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll("{" + name + "}", value), tr(key));
const params = new URLSearchParams(window.location.search);
const orderNumber = params.get("order");
const requestedStatus = params.get("status");
const localizedNumber = (value) => new Intl.NumberFormat(document.documentElement.lang === "en" ? "en-US" : "fa-IR").format(Math.round(Number(value || 0)));
const money = (value) => `${localizedNumber(value)} ${tr("toman")}`;

function setupTheme() {
  const root = document.documentElement;
  const button = document.querySelector("#theme-toggle");
  if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark");
  const update = () => { button.textContent = root.classList.contains("dark") ? "☼" : "☾"; };
  button.addEventListener("click", () => { root.classList.toggle("dark"); localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light"); update(); });
  update();
}

async function loadOrder() {
  if (!orderNumber) throw new Error(tr("operationFailed"));
  const response = await fetch(API_BASE + "orders/" + encodeURIComponent(orderNumber) + "/", { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || tr("operationFailed"));
  return data;
}

function renderResult(order) {
  const failed = requestedStatus === "failed" || order.payment_status === "failed" || order.status === "cancelled";
  const card = document.querySelector("#order-result-card");
  card.className = "order-result-card " + (failed ? "failed" : "success");
  const productDiscount = Number(order.product_discount_amount || 0);
  const couponDiscount = Number(order.coupon_discount_amount || 0);
  const shipping = Number(order.shipping_amount || 0);
  const summary = `<div class="result-summary"><div><span>${tr("cartSubtotal")}</span><strong>${money(order.subtotal)}</strong></div>${productDiscount > 0 ? `<div class="is-discount"><span>${tr("productDiscount")}</span><strong>−${money(productDiscount)}</strong></div>` : ""}${couponDiscount > 0 ? `<div class="is-discount"><span>${tr("couponDiscount")}</span><strong>−${money(couponDiscount)}</strong></div>` : ""}<div><span>${tr("shippingFee")}</span><strong>${shipping > 0 ? money(shipping) : tr("free")}</strong></div><div class="is-total"><span>${tr("profileOrderTotal")}</span><strong>${money(order.total_amount)}</strong></div></div>`;
  card.innerHTML = "<div class=\"result-icon\">" + (failed ? "!" : "✓") + "</div><p class=\"eyebrow\"><span></span><span>" + tr("orderResult") + "</span></p><h1>" + (failed ? tr("orderFailed") : tr("orderConfirmed")) + "</h1><p class=\"result-description\">" + (failed ? tr("orderResultFailedText") : tr("orderResultSuccessText")) + "</p><div class=\"result-order-number\"><span>" + tr("orderNumber") + "</span><strong>" + order.order_number + "</strong></div>" + summary + "<div class=\"result-actions\"><a class=\"primary-button\" href=\"/profile/?section=orders\">" + tr("viewOrders") + " <span>←</span></a><a class=\"secondary-button\" href=\"/\">" + tr("continueShopping") + "</a></div>";
  card.hidden = false;
  document.querySelector("#order-result-loading").hidden = true;
  document.title = (failed ? tr("orderFailed") : tr("orderConfirmed")) + " | Nexora";
}

function showError(message) {
  const loading = document.querySelector("#order-result-loading");
  loading.innerHTML = "<span class=\"state-icon\">!</span><h3>" + message + "</h3><a class=\"primary-button\" href=\"/\">" + tr("continueShopping") + "</a>";
}

window.addEventListener("nexora-language-changed", () => { if (window.loadedOrder) renderResult(window.loadedOrder); });
setupTheme();
loadOrder().then((order) => { window.loadedOrder = order; renderResult(order); }).catch((error) => showError(error.message));
