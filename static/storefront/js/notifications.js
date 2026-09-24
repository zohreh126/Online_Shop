(function () {
  const API_BASE = "/api/v1/";
  let items = [];
  let authenticated = false;

  const t = (key) => window.NexoraI18n?.t(key) || key;
  const locale = () => document.documentElement.lang === "en" ? "en-US" : "fa-IR";

  function getCookie(name) {
    const cookie = (document.cookie || "").split("; ").find((value) => value.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null;
  }

  async function csrf() {
    const existing = getCookie("csrftoken");
    if (existing) return existing;
    const response = await fetch(`${API_BASE}auth/csrf/`, { credentials: "same-origin" });
    if (!response.ok) throw new Error(t("securityTokenFailed"));
    return getCookie("csrftoken");
  }

  function hostElement() {
    return document.querySelector(".nav-actions, .page-actions");
  }

  function ensureUI() {
    const host = hostElement();
    if (!host || host.querySelector("[data-notification-root]")) return;
    const root = document.createElement("div");
    root.className = "notifications-root";
    root.dataset.notificationRoot = "true";
    root.innerHTML = `<button class="notification-button" id="notification-toggle" type="button" aria-expanded="false" aria-label="${t("notifications")}" title="${t("notifications")}"><svg class="notification-glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 9.6a6 6 0 0 0-12 0c0 6.1-2.4 7.2-2.4 8.4h16.8C20.4 16.8 18 15.7 18 9.6Z"/><path d="M9.7 20.2h4.6"/><path d="M12 2.1v1.2"/><path d="m4.1 4.2.9.9"/><path d="m19.9 4.2-.9.9"/><path d="M20.4 12.2h1.2"/></svg><b data-notification-count hidden>۰</b></button><div class="notifications-panel" id="notifications-panel" hidden><div class="notifications-heading"><div><span class="notifications-kicker">NEXORA</span><strong data-notifications-title>${t("notifications")}</strong></div><button class="notifications-read-all" id="notifications-read-all" type="button">${t("markAllRead")}</button></div><div class="notifications-list" id="notifications-list"></div></div>`;
    host.prepend(root);
    root.querySelector("#notification-toggle").addEventListener("click", () => {
      const panel = root.querySelector("#notifications-panel");
      const open = panel.hidden;
      panel.hidden = !open;
      root.querySelector("#notification-toggle").setAttribute("aria-expanded", String(open));
    });
    root.querySelector("#notifications-read-all").addEventListener("click", markAllRead);
    document.addEventListener("click", (event) => {
      if (!root.contains(event.target)) {
        root.querySelector("#notifications-panel").hidden = true;
        root.querySelector("#notification-toggle").setAttribute("aria-expanded", "false");
      }
    });
  }

  function render() {
    ensureUI();
    const root = document.querySelector("[data-notification-root]");
    if (!root) return;
    const unread = items.filter((item) => !item.is_read).length;
    const count = root.querySelector("[data-notification-count]");
    count.hidden = unread === 0;
    count.textContent = new Intl.NumberFormat(locale()).format(unread);
    const toggle = root.querySelector("#notification-toggle");
    toggle.setAttribute("aria-label", t("notifications"));
    toggle.title = t("notifications");
    root.querySelector("[data-notifications-title]").textContent = t("notifications");
    root.querySelector("#notifications-read-all").textContent = t("markAllRead");
    const list = root.querySelector("#notifications-list");
    if (!authenticated) {
      list.innerHTML = `<div class="notifications-empty"><span>♢</span><p>${t("loginToNotifications")}</p><a href="/account/">${t("login")}</a></div>`;
      return;
    }
    if (!items.length) {
      list.innerHTML = `<div class="notifications-empty"><span>✦</span><p>${t("noNotifications")}</p></div>`;
      return;
    }
    list.innerHTML = items.map((item) => {
      const date = new Intl.DateTimeFormat(locale(), { month: "short", day: "numeric" }).format(new Date(item.created_at));
      const target = item.link || "#";
      return `<a class="notification-item${item.is_read ? " is-read" : ""}" href="${target}" data-notification-id="${item.id}"><span class="notification-dot" aria-hidden="true">${item.kind === "birthday" ? "🎁" : item.kind === "campaign" ? "%" : "✦"}</span><span><strong>${item.title}</strong><small>${item.body}</small><time>${date}</time></span></a>`;
    }).join("");
    list.querySelectorAll("[data-notification-id]").forEach((link) => link.addEventListener("click", () => markRead(Number(link.dataset.notificationId))));
  }

  async function load() {
    ensureUI();
    try {
      const response = await fetch(`${API_BASE}auth/notifications/?page_size=20`, { credentials: "same-origin" });
      if (response.status === 401) { authenticated = false; items = []; render(); return; }
      if (!response.ok) throw new Error("notification-request-failed");
      const data = await response.json();
      items = data.results || data || [];
      authenticated = true;
      render();
    } catch (error) {
      authenticated = false;
      items = [];
      render();
    }
  }

  async function markRead(id) {
    const item = items.find((notification) => notification.id === id);
    if (!item || item.is_read) return;
    item.is_read = true;
    render();
    try {
      await fetch(`${API_BASE}auth/notifications/${id}/read/`, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": await csrf() } });
    } catch (error) {
      // The local state is still useful if the browser goes offline briefly.
    }
  }

  async function markAllRead(event) {
    event?.preventDefault();
    items = items.map((item) => ({ ...item, is_read: true }));
    render();
    try {
      await fetch(`${API_BASE}auth/notifications/read-all/`, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": await csrf() } });
    } catch (error) {
      // Best effort; the next refresh will reconcile the state.
    }
  }

  window.addEventListener("nexora-language-changed", render);
  window.addEventListener("nexora-logged-out", () => { authenticated = false; items = []; render(); });
  document.addEventListener("DOMContentLoaded", () => { ensureUI(); load(); });
})();
