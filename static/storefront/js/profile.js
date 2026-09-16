const API_BASE = "/api/v1/";
const tr = (key) => window.NexoraI18n?.t(key) || key;
const formatMessage = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, value), tr(key));
const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const localizedNumber = (value) => new Intl.NumberFormat(document.documentElement.lang === "en" ? "en-US" : "fa-IR").format(value);
const money = (value) => `${localizedNumber(Math.round(Number(value)))} ${tr("toman")}`;
const digits = (value) => String(value ?? "").replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d));
const normalizeText = (value) => String(value ?? "").normalize("NFC").replace(/[يى]/g, "ی").replace(/ك/g, "ک").replace(/\s+/g, " ").trim();
const state = { profile: null, addresses: [], orders: [], favorites: [], watches: [], watchesLoaded: false };

const roleTranslationKey = { product_manager: "roleProductManager", supervisor: "roleSupervisor", operator: "roleOperator" };

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
  const image = product.image_url
    ? "<img src=\"" + escapeHTML(product.image_url) + "\" alt=\"" + escapeHTML(name) + "\" loading=\"lazy\">"
    : "<span class=\"favorite-placeholder\">" + escapeHTML((product.brand || "N").slice(0, 1)) + "</span>";
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
function updateProfileStats() {
  const values = {
    "#profile-orders-count": state.orders.length,
    "#profile-addresses-count": state.addresses.length,
    "#profile-favorites-count": state.favorites.length,
    "#profile-watches-count": state.watches.length,
  };
  Object.entries(values).forEach(([selector, value]) => {
    const element = document.querySelector(selector);
    if (element) element.textContent = localizedNumber(value);
  });
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

async function loadFavorites() {
  try {
    const favorites = await (window.NexoraFavorites?.refresh ? window.NexoraFavorites.refresh() : window.NexoraFavorites?.load());
    state.favorites = (favorites || []).map((item) => item.product).filter(Boolean);
    renderFavorites();
  } catch (error) { message(error.message); }
}
function openSection(name) { document.querySelectorAll(".profile-nav button").forEach((button) => button.classList.toggle("selected", button.dataset.section === name)); document.querySelectorAll(".profile-section").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === name)); if (name === "addresses") loadAddresses(); if (name === "orders") loadOrders(); if (name === "favorites") loadFavorites(); if (name === "watches") loadWatches(); }
function renderProfile(profile) { Object.entries(profile).forEach(([key, value]) => { const input = document.querySelector(`[name="${key}"]`); if (input) input.value = value || ""; }); const name = `${profile.first_name || ""} ${profile.last_name || ""}`.trim() || profile.username; const roleKey = roleTranslationKey[profile.role] || "normalCustomer"; const roleLabel = tr(roleKey); const profileName = document.querySelector("#profile-name"); const profileEmail = document.querySelector("#profile-email"); const avatar = document.querySelector("#profile-avatar"); const role = document.querySelector("#profile-role"); const roleHint = document.querySelector("#profile-role-hint"); const verified = document.querySelector("#profile-verified"); const emailHint = document.querySelector("#profile-email-hint"); if (profileName) profileName.textContent = name; if (profileEmail) profileEmail.textContent = profile.email || ""; if (avatar) avatar.textContent = (name || "N").slice(0, 1).toUpperCase(); if (role) { role.textContent = roleLabel; role.classList.toggle("is-staff", Boolean(profile.role)); } if (roleHint) roleHint.textContent = roleLabel; if (verified) { verified.textContent = profile.email_verified ? `✓ ${tr("emailVerified")}` : `! ${tr("emailNotVerified")}`; verified.classList.toggle("is-warning", !profile.email_verified); } if (emailHint) emailHint.textContent = profile.email_verified ? tr("emailVerified") : tr("emailNotVerified"); }
function resetAddressForm() { const form = document.querySelector("#profile-address-form"); form.reset(); form.hidden = true; form.dataset.addressId = ""; form.classList.remove("editing"); document.querySelector("#profile-address-title").textContent = tr("addNewAddress"); clearErrors(form); }
function renderAddresses() { const list = document.querySelector("#profile-addresses"); if (!state.addresses.length) { list.innerHTML = `<div class="empty-inline">${tr("noSavedAddress")}</div>`; return; } list.innerHTML = state.addresses.map((address) => `<article class="profile-address-card"><div><strong>${escapeHTML(address.title)} ${address.is_default ? `<small class="default-badge">${tr("defaultAddress")}</small>` : ""}</strong><p>${escapeHTML(address.province)}، ${escapeHTML(address.city)}، ${escapeHTML(address.address_line)}</p><small>${escapeHTML(address.recipient_name)} · ${escapeHTML(address.recipient_phone)} · ${escapeHTML(address.postal_code)}</small></div><div class="address-actions"><button class="address-action" data-action="edit" data-id="${address.id}" type="button">${tr("editAddress")}</button><button class="address-action delete" data-action="delete" data-id="${address.id}" type="button">${tr("remove")}</button></div></article>`).join(""); list.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => { const address = state.addresses.find((item) => item.id === Number(button.dataset.id)); button.dataset.action === "edit" ? beginAddressEdit(address) : deleteAddress(address); })); }
function beginAddressEdit(address) { const form = document.querySelector("#profile-address-form"); form.hidden = false; form.dataset.addressId = address.id; form.classList.add("editing"); document.querySelector("#profile-address-title").textContent = tr("editAddress"); Object.entries(address).forEach(([key, value]) => { const input = form.querySelector(`[name="${key}"]`); if (input) input.value = value || ""; }); form.scrollIntoView({ behavior: "smooth", block: "center" }); }
async function deleteAddress(address) { if (!window.confirm(formatMessage("addressDeleteConfirm", { title: address.title }))) return; try { await request(`auth/addresses/${address.id}/`, { method: "DELETE" }); state.addresses = state.addresses.filter((item) => item.id !== address.id); renderAddresses(); message(tr("addressRemoved"), true); } catch (error) { message(error.message); } }
async function loadAddresses() { try { const data = await request("auth/addresses/"); state.addresses = data.results || data; renderAddresses(); updateProfileStats(); } catch (error) { if (error.status === 401) window.location.href = "/account/?next=/profile/"; else message(error.message); } }
function renderOrders() { const list = document.querySelector("#profile-orders"); if (!state.orders.length) { list.innerHTML = `<div class="empty-inline">${tr("noOrders")}</div>`; return; } list.innerHTML = state.orders.map((order) => `<article class="profile-order"><div><strong>${formatMessage("orderLabel", { number: escapeHTML(String(order.order_number).slice(0, 8).toUpperCase()) })}</strong><small>${new Date(order.created_at).toLocaleDateString(document.documentElement.lang === "en" ? "en-US" : "fa-IR")}</small></div><div><strong>${money(order.total_amount)}</strong><small>${tr(order.status || "")}</small></div></article>`).join(""); }
async function loadOrders() { try { const data = await request("orders/?page_size=100"); state.orders = data.results || data; renderOrders(); updateProfileStats(); } catch (error) { message(error.message); } }

document.querySelectorAll(".profile-nav button").forEach((button) => button.addEventListener("click", () => openSection(button.dataset.section)));
document.querySelector("#new-address").addEventListener("click", () => { const form = document.querySelector("#profile-address-form"); resetAddressForm(); form.hidden = false; form.scrollIntoView({ behavior: "smooth", block: "center" }); });
document.querySelector("#cancel-profile-address").addEventListener("click", resetAddressForm);
document.querySelector("#profile-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form)); payload.phone_number = digits(payload.phone_number).replace(/[\s-]/g, ""); try { const profile = await request("auth/profile/", { method: "PATCH", body: JSON.stringify(payload) }); state.profile = profile; renderProfile(profile); message(tr("profileSaved"), true); } catch (error) { if (!showErrors(form, error.data)) message(error.message); } });
document.querySelector("#profile-address-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; clearErrors(form); const payload = Object.fromEntries(new FormData(form)); ["title", "province", "city", "address_line", "recipient_name", "recipient_phone"].forEach((field) => { payload[field] = normalizeText(payload[field]); }); payload.postal_code = digits(payload.postal_code).replace(/[\s-]/g, ""); payload.recipient_phone = digits(payload.recipient_phone).replace(/[\s-]/g, ""); payload.is_default = state.addresses.length === 0; const addressId = form.dataset.addressId; const submit = form.querySelector("button[type=submit]"); submit.disabled = true; try { const address = await request(addressId ? `auth/addresses/${addressId}/` : "auth/addresses/", { method: addressId ? "PATCH" : "POST", body: JSON.stringify(payload) }); state.addresses = addressId ? state.addresses.map((item) => item.id === Number(addressId) ? address : item) : [address, ...state.addresses]; renderAddresses(); resetAddressForm(); message(tr("addressSaved"), true); } catch (error) { if (!showErrors(form, error.data)) message(error.message); } finally { submit.disabled = false; } });
document.querySelector("#password-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form)); try { await request("auth/password/change/", { method: "POST", body: JSON.stringify(payload) }); form.reset(); message(tr("passwordChanged"), true); } catch (error) { if (!showErrors(form, error.data)) message(error.message); } });
async function load() { try { state.profile = await request("auth/profile/"); renderProfile(state.profile); await loadAddresses(); await loadWatches(); } catch (error) { if (error.status === 401) window.location.href = "/account/?next=/profile/"; else message(error.message); } }
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
window.addEventListener("nexora-language-changed", () => { if (state.profile) renderProfile(state.profile); if (state.addresses.length) renderAddresses(); if (state.orders.length) renderOrders(); if (state.favorites.length) renderFavorites(); if (state.watchesLoaded) renderWatches(); });
setupTheme(); openSection(["personal", "addresses", "orders", "favorites", "watches", "security"].includes(initialSection) ? initialSection : "personal"); load();
