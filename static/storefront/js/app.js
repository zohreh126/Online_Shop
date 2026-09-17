const API_BASE = "/api/v1/";
const state = { products: [], categories: [], category: "", search: "", sort: "newest", onlyDiscounted: false, onlyInStock: false, priceBand: "all" };
const expandedCategorySlugs = new Set();
const COMPARE_STORAGE_KEY = "nexora-compare";
const RECENT_STORAGE_KEY = "nexora-recently-viewed";
const FREE_SHIPPING_THRESHOLD = 2000000;
const compareIds = new Set();

const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const localizedNumber = (value) => new Intl.NumberFormat(window.NexoraI18n?.current() === "en" ? "en-US" : "fa-IR").format(value);
const money = (value) => window.NexoraI18n?.current() === "en" ? `${new Intl.NumberFormat("en-US").format(Math.round(Number(value)))} toman` : `${faNumber(Math.round(Number(value)))} تومان`;
const latinNumber = (value) => String(value).replace(/[۰-۹]/g, (digit) => "۰۱۲۳۴۵۶۷۸۹".indexOf(digit));
const t = (key) => window.NexoraI18n?.t(key) || key;
const formatMessage = (key, values = {}) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, value), t(key));
const escapeHTML = (value) => String(value ?? "").replace(/[&<>\'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));

try {
  const storedCompareIds = JSON.parse(localStorage.getItem(COMPARE_STORAGE_KEY) || "[]");
  if (Array.isArray(storedCompareIds)) storedCompareIds.slice(0, 3).forEach((id) => { if (Number(id)) compareIds.add(Number(id)); });
} catch (error) {
  // Local storage can be disabled by the browser; comparison still works for this visit.
}

async function getJSON(path) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  if (!response.ok) throw new Error("API request failed");
  return response.json();
}

async function loadAccountState() {
  const account = document.querySelector("#account-area");
  try {
    const profile = await getJSON("auth/profile/");
    account.innerHTML = `<a class="account-name" href="/dashboard/">${profile.first_name || profile.username}</a><button class="account-link account-logout" id="account-logout" type="button">${t("logout")}</button>`;
    document.querySelector("#account-logout").addEventListener("click", async () => {
      try {
        await sendJSON("auth/logout/", "POST");
        account.innerHTML = '<a class="account-link" href="/account/">ورود</a>';
        showToast(t("loggedOut"));
      } catch (error) { showToast(error.message); }
    });
  } catch (error) {
    account.innerHTML = `<a class="account-link" href="/account/">${t("login")}</a>`;
  }
}

function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split("; ") : [];
  const cookie = cookies.find((value) => value.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null;
}

async function ensureCSRFToken() {
  const existingToken = getCookie("csrftoken");
  if (existingToken) return existingToken;

  const response = await fetch(`${API_BASE}auth/csrf/`, {
    credentials: "same-origin",
  });
  if (!response.ok) throw new Error("توکن امنیتی درخواست دریافت نشد.");

  const token = getCookie("csrftoken");
  if (!token) throw new Error("توکن امنیتی درخواست دریافت نشد.");
  return token;
}

async function sendJSON(path, method, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": await ensureCSRFToken(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.quantity?.[0] || data.product_id?.[0] || "عملیات سبد انجام نشد.");
  return data;
}

function productImage(product) {
  if (product.image_url) {
    const alt = formatMessage("productImageAlt", { name: productName(product) });
    return `<img src="${escapeHTML(product.image_url)}" alt="${escapeHTML(alt)}" loading="lazy" onerror="this.closest('.product-visual').classList.add('image-failed'); this.remove();">`;
  }
  const categorySlug = product.category?.slug || "accessories";
  return `<div class="product-placeholder placeholder-${categorySlug}"><span>${placeholderIcon(categorySlug)}</span><small>${categoryLabel(categorySlug)}</small></div>`;
}

function placeholderIcon(categorySlug) {
  const icons = { "cables-charging": "⌁", gaming: "◈", accessories: "N", audio: "◒", "keyboards-mice": "⌘" };
  return icons[categorySlug] || "N";
}

function categoryLabel(categorySlug) {
  const labels = { "cables-charging": "CONNECT", gaming: "PLAY", accessories: "NEXORA", audio: "AUDIO", "keyboards-mice": "DESK" };
  return labels[categorySlug] || "NEXORA";
}

function categoryName(category) {
  return window.NexoraI18n?.category(category.slug, category.name) || category.name;
}

function productName(product) {
  return window.NexoraI18n?.productName(product) || product.name;
}

function productRating(product) {
  const count = Number(product.rating_count || 0);
  if (!count) return "";
  const average = Number(product.rating_average || 0);
  const label = formatMessage("reviewCount", { count: localizedNumber(count) });
  return `<span class="product-rating-mini" title="${escapeHTML(label)}">★ ${escapeHTML(localizedNumber(average))} <small>(${escapeHTML(localizedNumber(count))})</small></span>`;
}

function discountLabel(product) {
  const amount = Number(product.discount_amount || 0);
  if (!amount) return "";
  if (product.discount_type === "percentage" && product.discount_value !== null && product.discount_value !== undefined) {
    return formatMessage("discountPercent", { percent: localizedNumber(Number(product.discount_value)) });
  }
  return formatMessage("discountAmount", { amount: money(amount) });
}

function discountSavingsMarkup(product) {
  const amount = Number(product.discount_amount || 0);
  if (!amount) return "";
  return `<small class="product-savings"><span aria-hidden="true">✦</span>${escapeHTML(formatMessage("youSave", { amount: money(amount) }))}</small>`;
}

function discountEndsTimestamp(product) {
  const timestamp = Date.parse(product.discount_ends_at || "");
  return Number.isFinite(timestamp) && timestamp > 0 ? timestamp : 0;
}

function discountCountdownMarkup(product) {
  const endsAt = discountEndsTimestamp(product);
  if (!endsAt || Number(product.discount_amount || 0) <= 0) return "";
  return `<small class="discount-countdown" data-discount-countdown="${endsAt}"><span aria-hidden="true">◷</span><span></span></small>`;
}

function discountCountdownText(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const values = [
    ["countdownDay", Math.floor(totalSeconds / 86400)],
    ["countdownHour", Math.floor((totalSeconds % 86400) / 3600)],
    ["countdownMinute", Math.floor((totalSeconds % 3600) / 60)],
    ["countdownSecond", totalSeconds % 60],
  ].filter(([, value]) => value > 0).slice(0, 2);
  if (!values.length) values.push(["countdownSecond", 0]);
  return values.map(([label, value]) => `${localizedNumber(value)} ${t(label)}`).join(" ");
}

function updateDiscountCountdowns() {
  document.querySelectorAll("[data-discount-countdown]").forEach((element) => {
    const remaining = Number(element.dataset.discountCountdown) - Date.now();
    if (remaining <= 0) {
      element.classList.add("expired");
      element.innerHTML = `<span aria-hidden="true">!</span><span>${escapeHTML(t("discountEnded"))}</span>`;
      return;
    }
    element.classList.remove("expired");
    element.innerHTML = `<span aria-hidden="true">◷</span><span>${escapeHTML(formatMessage("discountEndsIn", { time: discountCountdownText(remaining) }))}</span>`;
  });
}

function productCardMarkup(product, index = 0, compact = false) {
  const name = productName(product);
  const url = `/products/${encodeURIComponent(product.slug)}/`;
  const discount = discountLabel(product);
  const discountAmount = Number(product.discount_amount || 0);
  const addLabel = t("addToCart");
  return `<article class="product-card${compact ? " recent-product-card" : ""}" style="--delay:${index * 60}ms"><div class="product-visual">${productImage(product)}${discount ? `<span class="discount-badge">${escapeHTML(discount)}</span>` : ""}<span class="stock-badge ${product.is_in_stock ? "" : "out-of-stock"}">${escapeHTML(product.is_in_stock ? t("available") : t("unavailable"))}</span><button class="heart-button" aria-label="${escapeHTML(t("addToFavorites"))}" type="button">♡</button></div><div class="product-info"><div class="product-card-meta"><p class="product-category">${escapeHTML(product.category ? categoryName(product.category) : t("digitalAccessories"))}</p><div class="product-card-meta-actions">${productRating(product)}<button class="compare-button" data-compare-product="${product.id}" type="button" aria-pressed="false"><span aria-hidden="true">⇄</span><span>${escapeHTML(t("compare"))}</span></button></div></div><h3><a class="product-title-link" href="${url}">${escapeHTML(name)}</a></h3><div class="product-bottom"><div class="price-stack"><strong>${escapeHTML(money(product.final_price))}</strong>${discountAmount > 0 ? `<del>${escapeHTML(money(product.price))}</del>${discountSavingsMarkup(product)}${discountCountdownMarkup(product)}` : ""}</div><button class="add-button cart-icon-button" data-product="${product.id}" aria-label="${escapeHTML(addLabel)}" title="${escapeHTML(addLabel)}" type="button" ${product.is_in_stock ? "" : "disabled"}><span data-cart-icon aria-hidden="true">${product.is_in_stock ? "🛒" : "−"}</span></button></div></div></article>`;
}

function bindProductActions(container, products) {
  container.querySelectorAll(".heart-button").forEach((button, index) => {
    button.dataset.favoriteProduct = products[index].id;
    button.setAttribute("aria-pressed", "false");
  });
  window.NexoraFavorites?.bindButtons(container);
  container.querySelectorAll(".compare-button").forEach((button) => button.addEventListener("click", (event) => { event.preventDefault(); event.stopPropagation(); toggleCompare(button.dataset.compareProduct); }));
  container.querySelectorAll(".add-button").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    button.classList.add("is-loading");
    try {
      await sendJSON("cart/items/", "POST", { product_id: button.dataset.product, quantity: 1 });
      await refreshCart();
      const icon = button.querySelector("[data-cart-icon]");
      if (icon) icon.textContent = "✓";
      showToast(t("addedToCart"));
      setTimeout(() => { if (icon) icon.textContent = "🛒"; }, 900);
    } catch (error) {
      showToast(error.message);
    } finally {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }));
  container.querySelectorAll(".product-card").forEach((card) => card.addEventListener("click", (event) => {
    if (event.target.closest("button, a")) return;
    window.location.href = card.querySelector(".product-title-link")?.getAttribute("href") || "/";
  }));
}

function recentlyViewedEntries() {
  try {
    const entries = JSON.parse(localStorage.getItem(RECENT_STORAGE_KEY) || "[]");
    return Array.isArray(entries) ? entries : [];
  } catch (error) {
    return [];
  }
}

function renderRecentlyViewed() {
  const section = document.querySelector("#recently-viewed");
  const grid = document.querySelector("#recently-viewed-grid");
  if (!section || !grid || !state.products.length) return;

  const seen = new Set();
  const products = recentlyViewedEntries().map((entry) => {
    const id = typeof entry === "object" ? entry.id : entry;
    const entrySlug = typeof entry === "object" ? entry.slug : "";
    return state.products.find((product) => (id && Number(product.id) === Number(id)) || (entrySlug && product.slug === entrySlug));
  }).filter((product) => {
    if (!product || seen.has(product.id)) return false;
    seen.add(product.id);
    return true;
  }).slice(0, 4);

  section.hidden = !products.length;
  if (!products.length) return;
  grid.innerHTML = products.map((product, index) => productCardMarkup(product, index, true)).join("");
  bindProductActions(grid, products);
  updateDiscountCountdowns();
  updateCompareUI();
}

function persistCompareSelection() {
  try { localStorage.setItem(COMPARE_STORAGE_KEY, JSON.stringify([...compareIds])); } catch (error) { /* best effort */ }
}

function selectedCompareProducts() {
  return state.products.filter((product) => compareIds.has(Number(product.id)));
}

function syncCompareSelection() {
  if (!state.products.length) return;
  const availableIds = new Set(state.products.map((product) => Number(product.id)));
  let changed = false;
  [...compareIds].forEach((id) => {
    if (!availableIds.has(id)) { compareIds.delete(id); changed = true; }
  });
  if (changed) persistCompareSelection();
}

function compareSpecValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? t("yes") : t("no");
  return String(value);
}

function renderCompareModal() {
  const content = document.querySelector("#compare-content");
  if (!content) return;
  const selected = selectedCompareProducts();
  if (selected.length < 2) {
    content.innerHTML = `<div class="compare-empty"><span class="state-icon">⇄</span><h3>${escapeHTML(t("compareHint"))}</h3><p>${escapeHTML(t("compareEmptyHint"))}</p></div>`;
    return;
  }
  const rows = [
    [t("compareCategory"), selected.map((product) => product.category ? categoryName(product.category) : t("digitalAccessories"))],
    [t("compareBrand"), selected.map((product) => product.brand || "Nexora")],
    [t("comparePrice"), selected.map((product) => money(product.final_price))],
    [t("compareAvailability"), selected.map((product) => product.is_in_stock ? t("available") : t("unavailable"))],
    [t("compareDiscount"), selected.map((product) => Number(product.discount_amount) > 0 ? money(product.discount_amount) : "—")],
  ];
  const specificationKeys = [...new Set(selected.flatMap((product) => Object.keys(product.specifications || {})))].slice(0, 6);
  specificationKeys.forEach((key) => rows.push([window.NexoraI18n?.specificationLabel(key) || key, selected.map((product) => compareSpecValue(product.specifications?.[key]))]));
  content.innerHTML = `<div class="compare-table" style="--compare-columns:${selected.length}"><div class="compare-row compare-products-row"><strong class="compare-row-label">${escapeHTML(t("product"))}</strong>${selected.map((product) => {
    const name = productName(product);
    const image = product.image_url ? `<img src="${escapeHTML(product.image_url)}" alt="${escapeHTML(name)}" loading="lazy">` : `<span class="compare-placeholder">${escapeHTML((product.brand || "N").slice(0, 1))}</span>`;
    return `<article class="compare-product"><div class="compare-product-image">${image}</div><a href="/products/${encodeURIComponent(product.slug)}/">${escapeHTML(name)}</a><button class="quiet-link compare-remove" data-remove-compare="${product.id}" type="button">${escapeHTML(t("removeFromCompare"))}</button></article>`;
  }).join("")}</div>${rows.map(([label, values]) => `<div class="compare-row"><strong class="compare-row-label">${escapeHTML(label)}</strong>${values.map((value) => `<span>${escapeHTML(value)}</span>`).join("")}</div>`).join("")}</div>`;
  content.querySelectorAll("[data-remove-compare]").forEach((button) => button.addEventListener("click", () => toggleCompare(button.dataset.removeCompare)));
}

function updateCompareUI() {
  const bar = document.querySelector("#compare-bar");
  const count = document.querySelector("#compare-count");
  const chips = document.querySelector("#compare-chips");
  const openButton = document.querySelector("#compare-open");
  if (!bar || !count || !chips || !openButton) return;
  const selected = selectedCompareProducts();
  bar.hidden = !selected.length;
  count.textContent = localizedNumber(selected.length);
  chips.innerHTML = selected.map((product) => `<button class="compare-chip" data-remove-compare="${product.id}" type="button"><span>${escapeHTML(productName(product))}</span><b aria-hidden="true">×</b></button>`).join("");
  chips.querySelectorAll("[data-remove-compare]").forEach((button) => button.addEventListener("click", () => toggleCompare(button.dataset.removeCompare)));
  openButton.disabled = selected.length < 2;
  document.querySelectorAll("[data-compare-product]").forEach((button) => {
    const active = compareIds.has(Number(button.dataset.compareProduct));
    button.classList.toggle("is-selected", active);
    button.setAttribute("aria-pressed", String(active));
    button.disabled = !active && selected.length >= 3;
    button.innerHTML = `<span aria-hidden="true">${active ? "✓" : "⇄"}</span><span>${escapeHTML(t(active ? "removeFromCompare" : "compare"))}</span>`;
  });
  if (!document.querySelector("#compare-modal")?.hidden) renderCompareModal();
}

function toggleCompare(productId) {
  const numericProductId = Number(productId);
  if (!numericProductId) return;
  if (compareIds.has(numericProductId)) compareIds.delete(numericProductId);
  else if (compareIds.size >= 3) { showToast(t("compareLimit")); return; }
  else compareIds.add(numericProductId);
  persistCompareSelection();
  updateCompareUI();
}

function openCompare() {
  if (selectedCompareProducts().length < 2) { showToast(t("compareHint")); return; }
  renderCompareModal();
  const modal = document.querySelector("#compare-modal");
  modal.hidden = false;
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  document.querySelector("#compare-backdrop").hidden = false;
  document.body.classList.add("compare-open");
}

function closeCompare() {
  const modal = document.querySelector("#compare-modal");
  if (!modal) return;
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
  modal.hidden = true;
  document.querySelector("#compare-backdrop").hidden = true;
  document.body.classList.remove("compare-open");
}

function matchesPriceBand(product) {
  const price = Number(product.final_price ?? product.price ?? 0);
  if (state.priceBand === "under-2m") return price < 2000000;
  if (state.priceBand === "2m-4m") return price >= 2000000 && price <= 4000000;
  if (state.priceBand === "over-4m") return price > 4000000;
  return true;
}

function renderCatalogFilters() {
  const activeFilters = { discount: state.onlyDiscounted, stock: state.onlyInStock };
  document.querySelectorAll("[data-catalog-filter]").forEach((button) => {
    const active = Boolean(activeFilters[button.dataset.catalogFilter]);
    button.classList.toggle("selected", active);
    button.setAttribute("aria-pressed", String(active));
  });
  const priceFilter = document.querySelector("#price-filter");
  if (priceFilter) priceFilter.value = state.priceBand;
  const clearButton = document.querySelector("#clear-catalog-filters");
  if (clearButton) clearButton.hidden = !(state.onlyDiscounted || state.onlyInStock || state.priceBand !== "all");
}

function clearCatalogFilters() {
  state.onlyDiscounted = false;
  state.onlyInStock = false;
  state.priceBand = "all";
  renderCatalogFilters();
  renderProducts();
}

function renderProducts() {
  const grid = document.querySelector("#product-grid");
  syncCompareSelection();
  const categorySlugs = new Set();
  const collectCategorySlugs = (category) => { categorySlugs.add(category.slug); (category.children || []).forEach(collectCategorySlugs); };
  const selectedCategory = state.categories.find((category) => category.slug === state.category);
  if (selectedCategory) collectCategorySlugs(selectedCategory);
  const filtered = state.products.filter((product) => {
    const matchesCategory = !state.category || categorySlugs.has(product.category?.slug);
    const query = state.search.trim().toLowerCase();
    const matchesSearch = !query || `${productName(product)} ${product.name} ${product.brand || ""}`.toLowerCase().includes(query);
    const matchesDiscount = !state.onlyDiscounted || Number(product.discount_amount || 0) > 0;
    const matchesStock = !state.onlyInStock || product.is_in_stock;
    return matchesCategory && matchesSearch && matchesDiscount && matchesStock && matchesPriceBand(product);
  });
  const sorted = [...filtered].sort((a, b) => {
    if (state.sort === "price-low") return Number(a.final_price) - Number(b.final_price);
    if (state.sort === "price-high") return Number(b.final_price) - Number(a.final_price);
    if (state.sort === "name") return productName(a).localeCompare(productName(b), window.NexoraI18n?.current() === "en" ? "en" : "fa");
    return new Date(b.created_at || 0) - new Date(a.created_at || 0);
  });
  if (!sorted.length) {
    document.querySelector("#catalog-count").textContent = formatMessage("productCount", { count: localizedNumber(0) });
    grid.innerHTML = `<div class="state-card"><span class="state-icon">⌕</span><h3>${t("noProducts")}</h3><p>${t("changeFilter")}</p></div>`;
    renderRecentlyViewed();
    updateCompareUI();
    return;
  }
  document.querySelector("#catalog-count").textContent = formatMessage("productCount", { count: localizedNumber(sorted.length) });
  grid.innerHTML = sorted.map((product, index) => productCardMarkup(product, index)).join("");
  bindProductActions(grid, sorted);
  updateDiscountCountdowns();
  renderRecentlyViewed();
  updateCompareUI();
}

function featuredScore(product) {
  const price = Number(product.price || 0);
  const discount = Number(product.discount_amount || 0);
  const discountRatio = price > 0 ? discount / price : 0;
  const rating = Number(product.rating_average || 0);
  const stock = Math.min(Number(product.stock_quantity || 0), 50);
  const freshness = product.created_at ? new Date(product.created_at).getTime() / 1e12 : 0;
  return (discount > 0 ? 100 : 0) + discountRatio * 160 + rating * 12 + stock * 0.15 + freshness;
}

function renderFeaturedProducts() {
  const grid = document.querySelector("#featured-grid");
  if (!grid || !state.products.length) return;

  const candidates = state.products
    .filter((product) => product.is_in_stock)
    .sort((a, b) => featuredScore(b) - featuredScore(a))
    .slice(0, 4);

  if (!candidates.length) {
    grid.innerHTML = `<div class="state-card"><span class="state-icon">✦</span><h3>${escapeHTML(t("featuredEmpty"))}</h3><p>${escapeHTML(t("featuredFallback"))}</p></div>`;
    return;
  }

  grid.innerHTML = candidates.map((product, index) => productCardMarkup(product, index)).join("");
  bindProductActions(grid, candidates);
  updateDiscountCountdowns();
  updateCompareUI();
}

function renderDiscountProducts() {
  const section = document.querySelector("#discounts");
  const grid = document.querySelector("#discount-grid");
  if (!section || !grid || !state.products.length) return;

  const discounted = state.products
    .filter((product) => Number(product.discount_amount || 0) > 0)
    .sort((first, second) => {
      const firstRatio = Number(first.price) ? Number(first.discount_amount) / Number(first.price) : 0;
      const secondRatio = Number(second.price) ? Number(second.discount_amount) / Number(second.price) : 0;
      return (secondRatio - firstRatio) || (Number(second.discount_amount) - Number(first.discount_amount));
    })
    .slice(0, 4);

  section.hidden = false;
  if (!discounted.length) {
    grid.innerHTML = `<div class="state-card"><span class="state-icon">%</span><h3>${escapeHTML(t("discountsEmpty"))}</h3><p>${escapeHTML(t("discountsEmptyHint"))}</p></div>`;
    return;
  }
  grid.innerHTML = discounted.map((product, index) => productCardMarkup(product, index)).join("");
  bindProductActions(grid, discounted);
  updateDiscountCountdowns();
  updateCompareUI();
}

function renderCart(cart) {
  const body = document.querySelector("#cart-body");
  const footer = document.querySelector("#cart-footer");
  document.querySelector("#cart-count").textContent = localizedNumber(cart.item_count || 0);
  window.NexoraCartNav?.renderCount(cart.item_count || 0);
  document.querySelector("#cart-subtotal").textContent = money(cart.subtotal ?? 0);
  document.querySelector("#cart-total").textContent = money(cart.total_amount ?? cart.subtotal ?? 0);
  const shippingProgress = document.querySelector("#shipping-progress");
  const shippingProgressBar = document.querySelector("#shipping-progress-bar");
  const shippingProgressAmount = document.querySelector("#shipping-progress-amount");
  const shippingProgressMessage = document.querySelector("#shipping-progress-message");
  if (shippingProgress && shippingProgressBar && shippingProgressAmount && shippingProgressMessage) {
    const subtotal = Number(cart.subtotal || 0);
    const remaining = Math.max(FREE_SHIPPING_THRESHOLD - subtotal, 0);
    const progress = Math.min((subtotal / FREE_SHIPPING_THRESHOLD) * 100, 100);
    shippingProgress.hidden = false;
    shippingProgressBar.style.width = `${progress}%`;
    shippingProgressBar.classList.toggle("complete", remaining === 0);
    shippingProgressAmount.textContent = remaining ? money(remaining) : "✓";
    shippingProgressMessage.textContent = remaining
      ? formatMessage("shippingProgress", { amount: money(remaining) })
      : t("freeShippingUnlocked");
  }
  const couponTotal = document.querySelector("#coupon-total");
  const couponMessage = document.querySelector("#coupon-message");
  const couponInput = document.querySelector("#coupon-code");
  const couponForm = document.querySelector("#coupon-form");
  const couponRemove = document.querySelector("#coupon-remove");
  if (couponTotal) couponTotal.hidden = !(Number(cart.coupon_discount_amount) > 0);
  if (couponTotal && Number(cart.coupon_discount_amount) > 0) document.querySelector("#cart-coupon-discount").textContent = `-${money(cart.coupon_discount_amount)}`;
  if (couponInput) couponInput.value = cart.coupon_code || "";
  if (couponRemove) couponRemove.hidden = !cart.coupon_code;
  if (couponForm && !couponForm.dataset.bound) {
    couponForm.dataset.bound = "true";
    couponForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const code = couponInput.value.trim();
      if (!code) return;
      const button = couponForm.querySelector("button");
      button.disabled = true;
      couponMessage.textContent = "";
      try {
        await sendJSON("cart/coupon/", "POST", { code });
        await refreshCart();
        document.querySelector("#coupon-message").textContent = t("couponApplied");
      } catch (error) {
        couponMessage.textContent = error.message;
      } finally { button.disabled = false; }
    });
  }
  if (couponRemove && !couponRemove.dataset.bound) {
    couponRemove.dataset.bound = "true";
    couponRemove.addEventListener("click", async () => {
      couponRemove.disabled = true;
      try { await sendJSON("cart/coupon/", "DELETE"); await refreshCart(); document.querySelector("#coupon-message").textContent = t("couponRemoved"); }
      catch (error) { couponMessage.textContent = error.message; }
      finally { couponRemove.disabled = false; }
    });
  }
  if (!cart.items?.length) {
    footer.hidden = true;
    body.innerHTML = `<div class="cart-empty"><span class="state-icon">♡</span><h3>${t("emptyCart")}</h3><p>${t("emptyCartText")}</p><button class="retry-button" id="empty-cart-shop">${t("browseProducts")}</button></div>`;
    document.querySelector("#empty-cart-shop").addEventListener("click", () => closeCart());
    return;
  }
  footer.hidden = false;
  body.innerHTML = cart.items.map((item) => `<article class="cart-item"><div class="cart-item-image">${item.product?.image_url ? `<img src="${item.product.image_url}" alt="${productName(item.product)}">` : `<span>${(item.product?.brand || "N").slice(0, 1)}</span>`}</div><div class="cart-item-content"><h3>${item.product ? productName(item.product) : t("product")}</h3><strong>${money(item.line_total)}</strong>${item.unit_discount > 0 ? `<small class="cart-item-discount">${t("discountPerUnit")}: ${money(item.unit_discount)}</small>` : ""}<div class="quantity-control"><button data-action="decrease" data-item="${item.id}" aria-label="−">−</button><span>${localizedNumber(item.quantity)}</span><button data-action="increase" data-item="${item.id}" aria-label="+">+</button><button class="remove-item" data-action="remove" data-item="${item.id}" aria-label="${t("remove")}" title="${t("remove")}"><span aria-hidden="true">×</span><span class="sr-only">${t("remove")}</span></button></div></div></article>`).join("");
  body.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => updateCartItem(button.dataset.item, button.dataset.action)));
}

async function refreshCart() {
  try {
    const cart = await getJSON("cart/");
    renderCart(cart);
    return cart;
  } catch (error) {
    document.querySelector("#cart-body").innerHTML = `<div class="cart-empty"><span class="state-icon">!</span><h3>${t("cartUnavailable")}</h3><p>${t("retry")}</p></div>`;
  }
}

async function updateCartItem(itemId, action) {
  const item = document.querySelector(`[data-item="${itemId}"]`);
  const quantity = Number(latinNumber(item?.parentElement?.querySelector("span")?.textContent.replaceAll("٬", "") || 1));
  try {
    if (action === "remove" || (action === "decrease" && quantity <= 1)) await sendJSON(`cart/items/${itemId}/`, "DELETE");
    else await sendJSON(`cart/items/${itemId}/`, "PATCH", { quantity: action === "increase" ? quantity + 1 : quantity - 1 });
    await refreshCart();
  } catch (error) { showToast(error.message); }
}

function openCart() { document.querySelector("#cart-drawer").classList.add("open"); document.querySelector("#cart-drawer").setAttribute("aria-hidden", "false"); document.querySelector("#drawer-backdrop").hidden = false; refreshCart(); }
function closeCart() { document.querySelector("#cart-drawer").classList.remove("open"); document.querySelector("#cart-drawer").setAttribute("aria-hidden", "true"); document.querySelector("#drawer-backdrop").hidden = true; }
function showToast(message) { const toast = document.createElement("div"); toast.className = "toast-message"; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => toast.remove(), 2800); }

function renderCategories(categories) {
  const roots = categories.filter((category) => !category.parent);
  const hasDescendant = (category, slug) => category.slug === slug || (category.children || []).some((child) => hasDescendant(child, slug));
  const renderNode = (category, depth = 0) => {
    const children = category.children || [];
    const hasChildren = children.length > 0;
    const selected = hasDescendant(category, state.category);
    const expanded = hasChildren && (expandedCategorySlugs.has(category.slug) || (state.category && category.slug !== state.category && hasDescendant(category, state.category)));
    const name = categoryName(category);
    const escapedSlug = escapeHTML(category.slug);
    return `<li class="category-tree-item depth-${depth}${expanded ? " is-expanded" : ""}"><div class="category-tree-row"><button class="category-tree-button ${selected ? "selected" : ""}" data-category="${escapedSlug}" type="button" aria-current="${state.category === category.slug ? "true" : "false"}"><span class="category-tree-chevron" aria-hidden="true">${hasChildren ? (expanded ? "⌄" : "›") : "•"}</span><span class="category-tree-label">${escapeHTML(name)}</span></button>${hasChildren ? `<button class="category-tree-expand" data-category-expand="${escapedSlug}" type="button" aria-expanded="${String(expanded)}" aria-label="${escapeHTML(formatMessage(expanded ? "collapseCategory" : "expandCategory", { name }))}"><span aria-hidden="true">${expanded ? "−" : "+"}</span></button>` : ""}</div>${hasChildren ? `<ul class="category-tree-children"${expanded ? "" : " hidden"}>${children.map((child) => renderNode(child, depth + 1)).join("")}</ul>` : ""}</li>`;
  };
  document.querySelector("#category-tabs").innerHTML = `<button class="category-tree-all ${!state.category ? "selected" : ""}" data-category="" type="button">${t("categoriesAll")}</button><ul class="category-tree">${roots.map((category) => renderNode(category)).join("")}</ul>`;
  document.querySelectorAll("#category-tabs [data-category]").forEach((button) => button.addEventListener("click", () => {
    state.category = button.dataset.category;
    if (state.category) expandedCategorySlugs.add(state.category);
    renderCategories(categories);
    renderProducts();
  }));
  document.querySelectorAll("#category-tabs [data-category-expand]").forEach((button) => button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const slug = button.dataset.categoryExpand;
    if (expandedCategorySlugs.has(slug)) expandedCategorySlugs.delete(slug);
    else expandedCategorySlugs.add(slug);
    renderCategories(categories);
  }));
}

async function loadCatalog() {
  try {
    const [products, categories] = await Promise.all([getJSON("products/?page_size=100"), getJSON("categories/?page_size=100")]);
    state.products = products.results || products;
    state.categories = categories.results || categories;
    syncCompareSelection();
    await window.NexoraFavorites?.load();
    renderCategories(state.categories);
    renderCatalogFilters();
    renderProducts();
    renderDiscountProducts();
    renderFeaturedProducts();
  } catch (error) {
    document.querySelector("#product-grid").innerHTML = `<div class="state-card"><span class="state-icon">!</span><h3>${t("storefrontConnectionFailed")}</h3><p>${t("serverCheck")}</p><button class="retry-button" onclick="loadCatalog()">${t("tryAgain")}</button></div>`;
  }
}

document.querySelector("#product-search").addEventListener("input", (event) => { state.search = event.target.value; renderProducts(); });
document.querySelector("#product-sort").addEventListener("change", (event) => { state.sort = event.target.value; renderProducts(); });
document.querySelectorAll("[data-catalog-filter]").forEach((button) => button.addEventListener("click", () => {
  if (button.dataset.catalogFilter === "discount") state.onlyDiscounted = !state.onlyDiscounted;
  if (button.dataset.catalogFilter === "stock") state.onlyInStock = !state.onlyInStock;
  renderCatalogFilters();
  renderProducts();
}));
document.querySelector("#price-filter")?.addEventListener("change", (event) => {
  state.priceBand = event.target.value;
  renderCatalogFilters();
  renderProducts();
});
document.querySelector("#clear-catalog-filters")?.addEventListener("click", clearCatalogFilters);
document.querySelector("#discounts-view-all")?.addEventListener("click", (event) => {
  if (event.currentTarget.getAttribute("href") !== "#catalog") return;
  event.preventDefault();
  state.category = "";
  state.onlyDiscounted = true;
  renderCategories(state.categories);
  renderCatalogFilters();
  renderProducts();
  document.querySelector("#catalog")?.scrollIntoView({ behavior: "smooth", block: "start" });
});
document.querySelector("#menu-toggle").addEventListener("click", () => document.querySelector("#mobile-nav").classList.toggle("open"));
document.querySelector("#cart-toggle").addEventListener("click", openCart);
document.querySelector("#cart-close").addEventListener("click", closeCart);
document.querySelector("#drawer-backdrop").addEventListener("click", closeCart);
document.querySelector("#compare-open").addEventListener("click", openCompare);
document.querySelector("#compare-clear").addEventListener("click", () => { compareIds.clear(); persistCompareSelection(); updateCompareUI(); });
document.querySelector("#compare-close").addEventListener("click", closeCompare);
document.querySelector("#compare-backdrop").addEventListener("click", closeCompare);
document.querySelector("#clear-recently-viewed")?.addEventListener("click", () => {
  localStorage.removeItem(RECENT_STORAGE_KEY);
  renderRecentlyViewed();
});
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeCompare(); });
document.querySelector("#category-toggle").addEventListener("click", () => {
  const button = document.querySelector("#category-toggle");
  const panel = document.querySelector("#category-tabs");
  const isOpen = !panel.hidden;
  panel.hidden = isOpen;
  button.setAttribute("aria-expanded", String(!isOpen));
  document.querySelector("#category-filter").classList.toggle("open", !isOpen);
});
document.querySelector("#theme-toggle").addEventListener("click", () => { document.documentElement.classList.toggle("dark"); localStorage.setItem("nexora-theme", document.documentElement.classList.contains("dark") ? "dark" : "light"); updateThemeButton(); });
if (localStorage.getItem("nexora-theme") === "dark") document.documentElement.classList.add("dark");
function updateThemeButton() { document.querySelector("#theme-toggle").textContent = document.documentElement.classList.contains("dark") ? "☼" : "☾"; }
updateThemeButton();
window.setInterval(updateDiscountCountdowns, 1000);
renderCatalogFilters();
refreshCart();
loadAccountState();
loadCatalog().then(() => {
  const pendingToast = sessionStorage.getItem("nexora-toast");
  if (pendingToast) {
    sessionStorage.removeItem("nexora-toast");
    showToast(pendingToast);
  }
  if (new URLSearchParams(window.location.search).get("cart") === "open") openCart();
});
window.addEventListener("nexora-language-changed", () => {
  renderCategories(state.categories);
  renderProducts();
  renderDiscountProducts();
  renderFeaturedProducts();
  renderRecentlyViewed();
  refreshCart();
  loadAccountState();
  renderCatalogFilters();
  updateDiscountCountdowns();
  updateCompareUI();
});
