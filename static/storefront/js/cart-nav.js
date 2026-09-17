(function () {
  const API_BASE = "/api/v1/";
  let lastCount = 0;

  function locale() {
    return document.documentElement.lang === "en" ? "en-US" : "fa-IR";
  }

  function renderCount(value) {
    lastCount = Math.max(0, Number(value) || 0);
    const formatted = new Intl.NumberFormat(locale()).format(lastCount);
    document.querySelectorAll("[data-cart-count]").forEach((counter) => {
      counter.dataset.cartCount = String(lastCount);
      counter.textContent = formatted;
    });
    return lastCount;
  }

  async function refresh() {
    try {
      const response = await fetch(`${API_BASE}cart/`, { credentials: "same-origin" });
      if (!response.ok) return lastCount;
      const cart = await response.json();
      return renderCount(cart.item_count || 0);
    } catch (error) {
      return lastCount;
    }
  }

  window.NexoraCartNav = { refresh, renderCount };
  window.addEventListener("nexora-language-changed", () => renderCount(lastCount));
  window.addEventListener("nexora-cart-updated", (event) => renderCount(event.detail?.cart?.item_count || 0));
  refresh();
})();
