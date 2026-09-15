const API_BASE = "/api/v1/";
const t = (key) => window.NexoraI18n?.t(key) || key;
const number = (value) => new Intl.NumberFormat(window.NexoraI18n?.current() === "en" ? "en-US" : "fa-IR").format(value);
const money = (value) => window.NexoraI18n?.current() === "en" ? `${new Intl.NumberFormat("en-US").format(Math.round(Number(value)))} toman` : `${number(Math.round(Number(value)))} تومان`;
const format = (key, values) => Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{${name}}`, value), t(key));
const slug = window.location.pathname.split("/").filter(Boolean).pop();

async function getJSON(path) {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  if (!response.ok) throw new Error("product-not-found");
  return response.json();
}

function getCookie(name) {
  const value = document.cookie.split("; ").find((item) => item.startsWith(`${name}=`));
  return value ? decodeURIComponent(value.slice(name.length + 1)) : null;
}

async function csrf() {
  if (getCookie("csrftoken")) return getCookie("csrftoken");
  const response = await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" });
  if (!response.ok || !getCookie("csrftoken")) throw new Error(t("securityTokenFailed"));
  return getCookie("csrftoken");
}

async function addToCart(product) {
  const response = await fetch(`${API_BASE}cart/items/`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": await csrf() }, body: JSON.stringify({ product_id: product.id, quantity: 1 }) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.product_id?.[0] || t("operationFailed"));
  showToast(t("productAdded"));
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast-message";
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2800);
}

function renderProduct(product) {
  const specs = Object.entries(product.specifications || {});
  const displayName = window.NexoraI18n?.productName(product) || product.name;
  const image = product.image_url ? `<img class="product-detail-image" src="${product.image_url}" alt="${displayName}">` : `<div class="product-detail-placeholder"><span>${(product.brand || "N").slice(0, 1)}</span></div>`;
  document.querySelector("#product-detail-content").innerHTML = `<div class="product-detail-visual">${image}<span class="detail-badge">${product.category?.name || t("digitalAccessories")}</span></div><div class="product-detail-copy"><p class="eyebrow"><span></span><span data-i18n="productDetails">${t("productDetails")}</span></p><h1>${displayName}</h1><p class="product-detail-brand">${product.brand || "Nexora"} · ${t("sku")}: ${product.sku}</p><p class="product-detail-description">${window.NexoraI18n?.productDescription(product) || product.description || t("carefulChoiceText")}</p><div class="product-detail-price"><strong>${money(product.final_price)}</strong>${Number(product.discount_amount) > 0 ? `<del>${money(product.price)}</del>` : ""}</div><p class="product-stock ${product.is_in_stock ? "in-stock" : "out-of-stock"}">${product.is_in_stock ? format("stockCount", { count: number(product.stock_quantity) }) : t("unavailable")}</p><button class="primary-button detail-add" type="button" ${product.is_in_stock ? "" : "disabled"}>${product.is_in_stock ? t("addToCart") : t("unavailable")} <span>←</span></button><div class="specification-panel"><h2>${t("specifications")}</h2>${specs.length ? `<dl>${specs.map(([key, value]) => `<div><dt>${key}</dt><dd>${value}</dd></div>`).join("")}</dl>` : `<p class="empty-inline">${t("carefulChoiceText")}</p>`}</div></div>`;
  const detailContent = document.querySelector("#product-detail-content");
  detailContent.querySelector(".detail-badge").textContent = window.NexoraI18n?.category(product.category?.slug, product.category?.name || t("digitalAccessories")) || t("digitalAccessories");
  detailContent.querySelector(".product-detail-description").textContent = window.NexoraI18n?.productDescription(product) || t("carefulChoiceText");
  detailContent.querySelectorAll(".specification-panel dt").forEach((element, index) => { element.textContent = window.NexoraI18n?.specificationLabel(specs[index][0]) || specs[index][0]; });
  detailContent.querySelectorAll(".specification-panel dd").forEach((element, index) => { const value = specs[index][1]; element.textContent = Array.isArray(value) ? value.join(", ") : value === true ? "Yes" : value === false ? "No" : value; });
  document.querySelector(".detail-add")?.addEventListener("click", async (event) => { event.currentTarget.disabled = true; try { await addToCart(product); } catch (error) { showToast(error.message); } finally { event.currentTarget.disabled = false; } });
}

async function loadProduct() {
  try {
    const product = await getJSON(`products/${encodeURIComponent(slug)}/`);
    window.productDetail = product;
    renderProduct(product);
    document.querySelector("#product-detail-state").hidden = true;
    document.querySelector("#product-detail-content").hidden = false;
    document.title = `${product.name} | Nexora`;
    return product;
  } catch (error) {
    document.querySelector("#product-detail-state").innerHTML = `<span class="state-icon">!</span><h3>${t("noProducts")}</h3><p>${t("changeFilter")}</p>`;
  }
}

function updateThemeButton() { document.querySelector("#theme-toggle").textContent = document.documentElement.classList.contains("dark") ? "☼" : "☾"; }
document.querySelector("#theme-toggle").addEventListener("click", () => { document.documentElement.classList.toggle("dark"); localStorage.setItem("nexora-theme", document.documentElement.classList.contains("dark") ? "dark" : "light"); updateThemeButton(); });
if (localStorage.getItem("nexora-theme") === "dark") document.documentElement.classList.add("dark");
updateThemeButton();
window.addEventListener("nexora-language-changed", () => { if (window.productDetail) renderProduct(window.productDetail); });
loadProduct();
