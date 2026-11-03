(function () {
  const API_BASE = "/api/v1/";
  let currentUser = null;
  let loadingPromise = null;

  const t = (key) => window.NexoraI18n?.t(key) || key;
  const escapeHTML = (value) => String(value ?? "").replace(/[&<>\'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[character]));

  function accountAreas() {
    return [...document.querySelectorAll("#account-area, [data-account-area]")];
  }

  function getCookie(name) {
    const cookie = (document.cookie ? document.cookie.split("; ") : [])
      .find((item) => item.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null;
  }

  async function csrf() {
    const existing = getCookie("csrftoken");
    if (existing) return existing;
    const response = await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" });
    if (!response.ok || !getCookie("csrftoken")) throw new Error(t("securityTokenFailed"));
    return getCookie("csrftoken");
  }

  function notify(message) {
    const toast = document.createElement("div");
    toast.className = "toast-message";
    toast.textContent = message;
    document.body.appendChild(toast);
    window.setTimeout(() => toast.remove(), 2800);
  }

  function roleDestination(user) {
    return user?.is_staff || user?.is_superuser ? "/admin/" : "/profile/";
  }

  function render(user) {
    currentUser = user || null;
    const label = user ? (user.first_name || user.username) : t("login");
    accountAreas().forEach((area) => {
      if (!user) {
        area.innerHTML = `<a class="account-link" href="/account/" data-i18n="login">${t("login")}</a>`;
        return;
      }
      const destination = roleDestination(user);
      const roleLabel = user.is_staff || user.is_superuser ? t("adminRole") : t("customer");
      const safeLabel = escapeHTML(label);
      const safeRoleLabel = escapeHTML(roleLabel);
      const initial = escapeHTML(String(label).slice(0, 1).toUpperCase());
      area.innerHTML = `<a class="account-name" href="${destination}" title="${safeRoleLabel}"><span class="account-avatar" aria-hidden="true">${initial}</span><span>${safeLabel}</span></a><button class="account-link account-logout" type="button" data-account-logout>${escapeHTML(t("logout"))}</button>`;
      area.querySelector("[data-account-logout]")?.addEventListener("click", logout);
    });
  }

  async function load() {
    if (loadingPromise) return loadingPromise;
    loadingPromise = fetch(`${API_BASE}auth/profile/`, { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) {
          render(null);
          return null;
        }
        const user = await response.json();
        render(user);
        return user;
      })
      .catch(() => {
        render(null);
        return null;
      })
      .finally(() => { loadingPromise = null; });
    return loadingPromise;
  }

  async function logout(event) {
    event?.preventDefault();
    const button = event?.currentTarget;
    if (button) button.disabled = true;
    try {
      const response = await fetch(`${API_BASE}auth/logout/`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": await csrf() },
      });
      if (!response.ok) throw new Error(t("operationFailed"));
      render(null);
      window.NexoraCartNav?.renderCount(0);
      window.NexoraFavorites?.sync([]);
      window.dispatchEvent(new CustomEvent("nexora-logged-out"));
      notify(t("loggedOut"));
    } catch (error) {
      if (button) button.disabled = false;
      notify(error.message || t("operationFailed"));
    }
  }

  window.NexoraAccountNav = { load, refresh: load, render, logout, current: () => currentUser };
  window.addEventListener("nexora-logged-in", (event) => render(event.detail?.user || currentUser));
  window.addEventListener("nexora-language-changed", () => render(currentUser));
  document.addEventListener("DOMContentLoaded", () => {
    if (accountAreas().length) load();
  });
})();
