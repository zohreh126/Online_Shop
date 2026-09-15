const API_BASE = "/api/v1/";
const state = { products: [], categories: [], category: "", search: "" };

const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const localizedNumber = (value) => new Intl.NumberFormat(window.NexoraI18n?.current() === "en" ? "en-US" : "fa-IR").format(value);
const money = (value) => window.NexoraI18n?.current() === "en" ? `${new Intl.NumberFormat("en-US").format(Math.round(Number(value)))} toman` : `${faNumber(Math.round(Number(value)))} تومان`;
const latinNumber = (value) => String(value).replace(/[۰-۹]/g, (digit) => "۰۱۲۳۴۵۶۷۸۹".indexOf(digit));
const t = (key) => window.NexoraI18n?.t(key) || key;

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
    return `<img src="${product.image_url}" alt="تصویر ${product.name}" loading="lazy" onerror="this.closest('.product-visual').classList.add('image-failed'); this.remove();">`;
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

function renderProducts() {
  const grid = document.querySelector("#product-grid");
  const categorySlugs = new Set();
  const collectCategorySlugs = (category) => { categorySlugs.add(category.slug); (category.children || []).forEach(collectCategorySlugs); };
  const selectedCategory = state.categories.find((category) => category.slug === state.category);
  if (selectedCategory) collectCategorySlugs(selectedCategory);
  const filtered = state.products.filter((product) => {
    const matchesCategory = !state.category || categorySlugs.has(product.category?.slug);
    const query = state.search.trim().toLowerCase();
    const matchesSearch = !query || `${product.name} ${product.brand || ""}`.toLowerCase().includes(query);
    return matchesCategory && matchesSearch;
  });
  if (!filtered.length) {
    grid.innerHTML = `<div class="state-card"><span class="state-icon">⌕</span><h3>${t("noProducts")}</h3><p>${t("changeFilter")}</p></div>`;
    return;
  }
  grid.innerHTML = filtered.map((product, index) => `
    <article class="product-card" style="--delay:${index * 60}ms">
      <div class="product-visual">${productImage(product)}${product.discount_amount > 0 ? `<span class="discount-badge">${t("specialOffer")}</span>` : ''}<span class="stock-badge ${product.is_in_stock ? "" : "out-of-stock"}">${product.is_in_stock ? t("available") : t("unavailable")}</span><button class="heart-button" aria-label="${t("addToFavorites")}">♡</button></div>
      <div class="product-info"><p class="product-category">${product.category ? categoryName(product.category) : t("digitalAccessories")}</p><h3><a class="product-title-link" href="/products/${product.slug}/">${productName(product)}</a></h3><div class="product-bottom"><div><strong>${money(product.final_price)}</strong>${product.discount_amount > 0 ? `<del>${money(product.price)}</del>` : ""}</div><button class="add-button" data-product="${product.id}" aria-label="${t("addToCart")}" ${product.is_in_stock ? "" : "disabled"}>${product.is_in_stock ? "+" : "−"}</button></div></div>
    </article>`).join("");
  grid.querySelectorAll(".add-button").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    button.classList.add("is-loading");
    try {
      await sendJSON("cart/items/", "POST", { product_id: button.dataset.product, quantity: 1 });
      await refreshCart();
      button.textContent = "✓";
      showToast(t("addedToCart"));
      setTimeout(() => { button.textContent = "+"; }, 900);
    } catch (error) {
      showToast(error.message);
    } finally {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }));
  grid.querySelectorAll(".product-card").forEach((card) => card.addEventListener("click", (event) => {
    if (event.target.closest("button, a")) return;
    window.location.href = `/products/${card.querySelector(".product-title-link")?.getAttribute("href")?.split("/").filter(Boolean).pop()}/`;
  }));
}

function renderCart(cart) {
  const body = document.querySelector("#cart-body");
  const footer = document.querySelector("#cart-footer");
  document.querySelector("#cart-count").textContent = localizedNumber(cart.item_count || 0);
  document.querySelector("#cart-subtotal").textContent = money(cart.subtotal ?? 0);
  document.querySelector("#cart-total").textContent = money(cart.total_amount ?? cart.subtotal ?? 0);
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
  body.innerHTML = cart.items.map((item) => `<article class="cart-item"><div class="cart-item-image">${item.product?.image_url ? `<img src="${item.product.image_url}" alt="${productName(item.product)}">` : `<span>${(item.product?.brand || "N").slice(0, 1)}</span>`}</div><div class="cart-item-content"><h3>${item.product ? productName(item.product) : t("product")}</h3><strong>${money(item.line_total)}</strong>${item.unit_discount > 0 ? `<small class="cart-item-discount">${t("discountPerUnit")}: ${money(item.unit_discount)}</small>` : ""}<div class="quantity-control"><button data-action="decrease" data-item="${item.id}" aria-label="−">−</button><span>${localizedNumber(item.quantity)}</span><button data-action="increase" data-item="${item.id}" aria-label="+">+</button><button class="remove-item" data-action="remove" data-item="${item.id}" aria-label="${t("remove")}">${t("remove")}</button></div></div></article>`).join("");
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
  const renderNode = (category, depth = 0) => `<li class="category-tree-item depth-${depth}"><button class="category-tree-button ${hasDescendant(category, state.category) ? "selected" : ""}" data-category="${category.slug}" type="button"><span class="category-tree-chevron">${category.children?.length ? "⌄" : ""}</span>${categoryName(category)}</button>${category.children?.length ? `<ul class="category-tree-children">${category.children.map((child) => renderNode(child, depth + 1)).join("")}</ul>` : ""}</li>`;
  document.querySelector("#category-tabs").innerHTML = `<button class="category-tree-all ${!state.category ? "selected" : ""}" data-category="" type="button">${t("categoriesAll")}</button><ul class="category-tree">${roots.map((category) => renderNode(category)).join("")}</ul>`;
  document.querySelectorAll("[data-category]").forEach((button) => button.addEventListener("click", () => { state.category = button.dataset.category; renderCategories(categories); renderProducts(); }));
}

async function loadCatalog() {
  try {
    const [products, categories] = await Promise.all([getJSON("products/?page_size=100"), getJSON("categories/?page_size=100")]);
    state.products = products.results || products;
    state.categories = categories.results || categories;
    renderCategories(state.categories);
    renderProducts();
  } catch (error) {
    document.querySelector("#product-grid").innerHTML = `<div class="state-card"><span class="state-icon">!</span><h3>${t("storefrontConnectionFailed")}</h3><p>${t("serverCheck")}</p><button class="retry-button" onclick="loadCatalog()">${t("tryAgain")}</button></div>`;
  }
}

document.querySelector("#product-search").addEventListener("input", (event) => { state.search = event.target.value; renderProducts(); });
document.querySelector("#menu-toggle").addEventListener("click", () => document.querySelector("#mobile-nav").classList.toggle("open"));
document.querySelector("#cart-toggle").addEventListener("click", openCart);
document.querySelector("#cart-close").addEventListener("click", closeCart);
document.querySelector("#drawer-backdrop").addEventListener("click", closeCart);
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
refreshCart();
loadAccountState();
loadCatalog();
window.addEventListener("nexora-language-changed", () => {
  renderCategories(state.categories);
  renderProducts();
  refreshCart();
  loadAccountState();
});
