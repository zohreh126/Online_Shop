function setupSiteChrome() {
  const root = document.documentElement;
  const themeButton = document.querySelector("#theme-toggle");
  if (localStorage.getItem("nexora-theme") === "dark") root.classList.add("dark");
  const updateThemeButton = () => { if (themeButton) themeButton.textContent = root.classList.contains("dark") ? "☼" : "☾"; };
  if (themeButton && themeButton.dataset.themeBound !== "true") {
    themeButton.dataset.themeBound = "true";
    themeButton.addEventListener("click", () => { root.classList.toggle("dark"); localStorage.setItem("nexora-theme", root.classList.contains("dark") ? "dark" : "light"); updateThemeButton(); });
  }
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
