(() => {
  const tr = (key) => window.NexoraI18n?.t(key) || key;

  function updateToggle(button, input) {
    const visible = input.type === "text";
    const label = tr(visible ? "hidePassword" : "showPassword");
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
    button.textContent = visible ? "◌" : "◉";
  }

  function setupPasswordToggles() {
    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
      const input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;

      if (!button.dataset.bound) {
        button.dataset.bound = "true";
        button.addEventListener("click", () => {
          input.type = input.type === "password" ? "text" : "password";
          updateToggle(button, input);
          input.focus();
        });
      }

      updateToggle(button, input);
    });
  }

  setupPasswordToggles();
  window.addEventListener("nexora-language-changed", setupPasswordToggles);
})();
