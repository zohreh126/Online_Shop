const API_BASE = "/api/v1/";
const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const money = (value) => `${faNumber(Math.round(Number(value)))} تومان`;
const statusLabels = { pending: "در انتظار پرداخت", confirmed: "تأیید شده", processing: "در حال پردازش", shipped: "ارسال شده", delivered: "تحویل شده", cancelled: "لغو شده", refunded: "مرجوع شده" };
const paymentLabels = { unpaid: "پرداخت نشده", pending: "در انتظار پرداخت", paid: "پرداخت موفق", failed: "پرداخت ناموفق", refunded: "مرجوع شده" };

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(data.detail || "دریافت اطلاعات انجام نشد."), { status: response.status });
  return data;
}

function showAlert(message) {
  const alert = document.querySelector("#dashboard-alert");
  alert.hidden = false;
  alert.innerHTML = `<span class="state-icon">!</span><h3>${message}</h3><a class="primary-button" href="/account/">ورود به حساب <span>←</span></a>`;
}

function renderOrderDetail(container, order) {
  container.innerHTML = `<div class="order-detail"><div class="order-address"><strong>آدرس ارسال</strong><p>${order.shipping_province}، ${order.shipping_city}، ${order.shipping_address_line}</p><small>${order.shipping_recipient_name} · ${order.shipping_recipient_phone}</small></div><div class="order-items">${order.items.map((item) => `<div class="checkout-item"><span>${item.product_name} × ${faNumber(item.quantity)}</span><strong>${money(item.line_total)}</strong></div>`).join("")}</div></div>`;
}

function renderOrders(orders) {
  const list = document.querySelector("#orders-list");
  document.querySelector("#order-count").textContent = `${faNumber(orders.length)} سفارش`;
  if (!orders.length) { list.innerHTML = `<div class="empty-inline">هنوز سفارشی ثبت نکرده‌ای.</div>`; return; }
  list.innerHTML = orders.map((order) => `<article class="order-card"><button class="order-summary" data-order="${order.order_number}" type="button"><span><strong>سفارش ${String(order.order_number).slice(0, 8).toUpperCase()}</strong><small>${new Date(order.created_at).toLocaleDateString("fa-IR")}</small></span><span><b>${money(order.total_amount)}</b><small class="status-${order.status}">${statusLabels[order.status] || order.status} · ${paymentLabels[order.payment_status] || order.payment_status}</small></span><i>⌄</i></button><div class="order-detail-slot" hidden></div></article>`).join("");
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
    document.querySelector("#dashboard-content").hidden = false;
    renderOrders(orders.results || orders);
  } catch (error) {
    showAlert(error.status === 401 ? "برای مشاهده داشبورد ابتدا وارد حساب شو." : error.message);
  }
}

loadDashboard();
