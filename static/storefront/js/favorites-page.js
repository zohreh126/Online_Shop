(function () {
  const API_BASE = "/api/v1/";
  const tr = (key) => window.NexoraI18n?.t(key) || key;
  const localizedNumber = (value) => new Intl.NumberFormat(document.documentElement.lang === "en" ? "en-US" : "fa-IR").format(value);
  const money = (value) => `${localizedNumber(Math.round(Number(value)))} ${tr("toman")}`;
  const escapeHTML = (value) => String(value ?? "").replace(/[&<>\'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
  let products = [];
  let loaded = false;

  function productName(product) {
    return window.NexoraI18n?.productName(product) || product.name || product.product_name || tr("product");
  }

  function productCategory(product) {
    if (!product.category) return tr("digitalAccessories");
    return window.NexoraI18n?.category(product.category.slug, product.category.name) || product.category.name;
  }

  function productSavings(product) {
    const amount = Number(product.discount_amount || 0);
    return amount > 0 ? `<small class="product-savings"><span aria-hidden="true">✦</span>${escapeHTML(tr("youSave").replace("{amount}", money(amount)))}</small>` : "";
  }

  function discountLabel(product) {
    const amount = Number(product.discount_amount || 0);
    if (!amount) return "";
    if (product.discount_type === "percentage" && product.discount_value !== null && product.discount_value !== undefined) {
      return tr("discountPercent").replace("{percent}", localizedNumber(Number(product.discount_value)));
    }
    return tr("discountAmount").replace("{amount}", money(amount));
  }

  function discountCountdownMarkup(product) {
    const endsAt = Date.parse(product.discount_ends_at || "");
    if (!Number.isFinite(endsAt) || Number(product.discount_amount || 0) <= 0) return "";
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
    return values.map(([label, value]) => `${localizedNumber(value)} ${tr(label)}`).join(" ");
  }

  function updateDiscountCountdowns() {
    document.querySelectorAll("[data-discount-countdown]").forEach((element) => {
      const remaining = Number(element.dataset.discountCountdown) - Date.now();
      if (remaining <= 0) {
        element.classList.add("expired");
        element.innerHTML = `<span aria-hidden="true">!</span><span>${escapeHTML(tr("discountEnded"))}</span>`;
        return;
      }
      element.classList.remove("expired");
      element.innerHTML = `<span aria-hidden="true">◷</span><span>${escapeHTML(tr("discountEndsIn").replace("{time}", discountCountdownText(remaining)))}</span>`;
    });
  }

  function favoriteCard(product) {
    const name = productName(product);
    const href = "/products/" + encodeURIComponent(product.slug) + "/";
    const image = product.image_url
      ? `<img src="${escapeHTML(product.image_url)}" alt="${escapeHTML(name)}" loading="lazy">`
      : `<span class="favorite-placeholder">${escapeHTML((product.brand || "N").slice(0, 1))}</span>`;
    const discount = Number(product.discount_amount) > 0 ? `<del>${money(product.price)}</del>` : "";
    const discountBadge = discountLabel(product) ? `<span class="favorite-discount-badge">${escapeHTML(discountLabel(product))}</span>` : "";
    return `<article class="favorite-card">
      <a class="favorite-card-visual" href="${escapeHTML(href)}">${image}${discountBadge}</a>
      <div class="favorite-card-info">
        <p class="product-category">${escapeHTML(productCategory(product))}</p>
        <h3><a href="${escapeHTML(href)}">${escapeHTML(name)}</a></h3>
        <div class="favorite-card-bottom">
          <div class="price-stack"><strong>${money(product.final_price)}</strong>${discount}${productSavings(product)}${discountCountdownMarkup(product)}</div>
          <button class="heart-button favorite-remove" data-favorite-product="${product.id}" type="button" aria-label="${escapeHTML(tr("removeFromFavorites"))}" aria-pressed="true">♥</button>
        </div>
      </div>
    </article>`;
  }

  function renderEmpty(messageKey = "noFavorites", hintKey = "favoritesHint") {
    const state = document.querySelector("#favorites-state");
    const list = document.querySelector("#favorites-list");
    list.hidden = true;
    state.hidden = false;
    state.innerHTML = `<span class="state-icon">♡</span><h3>${escapeHTML(tr(messageKey))}</h3><p>${escapeHTML(tr(hintKey))}</p><a class="primary-button" href="/">${escapeHTML(tr("browseProducts"))} <span>←</span></a>`;
  }

  function render() {
    if (!loaded) return;
    const state = document.querySelector("#favorites-state");
    const list = document.querySelector("#favorites-list");
    if (!products.length) {
      renderEmpty();
      return;
    }
    state.hidden = true;
    list.hidden = false;
    list.innerHTML = products.map(favoriteCard).join("");
    window.NexoraFavorites?.bindButtons(list);
    updateDiscountCountdowns();
  }

  function renderError() {
    const state = document.querySelector("#favorites-state");
    const list = document.querySelector("#favorites-list");
    list.hidden = true;
    state.hidden = false;
    state.innerHTML = `<span class="state-icon">!</span><h3>${escapeHTML(tr("favoritesLoadFailed"))}</h3><p>${escapeHTML(tr("retry"))}</p><button class="primary-button" id="favorites-retry" type="button">${escapeHTML(tr("tryAgain"))} <span>↻</span></button>`;
    document.querySelector("#favorites-retry")?.addEventListener("click", loadPage, { once: true });
  }

  async function fetchFavorites() {
    const response = await fetch(API_BASE + "auth/favorites/", { credentials: "same-origin" });
    if (response.status === 401) {
      window.location.href = "/account/?next=" + encodeURIComponent(window.location.pathname);
      return null;
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || tr("favoritesLoadFailed"));
    const favorites = data.results || data || [];
    window.NexoraFavorites?.sync?.(favorites);
    return favorites.map((item) => item.product).filter(Boolean);
  }

  async function loadPage() {
    loaded = false;
    try {
      products = (await fetchFavorites()) || [];
      loaded = true;
      render();
    } catch (error) {
      loaded = true;
      renderError();
    }
  }

  document.addEventListener("nexora-favorite-changed", (event) => {
    const productId = Number(event.detail?.productId);
    if (!event.detail?.isFavorite) {
      products = products.filter((product) => Number(product.id) !== productId);
    } else if (event.detail?.favorite?.product) {
      const product = event.detail.favorite.product;
      products = [product, ...products.filter((item) => Number(item.id) !== Number(product.id))];
    }
    if (loaded) render();
  });

  window.addEventListener("nexora-language-changed", () => {
    if (loaded) render();
  });

  window.setInterval(updateDiscountCountdowns, 1000);
  loadPage();
})();
