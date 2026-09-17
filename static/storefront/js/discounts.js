const API_BASE = "/api/v1/";
const tr = (key) => window.NexoraI18n?.t(key) || key;
const currentLocale = () => document.documentElement.lang === "en" ? "en-US" : "fa-IR";
const number = (value) => new Intl.NumberFormat(currentLocale()).format(Number(value) || 0);
const money = (value) => `${number(Math.round(Number(value) || 0))} ${tr("toman")}`;
const escapeHTML = (value) => String(value ?? "").replace(/[&<>\'\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
const formatMessage = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, value), tr(key));

let products = [];
let sort = "saving";

function productName(product) {
  return window.NexoraI18n?.productName(product) || product.name || tr("product");
}

function productCategory(product) {
  if (!product.category) return tr("digitalAccessories");
  return window.NexoraI18n?.category(product.category.slug, product.category.name) || product.category.name;
}

function placeholderIcon(slug) {
  return { "cables-charging": "⌁", gaming: "◈", audio: "◒", "keyboards-mice": "⌘" }[slug] || "N";
}

function productImage(product, name) {
  if (product.image_url) {
    return `<img src="${escapeHTML(product.image_url)}" alt="${escapeHTML(name)}" loading="lazy" onerror="this.closest('.product-visual')?.classList.add('image-failed'); this.remove();">`;
  }
  return `<div class="product-placeholder placeholder-${escapeHTML(product.category?.slug || "accessories")}"><span>${escapeHTML(placeholderIcon(product.category?.slug))}</span><small>NEXORA</small></div>`;
}

function discountAmount(product) {
  return Number(product.discount_amount || 0);
}

function discountRatio(product) {
  const price = Number(product.price || 0);
  return price > 0 ? discountAmount(product) / price : 0;
}

function discountLabel(product) {
  const amount = discountAmount(product);
  if (!amount) return "";
  if (product.discount_type === "percentage" && product.discount_value !== null && product.discount_value !== undefined) {
    return formatMessage("discountPercent", { percent: number(product.discount_value) });
  }
  return formatMessage("discountAmount", { amount: money(amount) });
}

function countdownMarkup(product) {
  const timestamp = Date.parse(product.discount_ends_at || "");
  if (!Number.isFinite(timestamp) || !discountAmount(product)) return "";
  return `<small class="discount-countdown" data-discount-countdown="${timestamp}"><span aria-hidden="true">◷</span><span></span></small>`;
}

function countdownText(milliseconds) {
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  const values = [
    ["countdownDay", Math.floor(seconds / 86400)],
    ["countdownHour", Math.floor((seconds % 86400) / 3600)],
    ["countdownMinute", Math.floor((seconds % 3600) / 60)],
    ["countdownSecond", seconds % 60],
  ].filter(([, value]) => value > 0).slice(0, 2);
  if (!values.length) values.push(["countdownSecond", 0]);
  return values.map(([key, value]) => `${number(value)} ${tr(key)}`).join(" ");
}

function updateCountdowns() {
  document.querySelectorAll("[data-discount-countdown]").forEach((element) => {
    const remaining = Number(element.dataset.discountCountdown) - Date.now();
    if (remaining <= 0) {
      element.classList.add("expired");
      element.innerHTML = `<span aria-hidden="true">!</span><span>${escapeHTML(tr("discountEnded"))}</span>`;
      return;
    }
    element.classList.remove("expired");
    element.innerHTML = `<span aria-hidden="true">◷</span><span>${escapeHTML(formatMessage("discountEndsIn", { time: countdownText(remaining) }))}</span>`;
  });
}

function productRating(product) {
  const count = Number(product.rating_count || 0);
  if (!count) return "";
  return `<span class="product-rating-mini">★ ${escapeHTML(number(Number(product.rating_average || 0)))} <small>(${escapeHTML(number(count))})</small></span>`;
}

function productCard(product, index) {
  const name = productName(product);
  const href = `/products/${encodeURIComponent(product.slug)}/`;
  const label = discountLabel(product);
  const amount = discountAmount(product);
  const saving = formatMessage("youSave", { amount: money(amount) });
  return `<article class="product-card discount-product-card" style="--delay:${index * 55}ms">
    <div class="product-visual"><a class="discount-product-image-link" href="${escapeHTML(href)}" aria-label="${escapeHTML(name)}">${productImage(product, name)}</a><span class="discount-badge">${escapeHTML(label)}</span><span class="stock-badge ${product.is_in_stock ? "" : "out-of-stock"}">${escapeHTML(product.is_in_stock ? tr("available") : tr("unavailable"))}</span><button class="heart-button" data-favorite-product="${product.id}" type="button" aria-label="${escapeHTML(tr("addToFavorites"))}">♡</button></div>
    <div class="product-info"><div class="product-card-meta"><p class="product-category">${escapeHTML(productCategory(product))}</p>${productRating(product)}</div><h3><a class="product-title-link" href="${escapeHTML(href)}">${escapeHTML(name)}</a></h3><div class="product-bottom"><div class="price-stack"><strong>${escapeHTML(money(product.final_price))}</strong><del>${escapeHTML(money(product.price))}</del><small class="product-savings"><span aria-hidden="true">✦</span>${escapeHTML(saving)}</small>${countdownMarkup(product)}</div><button class="add-button cart-icon-button discount-add-button" data-product="${product.id}" type="button" aria-label="${escapeHTML(tr("addToCart"))}" title="${escapeHTML(tr("addToCart"))}" ${product.is_in_stock ? "" : "disabled"}><span data-discount-cart-icon aria-hidden="true">🛒</span></button></div></div>
  </article>`;
}

function sortedProducts() {
  return [...products].sort((first, second) => {
    if (sort === "ending") {
      const firstEnd = Date.parse(first.discount_ends_at || "") || Number.MAX_SAFE_INTEGER;
      const secondEnd = Date.parse(second.discount_ends_at || "") || Number.MAX_SAFE_INTEGER;
      return firstEnd - secondEnd || discountRatio(second) - discountRatio(first);
    }
    if (sort === "price") return Number(first.final_price) - Number(second.final_price);
    if (sort === "newest") return new Date(second.created_at || 0) - new Date(first.created_at || 0);
    return discountRatio(second) - discountRatio(first) || discountAmount(second) - discountAmount(first);
  });
}

function updateOverview() {
  const bestRatio = products.reduce((best, product) => Math.max(best, discountRatio(product)), 0);
  const available = products.filter((product) => product.is_in_stock).length;
  document.querySelector("#discounts-count").textContent = number(products.length);
  document.querySelector("#discounts-best-saving").textContent = `${number(Math.round(bestRatio * 100))}%`;
  document.querySelector("#discounts-in-stock").textContent = number(available);
}

function bindProductActions() {
  const grid = document.querySelector("#discount-grid");
  window.NexoraFavorites?.bindButtons(grid);
  grid.querySelectorAll(".discount-add-button").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    button.classList.add("is-loading");
    try {
      await sendJSON("cart/items/", "POST", { product_id: button.dataset.product, quantity: 1 });
      const icon = button.querySelector("[data-discount-cart-icon]");
      if (icon) icon.textContent = "✓";
      await loadCartCount();
      showToast(tr("addedToCart"));
      window.setTimeout(() => { if (icon) icon.textContent = "🛒"; }, 900);
    } catch (error) {
      showToast(error.message || tr("operationFailed"));
    } finally {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }));
  grid.querySelectorAll(".product-card").forEach((card) => card.addEventListener("click", (event) => {
    if (event.target.closest("button, a")) return;
    window.location.href = card.querySelector(".product-title-link")?.getAttribute("href") || "/";
  }));
}

function render() {
  const state = document.querySelector("#discounts-state");
  const grid = document.querySelector("#discount-grid");
  if (!state || !grid) return;
  updateOverview();
  if (!products.length) {
    state.hidden = false;
    state.innerHTML = `<span class="state-icon">%</span><h3>${escapeHTML(tr("discountsEmpty"))}</h3><p>${escapeHTML(tr("discountsEmptyHint"))}</p><a class="primary-button" href="/">${escapeHTML(tr("browseProducts"))}<span aria-hidden="true">←</span></a>`;
    grid.hidden = true;
    return;
  }
  state.hidden = true;
  grid.hidden = false;
  grid.innerHTML = sortedProducts().map(productCard).join("");
  bindProductActions();
  updateCountdowns();
}

async function getJSON(path) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || tr("storefrontConnectionFailed"));
  return data;
}

function getCookie(name) {
  const cookie = (document.cookie ? document.cookie.split("; ") : []).find((value) => value.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null;
}

async function csrf() {
  const existing = getCookie("csrftoken");
  if (existing) return existing;
  const response = await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" });
  if (!response.ok || !getCookie("csrftoken")) throw new Error(tr("securityTokenFailed"));
  return getCookie("csrftoken");
}

async function sendJSON(path, method, body) {
  const response = await fetch(`${API_BASE}${path}`, { method, credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": await csrf() }, body: JSON.stringify(body) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.product_id?.[0] || tr("operationFailed"));
  return data;
}

async function loadCartCount() {
  try {
    const cart = await getJSON("cart/");
    document.querySelector("#discount-cart-count").textContent = number(cart.item_count || 0);
  } catch (error) {
    // The discount shelf remains usable when cart state is temporarily unavailable.
  }
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast-message";
  toast.textContent = message;
  document.body.appendChild(toast);
  window.setTimeout(() => toast.remove(), 2800);
}

async function loadDiscounts() {
  try {
    const data = await getJSON("products/?has_discount=true&page_size=100");
    products = data.results || data || [];
    render();
  } catch (error) {
    const state = document.querySelector("#discounts-state");
    state.innerHTML = `<span class="state-icon">!</span><h3>${escapeHTML(tr("discountsLoadFailed"))}</h3><p>${escapeHTML(error.message || tr("retry"))}</p><button class="retry-button" type="button" id="discounts-retry">${escapeHTML(tr("tryAgain"))}</button>`;
    document.querySelector("#discounts-retry")?.addEventListener("click", loadDiscounts, { once: true });
  }
}

document.querySelector("#discount-sort")?.addEventListener("change", (event) => {
  sort = event.target.value;
  render();
});
window.addEventListener("nexora-language-changed", () => { render(); loadCartCount(); });
window.setInterval(updateCountdowns, 1000);
loadCartCount();
loadDiscounts();
