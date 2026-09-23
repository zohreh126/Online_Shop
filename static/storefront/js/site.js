function setupSiteChrome() {
  const root = document.documentElement;
  const themeButton = document.querySelector("#theme-toggle");
  const menuButton = document.querySelector("#menu-toggle");
  const mobileNav = document.querySelector("#mobile-nav");
  if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark");
  const updateThemeButton = () => { if (themeButton) themeButton.textContent = root.classList.contains("dark") ? "☼" : "☾"; };
  themeButton?.addEventListener("click", () => { root.classList.toggle("dark"); localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light"); updateThemeButton(); });
  menuButton?.addEventListener("click", () => {
    if (!mobileNav) return;
    const open = mobileNav.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(Boolean(open)));
    menuButton.setAttribute("aria-label", open ? "بستن منو" : "باز کردن منو");
  });
  mobileNav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => mobileNav.classList.remove("open")));
  updateThemeButton();
}

function setupFAQ() {
  document.querySelectorAll(".faq-question").forEach((button) => button.addEventListener("click", () => {
    const item = button.closest(".faq-item");
    const answer = item?.querySelector(".faq-answer");
    const open = button.getAttribute("aria-expanded") === "true";
    document.querySelectorAll(".faq-item").forEach((other) => {
      other.querySelector(".faq-question")?.setAttribute("aria-expanded", "false");
      const otherAnswer = other.querySelector(".faq-answer");
      if (otherAnswer) otherAnswer.hidden = true;
      other.classList.remove("open");
    });
    if (!open && answer) {
      button.setAttribute("aria-expanded", "true");
      answer.hidden = false;
      item.classList.add("open");
    }
  }));
}

document.addEventListener("DOMContentLoaded", () => { setupSiteChrome(); setupFAQ(); });
