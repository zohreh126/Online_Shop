function setupSiteChrome() {
  const root = document.documentElement;
  const themeButton = document.querySelector("#theme-toggle");
  const menuButton = document.querySelector("#menu-toggle");
  const mobileNav = document.querySelector("#mobile-nav");
  if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark");
  const updateThemeButton = () => { if (themeButton) themeButton.textContent = root.classList.contains("dark") ? "☼" : "☾"; };
  themeButton?.addEventListener("click", () => { root.classList.toggle("dark"); localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light"); updateThemeButton(); });
  menuButton?.addEventListener("click", () => { const open = mobileNav?.classList.toggle("open"); menuButton.setAttribute("aria-expanded", String(Boolean(open))); });
  mobileNav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => mobileNav.classList.remove("open")));
  updateThemeButton();
}

document.addEventListener("DOMContentLoaded", setupSiteChrome);
