(function () {
  const API_BASE = "/api/v1/";
  const favoriteIds = new Set();
  const favoriteItems = [];
  let loaded = false;
  let loadingPromise = null;

  const t = (key) => window.NexoraI18n?.t(key) || key;

  function getCookie(name) {
    const cookie = (document.cookie ? document.cookie.split("; ") : []).find((value) => value.startsWith(name + "="));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null;
  }

  async function csrf() {
    const existingToken = getCookie("csrftoken");
    if (existingToken) return existingToken;
    const response = await fetch(API_BASE + "auth/csrf/", { credentials: "same-origin" });
    if (!response.ok || !getCookie("csrftoken")) throw new Error(t("securityTokenFailed"));
    return getCookie("csrftoken");
  }

  function isFavorite(productId) {
    return favoriteIds.has(Number(productId));
  }

  function updateButton(button, active) {
    if (!button) return;
    const isActive = Boolean(active);
    const label = t(isActive ? "removeFromFavorites" : "addToFavorites");
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
    button.setAttribute("aria-label", label);
    button.title = label;
    button.textContent = isActive ? "♥" : "♡";
  }

  function updateFavoriteNavigation() {
    const locale = window.NexoraI18n?.current() === "en" ? "en-US" : "fa-IR";
    const label = t("favorites");
    document.querySelectorAll("[data-favorites-nav]").forEach((link) => {
      link.setAttribute("aria-label", label);
      link.title = label;
    });
    document.querySelectorAll("[data-favorite-count]").forEach((counter) => {
      counter.textContent = new Intl.NumberFormat(locale).format(favoriteIds.size);
    });
  }

  function updateAllButtons(productId, active) {
    document.querySelectorAll("[data-favorite-product=\"" + productId + "\"]").forEach((button) => updateButton(button, active));
  }

  function sync(favorites) {
    const items = Array.isArray(favorites) ? favorites : [];
    favoriteIds.clear();
    favoriteItems.splice(0, favoriteItems.length, ...items);
    items.forEach((item) => {
      const productId = Number(item.product?.id || item.product_id);
      if (productId) favoriteIds.add(productId);
    });
    loaded = true;
    updateFavoriteNavigation();
    document.querySelectorAll("[data-favorite-product]").forEach((button) => updateButton(button, isFavorite(button.dataset.favoriteProduct)));
    return favoriteItems;
  }

  async function load() {
    if (loaded) return favoriteItems;
    if (loadingPromise) return loadingPromise;
    loadingPromise = (async () => {
      try {
        const response = await fetch(API_BASE + "auth/favorites/", { credentials: "same-origin" });
        if (response.status === 401) {
          return sync([]);
        }
        if (!response.ok) throw new Error("favorites-request-failed");
        const data = await response.json();
        const favorites = data.results || data || [];
        return sync(favorites);
      } catch (error) {
        return sync([]);
      } finally {
        loadingPromise = null;
      }
    })();
    return loadingPromise;
  }

  async function refresh() {
    loaded = false;
    return load();
  }

  async function toggle(productId) {
    const numericProductId = Number(productId);
    const response = await fetch(API_BASE + "auth/favorites/toggle/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": await csrf(),
      },
      body: JSON.stringify({ product_id: numericProductId }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.detail || data.product_id?.[0] || t("operationFailed"));
      error.status = response.status;
      throw error;
    }
    const active = Boolean(data.is_favorite);
    if (active) favoriteIds.add(numericProductId);
    else favoriteIds.delete(numericProductId);
    const existingIndex = favoriteItems.findIndex((item) => Number(item.product?.id) === numericProductId);
    if (active && data.favorite) {
      if (existingIndex === -1) favoriteItems.unshift(data.favorite);
      else favoriteItems[existingIndex] = data.favorite;
    } else if (!active && existingIndex !== -1) {
      favoriteItems.splice(existingIndex, 1);
    }
    updateFavoriteNavigation();
    updateAllButtons(numericProductId, active);
    document.dispatchEvent(new CustomEvent("nexora-favorite-changed", {
      detail: { productId: numericProductId, isFavorite: active, favorite: data.favorite || null },
    }));
    return data;
  }

  function showToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast-message";
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2800);
  }

  function redirectToLogin() {
    const next = window.location.pathname + window.location.search;
    window.location.href = "/account/?next=" + encodeURIComponent(next);
  }

  function bindButtons(root = document) {
    root.querySelectorAll("[data-favorite-product]").forEach((button) => {
      updateButton(button, isFavorite(button.dataset.favoriteProduct));
      if (button.dataset.favoriteBound) return;
      button.dataset.favoriteBound = "true";
      button.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (button.disabled) return;
        button.disabled = true;
        button.classList.add("is-loading");
        try {
          const data = await toggle(button.dataset.favoriteProduct);
          showToast(t(data.is_favorite ? "favoriteAdded" : "favoriteRemoved"));
        } catch (error) {
          if (error.status === 401 || error.status === 403) redirectToLogin();
          else showToast(error.message);
        } finally {
          button.disabled = false;
          button.classList.remove("is-loading");
        }
      });
    });
  }

  window.NexoraFavorites = { bindButtons, isFavorite, load, refresh, sync, toggle, updateButton };
  window.addEventListener("nexora-language-changed", () => {
    updateFavoriteNavigation();
    bindButtons(document);
  });
  updateFavoriteNavigation();
  load();
})();
