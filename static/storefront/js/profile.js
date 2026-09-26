const API_BASE = "/api/v1/";
const tr = (key) => window.NexoraI18n?.t(key) || key;
const formatMessage = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, value), tr(key));
const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const localizedNumber = (value) => new Intl.NumberFormat(document.documentElement.lang === "en" ? "en-US" : "fa-IR").format(value);
const money = (value) => `${localizedNumber(Math.round(Number(value)))} ${tr("toman")}`;
const digits = (value) => String(value ?? "").replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d));
const normalizeText = (value) => String(value ?? "").normalize("NFC").replace(/[يى]/g, "ی").replace(/ك/g, "ک").replace(/\s+/g, " ").trim();
const state = { profile: null, addresses: [], orders: [], favorites: [], watches: [], watchesLoaded: false, rewards: null, rewardsLoaded: false };
const PROFILE_ORDER_STEPS = [
  { key: "pending", label: "profileOrderPlaced", icon: "1" },
  { key: "confirmed", label: "profileOrderConfirmed", icon: "2" },
  { key: "processing", label: "profileOrderProcessing", icon: "3" },
  { key: "shipped", label: "profileOrderShipped", icon: "4" },
  { key: "delivered", label: "profileOrderDelivered", icon: "5" },
];
const PROFILE_ORDER_STATUS_INDEX = { pending: 0, confirmed: 1, processing: 2, shipped: 3, delivered: 4 };

const roleTranslationKey = { product_manager: "roleProductManager", supervisor: "roleSupervisor", operator: "roleOperator" };
function profileRoleKey(profile) {
  if (profile?.is_superuser || (profile?.is_staff && !profile?.role)) return "roleAdministrator";
  return roleTranslationKey[profile?.role] || "normalCustomer";
}
const PROFILE_SECTIONS = ["personal", "addresses", "orders", "favorites", "watches", "rewards", "security"];

function getCookie(name) { const cookie = (document.cookie ? document.cookie.split("; ") : []).find((value) => value.startsWith(`${name}=`)); return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null; }
async function csrf() { let token = getCookie("csrftoken"); if (token) return token; await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" }); return getCookie("csrftoken"); }
async function request(path, options = {}) {
  const method = options.method || "GET"; const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}) };
  if (method !== "GET") headers["X-CSRFToken"] = await csrf();
  const response = await fetch(`${API_BASE}${path}`, { ...options, method, headers, credentials: "same-origin" }); const data = await response.json().catch(() => ({}));
  if (!response.ok) { const messages = Object.entries(data).flatMap(([field, value]) => (Array.isArray(value) ? value : [value]).map((item) => `${field}: ${item}`)); throw Object.assign(new Error(messages.join(" | ") || data.detail || tr("operationFailed")), { status: response.status, data }); }
  return data;
}
function setupTheme() { const root = document.documentElement; const button = document.querySelector("#theme-toggle"); if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark"); const update = () => { if (button) button.textContent = root.classList.contains("dark") ? "☼" : "☾"; }; button?.addEventListener("click", () => { root.classList.toggle("dark"); localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light"); update(); }); update(); }
function message(text, success = false) { const alert = document.querySelector("#profile-alert"); alert.hidden = false; alert.className = `account-alert ${success ? "success" : "error"}`; alert.textContent = text; }
function clearErrors(form) { form.querySelectorAll(".field-error").forEach((item) => item.remove()); form.querySelectorAll("[aria-invalid=true]").forEach((item) => item.removeAttribute("aria-invalid")); }
function showErrors(form, data) { clearErrors(form); let shown = false; Object.entries(data || {}).forEach(([field, values]) => { const input = form.querySelector(`[name="${field}"]`); if (!input) return; input.setAttribute("aria-invalid", "true"); const error = document.createElement("small"); error.className = "field-error"; error.textContent = Array.isArray(values) ? values[0] : values; input.insertAdjacentElement("afterend", error); shown = true; }); return shown; }
function escapeHTML(value) { return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char])); }
const favoriteProductName = (product) => window.NexoraI18n?.productName(product) || product.name || product.product_name || tr("product");
const favoriteSavings = (product) => { const amount = Number(product.discount_amount || 0); return amount > 0 ? `<small class="product-savings"><span aria-hidden="true">✦</span>${escapeHTML(tr("youSave").replace("{amount}", money(amount)))}</small>` : ""; };
function favoriteCard(product) {
  const name = favoriteProductName(product);
  const category = product.category ? (window.NexoraI18n?.category(product.category.slug, product.category.name) || product.category.name) : tr("digitalAccessories");
  const href = "/products/" + encodeURIComponent(product.slug) + "/";
  const image = window.NexoraI18n?.productVisualMarkup?.(product, {
    className: "favorite-product-art",
    alt: tr("productImageAlt").replace("{name}", name),
  }) || "<span class=\"favorite-placeholder\">✦</span>";
  const discount = Number(product.discount_amount) > 0 ? "<del>" + money(product.price) + "</del>" : "";
  return "<article class=\"favorite-card\"><a class=\"favorite-card-visual\" href=\"" + escapeHTML(href) + "\">" + image + "</a><div class=\"favorite-card-info\"><p class=\"product-category\">" + escapeHTML(category) + "</p><h3><a href=\"" + escapeHTML(href) + "\">" + escapeHTML(name) + "</a></h3><div class=\"favorite-card-bottom\"><div class=\"price-stack\"><strong>" + money(product.final_price) + "</strong>" + discount + favoriteSavings(product) + "</div><button class=\"heart-button favorite-remove\" data-favorite-product=\"" + product.id + "\" type=\"button\" aria-label=\"" + tr("removeFromFavorites") + "\" aria-pressed=\"true\">♥</button></div></div></article>";
}
function renderFavorites() {
  const list = document.querySelector("#profile-favorites");
  if (!list) return;
  if (!state.favorites.length) { list.innerHTML = "<div class=\"empty-inline\">" + tr("noFavorites") + "</div>"; updateProfileStats(); return; }
  list.innerHTML = state.favorites.map(favoriteCard).join("");
  window.NexoraFavorites?.bindButtons(list);
  updateProfileStats();
}
function renderProfileCompletion() {
  if (!state.profile) return;
  const steps = [
    { complete: Boolean(state.profile.first_name && state.profile.last_name), label: tr("personalInfo"), section: "personal" },
    { complete: Boolean(state.profile.phone_number), label: tr("phone"), section: "personal" },
    { complete: Boolean(state.profile.email_verified), label: tr("emailVerified"), section: "personal" },
    { complete: state.addresses.length > 0, label: tr("addresses"), section: "addresses" },
  ];
  const completed = steps.filter((step) => step.complete).length;
  const percentage = Math.round((completed / steps.length) * 100);
  const remaining = steps.length - completed;
  const percent = document.querySelector("#profile-completion-percent");
  const progress = document.querySelector("#profile-completion-progress");
  const hint = document.querySelector("#profile-completion-hint");
  const next = document.querySelector("#profile-completion-next");
  const action = document.querySelector("#profile-completion-action");
  const percentSuffix = document.documentElement.lang === "en" ? "%" : "٪";
  const nextStep = steps.find((step) => !step.complete);
  if (percent) percent.textContent = `${localizedNumber(percentage)}${percentSuffix}`;
  if (progress) progress.style.width = `${percentage}%`;
  const progressBar = progress?.parentElement;
  if (progressBar) progressBar.setAttribute("aria-valuenow", String(percentage));
  if (hint) hint.textContent = remaining ? formatMessage("profileCompletionHint", { remaining: localizedNumber(remaining) }) : tr("profileCompletionDone");
  if (next) next.textContent = nextStep ? formatMessage("profileCompletionNext", { step: nextStep.label }) : tr("profileCompletionDone");
  if (action) {
    action.hidden = !nextStep;
    if (nextStep) action.dataset.profileShortcut = nextStep.section;
  }
}
function updateProfileStats() {
  const values = {
    "#profile-orders-count": state.orders.length,
    "#profile-addresses-count": state.addresses.length,
    "#profile-favorites-count": state.favorites.length,
    "#profile-watches-count": state.watches.length,
    "#profile-reward-points": state.rewards?.balance || 0,
  };
  Object.entries(values).forEach(([selector, value]) => {
    const element = document.querySelector(selector);
    if (element) element.textContent = localizedNumber(value);
  });
  renderProfileCompletion();
}

function watchCard(watch) {
  const product = watch.product || {};
  const name = favoriteProductName(product);
  const href = `/products/${encodeURIComponent(product.slug || "")}/`;
  const alerts = [watch.notify_price_drop ? tr("priceDropAlert") : "", watch.notify_restock ? tr("restockAlert") : ""].filter(Boolean).join(" · ");
  const target = Number(watch.target_price || 0) > 0 ? `<small>${escapeHTML(tr("watchTargetPrice"))}: ${escapeHTML(money(watch.target_price))}</small>` : "";
  return `<article class="profile-watch-card"><span class="profile-watch-icon" aria-hidden="true">◉</span><div class="profile-watch-info"><a href="${escapeHTML(href)}"><strong>${escapeHTML(name)}</strong></a><small>${escapeHTML(alerts)}</small>${target}</div><div class="profile-watch-side"><strong>${escapeHTML(money(watch.current_price))}</strong><button class="address-action delete" data-watch-delete="${watch.id}" type="button" aria-label="${escapeHTML(tr("stopWatching"))}">×</button></div></article>`;
}

function renderWatches() {
  const list = document.querySelector("#profile-watches");
  if (!list) return;
  if (!state.watches.length) {
    list.innerHTML = `<div class="empty-inline">${escapeHTML(tr("noProductWatches"))}</div>`;
    updateProfileStats();
    return;
  }
  list.innerHTML = state.watches.map(watchCard).join("");
  list.querySelectorAll("[data-watch-delete]").forEach((button) => {
    button.addEventListener("click", () => {
      const watch = state.watches.find((item) => Number(item.id) === Number(button.dataset.watchDelete));
      if (watch) deleteWatch(watch);
    });
  });
  updateProfileStats();
}

async function loadWatches() {
  if (state.watchesLoaded) {
    renderWatches();
    return;
  }
  try {
    const data = await request("auth/product-watches/?page_size=100");
    state.watches = data.results || data || [];
    state.watchesLoaded = true;
    renderWatches();
  } catch (error) {
    message(error.message || tr("productWatchLoadFailed"));
  }
}

async function deleteWatch(watch) {
  const name = favoriteProductName(watch.product || {});
  if (!window.confirm(formatMessage("watchDeleteConfirm", { name }))) return;
  try {
    await request(`auth/product-watches/${watch.id}/`, { method: "DELETE" });
    state.watches = state.watches.filter((item) => Number(item.id) !== Number(watch.id));
    renderWatches();
    message(tr("watchRemoved"), true);
  } catch (error) {
    message(error.message || tr("operationFailed"));
  }
}

function renderRewards() {
  const container = document.querySelector("#profile-rewards");
  if (!container || !state.rewards) return;
  const transactions = state.rewards.transactions || [];
  const balance = localizedNumber(state.rewards.balance || 0);
  const history = transactions.length
    ? transactions.map((item) => {
      const date = new Date(item.created_at).toLocaleDateString(document.documentElement.lang === "en" ? "en-US" : "fa-IR");
      return `<article class="reward-history-item"><span class="reward-history-icon" aria-hidden="true">✦</span><div><strong>${escapeHTML(tr("rewardOrder"))}</strong><small>${escapeHTML(item.reason || tr("rewardOrder"))} · ${escapeHTML(date)}</small></div><b>+${escapeHTML(localizedNumber(item.points || 0))}</b></article>`;
    }).join("")
    : `<div class="empty-inline">${escapeHTML(tr("noRewards"))}</div>`;
  container.innerHTML = `<div class="reward-balance-card"><span class="reward-balance-icon" aria-hidden="true">✦</span><div><small>${escapeHTML(tr("rewardBalance"))}</small><strong>${escapeHTML(balance)}</strong><span>${escapeHTML(tr("rewardPoints"))}</span></div><p>${escapeHTML(tr("rewardRule"))}</p></div><div class="reward-history"><div class="reward-history-heading"><strong>${escapeHTML(tr("rewardHistory"))}</strong><small>${escapeHTML(tr("rewardHint"))}</small></div>${history}</div>`;
  updateProfileStats();
}

async function loadRewards() {
  if (state.rewardsLoaded) {
    renderRewards();
    return;
  }
  try {
    state.rewards = await request("auth/rewards/");
    state.rewardsLoaded = true;
    renderRewards();
  } catch (error) {
    if (error.status === 401) window.location.href = "/account/?next=/profile/";
    else message(error.message || tr("operationFailed"));
  }
}

async function loadFavorites() {
  try {
    const favorites = await (window.NexoraFavorites?.refresh ? window.NexoraFavorites.refresh() : window.NexoraFavorites?.load());
    state.favorites = (favorites || []).map((item) => item.product).filter(Boolean);
    renderFavorites();
  } catch (error) { message(error.message); }
}
function openSection(name, { persist = true } = {}) {
  const selectedSection = PROFILE_SECTIONS.includes(name) ? name : "personal";
  document.querySelectorAll(".profile-nav button").forEach((button) => {
    const active = button.dataset.section === selectedSection;
    button.classList.toggle("selected", active);
    button.setAttribute("aria-current", active ? "page" : "false");
    button.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll(".profile-section").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === selectedSection));
  if (persist) {
    const url = new URL(window.location.href);
    url.searchParams.set("section", selectedSection);
    window.history.replaceState({ section: selectedSection }, "", url);
  }
  if (selectedSection === "addresses") loadAddresses();
  if (selectedSection === "orders") loadOrders();
  if (selectedSection === "favorites") loadFavorites();
  if (selectedSection === "watches") loadWatches();
  if (selectedSection === "rewards") loadRewards();
}
function renderProfile(profile) { Object.entries(profile).forEach(([key, value]) => { const input = document.querySelector(`[name="${key}"]`); if (input) input.value = value || ""; }); const name = `${profile.first_name || ""} ${profile.last_name || ""}`.trim() || profile.username; const roleKey = profileRoleKey(profile); const roleLabel = tr(roleKey); const profileName = document.querySelector("#profile-name"); const profileEmail = document.querySelector("#profile-email"); const avatar = document.querySelector("#profile-avatar"); const role = document.querySelector("#profile-role"); const roleHint = document.querySelector("#profile-role-hint"); const verified = document.querySelector("#profile-verified"); const emailHint = document.querySelector("#profile-email-hint"); if (profileName) profileName.textContent = name; if (profileEmail) profileEmail.textContent = profile.email || ""; if (avatar) avatar.textContent = (name || "N").slice(0, 1).toUpperCase(); if (role) { role.textContent = roleLabel; role.classList.toggle("is-staff", Boolean(profile.is_staff || profile.is_superuser || profile.role)); } if (roleHint) roleHint.textContent = roleLabel; if (verified) { verified.textContent = profile.email_verified ? `✓ ${tr("emailVerified")}` : `! ${tr("emailNotVerified")}`; verified.classList.toggle("is-warning", !profile.email_verified); } if (emailHint) emailHint.textContent = profile.email_verified ? tr("emailVerified") : tr("emailNotVerified"); renderProfileCompletion(); }
function resetAddressForm() { const form = document.querySelector("#profile-address-form"); form.reset(); form.hidden = true; form.dataset.addressId = ""; form.classList.remove("editing"); document.querySelector("#profile-address-title").textContent = tr("addNewAddress"); clearErrors(form); }
function renderAddresses() { const list = document.querySelector("#profile-addresses"); if (!state.addresses.length) { list.innerHTML = `<div class="empty-inline">${tr("noSavedAddress")}</div>`; return; } list.innerHTML = state.addresses.map((address) => `<article class="profile-address-card"><div><strong>${escapeHTML(address.title)} ${address.is_default ? `<small class="default-badge">${tr("defaultAddress")}</small>` : ""}</strong><p>${escapeHTML(address.province)}، ${escapeHTML(address.city)}، ${escapeHTML(address.address_line)}</p><small>${escapeHTML(address.recipient_name)} · ${escapeHTML(address.recipient_phone)} · ${escapeHTML(address.postal_code)}</small></div><div class="address-actions"><button class="address-action" data-action="edit" data-id="${address.id}" type="button">${tr("editAddress")}</button><button class="address-action delete" data-action="delete" data-id="${address.id}" type="button">${tr("remove")}</button></div></article>`).join(""); list.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => { const address = state.addresses.find((item) => item.id === Number(button.dataset.id)); button.dataset.action === "edit" ? beginAddressEdit(address) : deleteAddress(address); })); }
function beginAddressEdit(address) { const form = document.querySelector("#profile-address-form"); form.hidden = false; form.dataset.addressId = address.id; form.classList.add("editing"); document.querySelector("#profile-address-title").textContent = tr("editAddress"); Object.entries(address).forEach(([key, value]) => { const input = form.querySelector(`[name="${key}"]`); if (input) input.value = value || ""; }); form.scrollIntoView({ behavior: "smooth", block: "center" }); }
async function deleteAddress(address) { if (!window.confirm(formatMessage("addressDeleteConfirm", { title: address.title }))) return; try { await request(`auth/addresses/${address.id}/`, { method: "DELETE" }); state.addresses = state.addresses.filter((item) => item.id !== address.id); renderAddresses(); message(tr("addressRemoved"), true); } catch (error) { message(error.message); } }
async function loadAddresses() { try { const data = await request("auth/addresses/"); state.addresses = data.results || data; renderAddresses(); updateProfileStats(); } catch (error) { if (error.status === 401) window.location.href = "/account/?next=/profile/"; else message(error.message); } }
function formatOrderDate(value) { const date = new Date(value); return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat(document.documentElement.lang === "en" ? "en-US" : "fa-IR", { year: "numeric", month: "short", day: "numeric" }).format(date); }
function orderItemCount(order) { return (order.items || []).reduce((total, item) => total + Number(item.quantity || 0), 0); }
function orderItemName(item) { return window.NexoraI18n?.productName({ sku: item.product_sku, product_name: item.product_name }) || item.product_name || tr("product"); }
function orderStatusLabel(status) { return tr(status || "pending"); }
function orderTimelineMarkup(order) {
  const status = order.status || "pending";
  if (status === "cancelled" || status === "refunded") return `<div class="profile-order-special-status status-${escapeHTML(status)}"><span aria-hidden="true">!</span><strong>${escapeHTML(tr(status === "cancelled" ? "profileOrderCancelled" : "profileOrderRefunded"))}</strong></div>`;
  const activeIndex = PROFILE_ORDER_STATUS_INDEX[status] ?? 0;
  return `<div class="profile-order-timeline" role="list" aria-label="${escapeHTML(tr("profileOrderTimeline"))}">${PROFILE_ORDER_STEPS.map((step, index) => `<div class="profile-order-step ${index < activeIndex ? "is-complete" : ""} ${index === activeIndex ? "is-current" : ""}" role="listitem"><span aria-hidden="true">${index < activeIndex ? "✓" : step.icon}</span><small>${escapeHTML(tr(step.label))}</small></div>`).join("")}</div>`;
}
function renderProfileOrderDetail(container, order) {
  const items = Array.isArray(order.items) ? order.items : [];
  const itemMarkup = items.length ? items.map((item) => `<div class="profile-order-item"><div><strong>${escapeHTML(orderItemName(item))}</strong><small>${escapeHTML(item.product_sku || "")} · ${escapeHTML(formatMessage("profileOrderItems", { count: localizedNumber(item.quantity) }))}</small></div><strong>${escapeHTML(money(item.line_total))}</strong></div>`).join("") : `<div class="empty-inline">${escapeHTML(tr("profileOrderEmptyItems"))}</div>`;
  const productDiscount = Number(order.product_discount_amount || 0);
  const couponDiscount = Number(order.coupon_discount_amount || 0);
  const discountRows = [
    productDiscount > 0 ? `<div class="profile-order-summary-row is-discount"><span>${escapeHTML(tr("discountPerUnit"))}</span><strong>−${escapeHTML(money(productDiscount))}</strong></div>` : "",
    couponDiscount > 0 ? `<div class="profile-order-summary-row is-discount"><span>${escapeHTML(tr("couponDiscount"))}</span><strong>−${escapeHTML(money(couponDiscount))}</strong></div>` : "",
    Number(order.shipping_amount || 0) > 0 ? `<div class="profile-order-summary-row"><span>${escapeHTML(tr("shippingFee"))}</span><strong>${escapeHTML(money(order.shipping_amount))}</strong></div>` : `<div class="profile-order-summary-row"><span>${escapeHTML(tr("shippingFee"))}</span><strong>${escapeHTML(tr("free"))}</strong></div>`,
  ].join("");
  container.innerHTML = `<div class="profile-order-detail-inner"><div class="profile-order-detail-heading"><strong>${escapeHTML(tr("profileOrderDetails"))}</strong><small>${escapeHTML(formatMessage("profileOrderDate", { date: formatOrderDate(order.created_at) }))}</small></div><div class="profile-order-detail-grid"><div class="profile-order-detail-panel"><h3><span aria-hidden="true">▣</span>${escapeHTML(tr("profileOrderItemsHeading"))}</h3><div class="profile-order-items">${itemMarkup}</div></div><div class="profile-order-detail-panel"><h3><span aria-hidden="true">✦</span>${escapeHTML(tr("profileOrderSummary"))}</h3><div class="profile-order-summary-row"><span>${escapeHTML(tr("cartSubtotal"))}</span><strong>${escapeHTML(money(order.subtotal))}</strong></div>${discountRows}<div class="profile-order-summary-row is-total"><span>${escapeHTML(tr("profileOrderTotal"))}</span><strong>${escapeHTML(money(order.total_amount))}</strong></div></div></div><div class="profile-order-delivery"><h3><span aria-hidden="true">⌖</span>${escapeHTML(tr("shippingAddressLabel"))}</h3><p>${escapeHTML([order.shipping_province, order.shipping_city, order.shipping_address_line].filter(Boolean).join("، "))}</p><small>${escapeHTML(order.shipping_recipient_name || "")} · ${escapeHTML(order.shipping_recipient_phone || "")}</small></div></div>`;
}
function renderOrders() {
  const list = document.querySelector("#profile-orders");
  if (!state.orders.length) { list.innerHTML = `<div class="empty-inline">${escapeHTML(tr("noOrders"))}</div>`; return; }
  list.innerHTML = state.orders.map((order) => {
    const status = order.status || "pending";
    const itemCount = orderItemCount(order);
    const previewItems = (order.items || []).slice(0, 2).map((item) => escapeHTML(orderItemName(item))).join(" · ");
    const extraItems = Math.max(0, (order.items || []).length - 2);
    const savings = Number(order.product_discount_amount || 0) + Number(order.coupon_discount_amount || 0);
    return `<article class="profile-order-card"><header class="profile-order-header"><div class="profile-order-number"><span class="profile-order-icon" aria-hidden="true">▣</span><div><strong>${escapeHTML(formatMessage("orderLabel", { number: String(order.order_number).slice(0, 8).toUpperCase() }))}</strong><small>${escapeHTML(formatMessage("profileOrderDate", { date: formatOrderDate(order.created_at) }))}</small></div></div><span class="profile-order-status status-${escapeHTML(status)}"><span aria-hidden="true">●</span>${escapeHTML(orderStatusLabel(status))}</span></header><div class="profile-order-overview"><div class="profile-order-preview"><small>${escapeHTML(formatMessage("profileOrderItems", { count: localizedNumber(itemCount) }))}</small><strong>${previewItems || escapeHTML(tr("profileOrderEmptyItems"))}${extraItems ? ` <span>+${escapeHTML(localizedNumber(extraItems))}</span>` : ""}</strong></div><div class="profile-order-metric"><small>${escapeHTML(tr("profileOrderPayment"))}</small><strong>${escapeHTML(tr(order.payment_status || "unpaid"))}</strong></div><div class="profile-order-metric profile-order-total"><small>${escapeHTML(tr("profileOrderTotal"))}</small><strong>${escapeHTML(money(order.total_amount))}</strong></div></div>${orderTimelineMarkup(order)}<footer class="profile-order-footer"><span class="profile-order-saving" ${savings > 0 ? "" : "hidden"}><span aria-hidden="true">✦</span>${escapeHTML(tr("profileOrderSaved"))}: ${escapeHTML(money(savings))}</span><div class="profile-order-actions"><button class="profile-order-detail-button" data-profile-order-details="${escapeHTML(String(order.order_number))}" type="button" aria-expanded="false"><span aria-hidden="true">⌄</span><span class="profile-order-detail-label">${escapeHTML(tr("profileOrderDetails"))}</span></button><button class="order-reorder profile-order-reorder" data-profile-reorder="${escapeHTML(String(order.order_number))}" type="button" title="${escapeHTML(tr("reorderHint"))}"><span aria-hidden="true">↻</span><span>${escapeHTML(tr("reorder"))}</span></button></div></footer><div class="profile-order-detail-slot" hidden></div></article>`;
  }).join("");
  list.querySelectorAll("[data-profile-order-details]").forEach((button) => button.addEventListener("click", async () => {
    const card = button.closest(".profile-order-card");
    const slot = card.querySelector(".profile-order-detail-slot");
    const label = button.querySelector(".profile-order-detail-label");
    if (!slot.hidden) { slot.hidden = true; button.setAttribute("aria-expanded", "false"); label.textContent = tr("profileOrderDetails"); return; }
    slot.hidden = false;
    slot.innerHTML = `<div class="drawer-loading"><span class="loader"></span></div>`;
    button.disabled = true;
    try { renderProfileOrderDetail(slot, await request(`orders/${encodeURIComponent(button.dataset.profileOrderDetails)}/`)); button.setAttribute("aria-expanded", "true"); label.textContent = tr("hideDetails"); } catch (error) { slot.innerHTML = `<p class="field-error">${escapeHTML(error.message || tr("operationFailed"))}</p>`; } finally { button.disabled = false; }
  }));
  list.querySelectorAll("[data-profile-reorder]").forEach((button) => button.addEventListener("click", () => reorderProfileOrder(button.dataset.profileReorder, button)));
}
async function reorderProfileOrder(orderNumber, button) {
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}orders/${encodeURIComponent(orderNumber)}/reorder/`, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": await csrf() } });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) { window.location.href = `/account/?next=${encodeURIComponent(window.location.pathname)}`; return; }
    if (!response.ok) throw Object.assign(new Error(data.detail || tr("reorderFailed")), { status: response.status });
    const addedCount = (data.added || []).reduce((total, item) => total + Number(item.quantity || 0), 0);
    const skippedCount = (data.skipped || []).length;
    const notice = skippedCount ? formatMessage("reorderPartial", { added: localizedNumber(addedCount), skipped: localizedNumber(skippedCount) }) : formatMessage("reorderSuccess", { count: localizedNumber(addedCount) });
    sessionStorage.setItem("nexora-toast", notice);
    window.location.href = "/?cart=open";
  } catch (error) { message(error.message || tr("reorderFailed")); button.disabled = false; }
}
async function loadOrders() { try { const data = await request("orders/?page_size=100"); state.orders = data.results || data; renderOrders(); updateProfileStats(); } catch (error) { message(error.message); } }

document.querySelectorAll(".profile-nav button").forEach((button) => {
  button.addEventListener("click", () => openSection(button.dataset.section));
  button.addEventListener("keydown", (event) => {
    const buttons = [...document.querySelectorAll(".profile-nav button")];
    const index = buttons.indexOf(button);
    const forwardKey = document.documentElement.dir === "rtl" ? "ArrowLeft" : "ArrowRight";
    const backwardKey = document.documentElement.dir === "rtl" ? "ArrowRight" : "ArrowLeft";
    const nextIndex = event.key === "ArrowDown" || event.key === forwardKey
      ? (index + 1) % buttons.length
      : event.key === "ArrowUp" || event.key === backwardKey
        ? (index - 1 + buttons.length) % buttons.length
        : event.key === "Home"
          ? 0
          : event.key === "End"
            ? buttons.length - 1
            : -1;
    if (nextIndex < 0) return;
    event.preventDefault();
    buttons[nextIndex].focus();
    openSection(buttons[nextIndex].dataset.section);
  });
});
document.querySelectorAll("[data-profile-shortcut]").forEach((button) => button.addEventListener("click", () => { openSection(button.dataset.profileShortcut); document.querySelector(".profile-main")?.scrollIntoView({ behavior: "smooth", block: "start" }); }));
document.querySelector("#new-address").addEventListener("click", () => { const form = document.querySelector("#profile-address-form"); resetAddressForm(); form.hidden = false; form.scrollIntoView({ behavior: "smooth", block: "center" }); });
document.querySelector("#cancel-profile-address").addEventListener("click", resetAddressForm);
document.querySelector("#profile-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form)); payload.phone_number = digits(payload.phone_number).replace(/[\s-]/g, ""); try { const profile = await request("auth/profile/", { method: "PATCH", body: JSON.stringify(payload) }); state.profile = profile; renderProfile(profile); message(tr("profileSaved"), true); } catch (error) { if (!showErrors(form, error.data)) message(error.message); } });
document.querySelector("#profile-address-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; clearErrors(form); const payload = Object.fromEntries(new FormData(form)); ["title", "province", "city", "address_line", "recipient_name", "recipient_phone"].forEach((field) => { payload[field] = normalizeText(payload[field]); }); payload.postal_code = digits(payload.postal_code).replace(/[\s-]/g, ""); payload.recipient_phone = digits(payload.recipient_phone).replace(/[\s-]/g, ""); payload.is_default = state.addresses.length === 0; const addressId = form.dataset.addressId; const submit = form.querySelector("button[type=submit]"); submit.disabled = true; try { const address = await request(addressId ? `auth/addresses/${addressId}/` : "auth/addresses/", { method: addressId ? "PATCH" : "POST", body: JSON.stringify(payload) }); state.addresses = addressId ? state.addresses.map((item) => item.id === Number(addressId) ? address : item) : [address, ...state.addresses]; renderAddresses(); resetAddressForm(); message(tr("addressSaved"), true); } catch (error) { if (!showErrors(form, error.data)) message(error.message); } finally { submit.disabled = false; } });
document.querySelector("#password-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form)); try { await request("auth/password/change/", { method: "POST", body: JSON.stringify(payload) }); form.reset(); message(tr("passwordChanged"), true); } catch (error) { if (!showErrors(form, error.data)) message(error.message); } });
document.querySelector("#delete-account-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; if (!window.confirm(tr("deleteAccountFinalConfirm"))) return; const button = form.querySelector("button[type=submit]"); const payload = Object.fromEntries(new FormData(form)); payload.confirm = form.elements.confirm.checked; button.disabled = true; try { await request("auth/profile/", { method: "DELETE", body: JSON.stringify(payload) }); window.NexoraCartNav?.renderCount(0); window.NexoraFavorites?.sync([]); window.dispatchEvent(new CustomEvent("nexora-logged-out")); window.location.href = "/?account_deleted=1"; } catch (error) { if (!showErrors(form, error.data)) message(error.message); button.disabled = false; } });
async function load() { try { state.profile = await request("auth/profile/"); renderProfile(state.profile); await loadAddresses(); await loadWatches(); await loadRewards(); } catch (error) { if (error.status === 401) window.location.href = "/account/?next=/profile/"; else message(error.message); } }
const initialSection = new URLSearchParams(window.location.search).get("section") || window.location.hash.slice(1) || "personal";
document.addEventListener("nexora-favorite-changed", (event) => {
  const detail = event.detail || {};
  const productId = Number(detail.productId);
  const index = state.favorites.findIndex((product) => Number(product.id) === productId);
  if (detail.isFavorite && index === -1 && detail.favorite?.product) state.favorites = [detail.favorite.product, ...state.favorites];
  if (!detail.isFavorite) state.favorites = state.favorites.filter((product) => Number(product.id) !== productId);
  updateProfileStats();
  if (document.querySelector('[data-panel="favorites"]')?.classList.contains("active")) renderFavorites();
});
window.addEventListener("nexora-language-changed", () => { if (state.profile) renderProfile(state.profile); if (state.addresses.length) renderAddresses(); if (state.orders.length) renderOrders(); if (state.favorites.length) renderFavorites(); if (state.watchesLoaded) renderWatches(); if (state.rewardsLoaded) renderRewards(); renderProfileCompletion(); });
setupTheme();
openSection(PROFILE_SECTIONS.includes(initialSection) ? initialSection : "personal", { persist: false });
window.addEventListener("popstate", () => {
  const section = new URLSearchParams(window.location.search).get("section") || "personal";
  openSection(PROFILE_SECTIONS.includes(section) ? section : "personal", { persist: false });
});
load();
