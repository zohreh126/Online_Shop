(function () {
  const root = document.documentElement;
  const storageKey = "nexora-admin-theme";

  function isEnglish() {
    return (root.lang || "fa").toLowerCase().startsWith("en");
  }

  function applyTheme(theme) {
    const dark = theme === "dark";
    root.classList.toggle("nexora-admin-dark", dark);
    document.querySelectorAll("[data-admin-theme-toggle]").forEach((button) => {
      button.textContent = dark ? "☼" : "☾";
      const labels = isEnglish()
        ? { light: "Switch to light mode", dark: "Switch to dark mode" }
        : { light: "فعال‌کردن حالت روشن", dark: "فعال‌کردن حالت تیره" };
      button.setAttribute("aria-label", dark ? labels.light : labels.dark);
      button.title = button.getAttribute("aria-label");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    root.dataset.adminLanguage = isEnglish() ? "en" : "fa";
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
