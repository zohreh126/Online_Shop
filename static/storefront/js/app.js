const API_BASE = "/api/v1/";
const state = { products: [], category: "", search: "" };

const faNumber = (value) => new Intl.NumberFormat("fa-IR").format(value);
const money = (value) => `${faNumber(Math.round(Number(value)))} تومان`;
const latinNumber = (value) => String(value).replace(/[۰-۹]/g, (digit) => "۰۱۲۳۴۵۶۷۸۹".indexOf(digit));

async function getJSON(path) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  if (!response.ok) throw new Error("API request failed");
  return response.json();
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

function renderProducts() {
  const grid = document.querySelector("#product-grid");
  const filtered = state.products.filter((product) => {
    const matchesCategory = !state.category || product.category?.slug === state.category;
    const query = state.search.trim().toLowerCase();
    const matchesSearch = !query || `${product.name} ${product.brand || ""}`.toLowerCase().includes(query);
    return matchesCategory && matchesSearch;
  });
  if (!filtered.length) {
    grid.innerHTML = `<div class="state-card"><span class="state-icon">⌕</span><h3>محصولی پیدا نشد</h3><p>فیلتر یا عبارت جست‌وجو را تغییر بده.</p></div>`;
    return;
  }
  grid.innerHTML = filtered.map((product, index) => `
    <article class="product-card" style="--delay:${index * 60}ms">
      <div class="product-visual">${productImage(product)}${product.discount_amount > 0 ? '<span class="discount-badge">پیشنهاد ویژه</span>' : ''}<span class="stock-badge ${product.is_in_stock ? "" : "out-of-stock"}">${product.is_in_stock ? "موجود" : "ناموجود"}</span><button class="heart-button" aria-label="افزودن به علاقه‌مندی‌ها">♡</button></div>
      <div class="product-info"><p class="product-category">${product.category?.name || "اکسسوری دیجیتال"}</p><h3>${product.name}</h3><div class="product-bottom"><div><strong>${money(product.final_price)}</strong>${product.discount_amount > 0 ? `<del>${money(product.price)}</del>` : ""}</div><button class="add-button" data-product="${product.id}" aria-label="افزودن ${product.name} به سبد" ${product.is_in_stock ? "" : "disabled"}>${product.is_in_stock ? "+" : "−"}</button></div></div>
    </article>`).join("");
  grid.querySelectorAll(".add-button").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    button.classList.add("is-loading");
    try {
      await sendJSON("cart/items/", "POST", { product_id: button.dataset.product, quantity: 1 });
      await refreshCart();
      button.textContent = "✓";
      openCart();
      setTimeout(() => { button.textContent = "+"; }, 900);
    } catch (error) {
      showToast(error.message);
    } finally {
      button.disabled = false;
      button.classList.remove("is-loading");
    }
  }));
}

function renderCart(cart) {
  const body = document.querySelector("#cart-body");
  const footer = document.querySelector("#cart-footer");
  document.querySelector("#cart-count").textContent = faNumber(cart.item_count || 0);
  document.querySelector("#cart-subtotal").textContent = money(cart.total_amount ?? cart.subtotal ?? 0);
  if (!cart.items?.length) {
    footer.hidden = true;
    body.innerHTML = `<div class="cart-empty"><span class="state-icon">♡</span><h3>سبد خرید خالی است</h3><p>محصولی که دوست داری را به سبد اضافه کن.</p><button class="retry-button" id="empty-cart-shop">مشاهده محصولات</button></div>`;
    document.querySelector("#empty-cart-shop").addEventListener("click", () => closeCart());
    return;
  }
  footer.hidden = false;
  body.innerHTML = cart.items.map((item) => `<article class="cart-item"><div class="cart-item-image">${item.product?.image_url ? `<img src="${item.product.image_url}" alt="تصویر ${item.product.name}">` : `<span>${(item.product?.brand || "N").slice(0, 1)}</span>`}</div><div class="cart-item-content"><h3>${item.product?.name || "محصول"}</h3><strong>${money(item.line_total)}</strong>${item.unit_discount > 0 ? `<small class="cart-item-discount">تخفیف هر واحد: ${money(item.unit_discount)}</small>` : ""}<div class="quantity-control"><button data-action="decrease" data-item="${item.id}" aria-label="کاهش تعداد">−</button><span>${faNumber(item.quantity)}</span><button data-action="increase" data-item="${item.id}" aria-label="افزایش تعداد">+</button><button class="remove-item" data-action="remove" data-item="${item.id}" aria-label="حذف محصول">حذف</button></div></div></article>`).join("");
  body.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => updateCartItem(button.dataset.item, button.dataset.action)));
}

async function refreshCart() {
  try {
    const cart = await getJSON("cart/");
    renderCart(cart);
    return cart;
  } catch (error) {
    document.querySelector("#cart-body").innerHTML = `<div class="cart-empty"><span class="state-icon">!</span><h3>سبد خرید در دسترس نیست</h3><p>دوباره تلاش کن.</p></div>`;
  }
}

async function updateCartItem(itemId, action) {
  const item = document.querySelector(`[data-item="${itemId}"]`);
  const quantity = Number(latinNumber(item?.parentElement?.querySelector("span")?.textContent.replaceAll("٬", "") || 1));
  try {
    if (action === "remove" || (action === "decrease" && quantity <= 1)) await sendJSON(`cart/items/${itemId}/`, "DELETE");
    else await sendJSON(`cart/items/${itemId}/`, "PATCH", { quantity: action === "increase" ? quantity + 1 : quantity - 1 });
    await refreshCart();
    await loadCatalog();
  } catch (error) { showToast(error.message); }
}

function openCart() { document.querySelector("#cart-drawer").classList.add("open"); document.querySelector("#cart-drawer").setAttribute("aria-hidden", "false"); document.querySelector("#drawer-backdrop").hidden = false; refreshCart(); }
function closeCart() { document.querySelector("#cart-drawer").classList.remove("open"); document.querySelector("#cart-drawer").setAttribute("aria-hidden", "true"); document.querySelector("#drawer-backdrop").hidden = true; }
function showToast(message) { const toast = document.createElement("div"); toast.className = "toast-message"; toast.textContent = message; document.body.appendChild(toast); setTimeout(() => toast.remove(), 2800); }

function renderCategories(categories) {
  document.querySelector("#category-tabs").innerHTML = [{ name: "همه", slug: "" }, ...categories].map((category) => `<button class="${category.slug === state.category ? "selected" : ""}" data-category="${category.slug}">${category.name}</button>`).join("");
  document.querySelectorAll("[data-category]").forEach((button) => button.addEventListener("click", () => {
    state.category = button.dataset.category;
    renderCategories(categories);
    renderProducts();
  }));
}

async function loadCatalog() {
  try {
    const [products, categories] = await Promise.all([getJSON("products/?page_size=100"), getJSON("categories/?page_size=100")]);
    state.products = products.results || products;
    renderCategories(categories.results || categories);
    renderProducts();
  } catch (error) {
    document.querySelector("#product-grid").innerHTML = `<div class="state-card"><span class="state-icon">!</span><h3>اتصال به ویترین برقرار نشد</h3><p>مطمئن شو سرور Django روشن است و دوباره تلاش کن.</p><button class="retry-button" onclick="loadCatalog()">تلاش دوباره</button></div>`;
  }
}

document.querySelector("#product-search").addEventListener("input", (event) => { state.search = event.target.value; renderProducts(); });
document.querySelector("#menu-toggle").addEventListener("click", () => document.querySelector("#mobile-nav").classList.toggle("open"));
document.querySelector("#cart-toggle").addEventListener("click", openCart);
document.querySelector("#cart-close").addEventListener("click", closeCart);
document.querySelector("#drawer-backdrop").addEventListener("click", closeCart);
document.querySelector("#theme-toggle").addEventListener("click", () => { document.documentElement.classList.toggle("dark"); localStorage.setItem("nexora-theme", document.documentElement.classList.contains("dark") ? "dark" : "light"); updateThemeButton(); });
if (localStorage.getItem("nexora-theme") === "dark") document.documentElement.classList.add("dark");
function updateThemeButton() { document.querySelector("#theme-toggle").textContent = document.documentElement.classList.contains("dark") ? "☼" : "☾"; }
updateThemeButton();
refreshCart();
loadCatalog();
