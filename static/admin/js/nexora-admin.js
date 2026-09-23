(function () {
  const root = document.documentElement;
  const storageKey = "nexora-admin-theme";

  function applyTheme(theme) {
    const dark = theme === "dark";
    root.classList.toggle("nexora-admin-dark", dark);
    document.querySelectorAll("[data-admin-theme-toggle]").forEach((button) => {
      button.textContent = dark ? "☼" : "☾";
      button.setAttribute("aria-label", dark ? "فعال‌کردن حالت روشن" : "فعال‌کردن حالت تیره");
      button.title = button.getAttribute("aria-label");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme(localStorage.getItem(storageKey) || "light");
    document.querySelectorAll("[data-admin-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = root.classList.contains("nexora-admin-dark") ? "light" : "dark";
        localStorage.setItem(storageKey, next);
        applyTheme(next);
      });
    });
  });
})();
