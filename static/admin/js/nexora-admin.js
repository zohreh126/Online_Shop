(function () {
  const root = document.documentElement;
  const storageKey = "nexora-admin-theme";

  function isEnglish() {
    return (root.lang || "fa").toLowerCase().startsWith("en");
  }

  function applyTheme(theme) {
    const dark = theme === "dark";
    root.classList.toggle("nexora-admin-dark", dark);
    // Keep Django's native color variables in sync with the Nexora toggle.
    // The stock admin theme script reads this attribute before our deferred
    // script runs, so setting it here prevents light cards inside dark pages.
    root.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("theme", dark ? "dark" : "light");
    root.style.colorScheme = dark ? "dark" : "light";
    document.querySelectorAll("[data-admin-theme-toggle]").forEach((button) => {
      const icon = button.querySelector("[data-theme-icon]");
      if (icon) icon.textContent = dark ? "☼" : "☾";
      const labels = isEnglish()
        ? { light: "Switch to light mode", dark: "Switch to dark mode" }
        : { light: "فعال‌کردن حالت روشن", dark: "فعال‌کردن حالت تیره" };
      button.setAttribute("aria-label", dark ? labels.light : labels.dark);
      button.title = button.getAttribute("aria-label");
    });
  }

  const savedTheme = localStorage.getItem(storageKey) || "light";
  applyTheme(savedTheme);

  document.addEventListener("DOMContentLoaded", () => {
    root.dataset.adminLanguage = isEnglish() ? "en" : "fa";
    applyTheme(localStorage.getItem(storageKey) || savedTheme);
    document.querySelectorAll("[data-admin-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = root.classList.contains("nexora-admin-dark") ? "light" : "dark";
        localStorage.setItem(storageKey, next);
        applyTheme(next);
      });
    });
  });
})();
