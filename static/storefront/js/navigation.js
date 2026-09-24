(function () {
  const links = [
    { key: "shop", icon: "◈", href: () => window.location.pathname === "/" ? "#catalog" : "/" },
    { key: "discounts", icon: "%", href: () => window.location.pathname === "/" ? "#discounts" : "/discounts/" },
    { key: "whyNexora", icon: "◎", href: () => window.location.pathname === "/" ? "#why-us" : "/#why-us" },
    { key: "about", icon: "✧", href: () => "/about/" },
    { key: "contact", icon: "⌖", href: () => "/contact/" },
  ];

  const t = (key) => window.NexoraI18n?.t(key) || key;

  function renderGeneratedMenu(menu) {
    menu.innerHTML = links.map(({ key, icon, href }) => (
      `<a href="${href()}"><span class="nav-link-icon" aria-hidden="true">${icon}</span><span data-i18n="${key}">${t(key)}</span></a>`
    )).join("");
  }

  function closeMenu(menu, button) {
    menu?.classList.remove("open");
    menu?.setAttribute("aria-hidden", "true");
    button?.setAttribute("aria-expanded", "false");
    if (button) button.setAttribute("aria-label", t("openMenu"));
  }

  function bindMenuLinks(menu, button) {
    menu.querySelectorAll("a").forEach((link) => {
      if (link.dataset.navigationBound === "true") return;
      link.dataset.navigationBound = "true";
      link.addEventListener("click", () => closeMenu(menu, button));
    });
  }

  function setup() {
    const header = document.querySelector(".site-header");
    const actions = header?.querySelector(".nav-actions, .page-actions");
    if (!header || !actions) return;

    let button = actions.querySelector("#menu-toggle");
    if (!button) {
      button = document.createElement("button");
      button.className = "menu-button";
      button.id = "menu-toggle";
      button.type = "button";
      button.setAttribute("aria-controls", "mobile-nav");
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-label", t("openMenu"));
      button.textContent = "☰";
      actions.append(button);
    }
    button.setAttribute("aria-controls", "mobile-nav");
    if (!button.hasAttribute("aria-expanded")) button.setAttribute("aria-expanded", "false");
    if (!button.hasAttribute("aria-label")) button.setAttribute("aria-label", t("openMenu"));

    let menu = header.querySelector("#mobile-nav");
    if (!menu) {
      menu = document.createElement("nav");
      menu.className = "mobile-nav container";
      menu.id = "mobile-nav";
      menu.setAttribute("aria-label", t("mobileNavigation"));
      menu.dataset.navigationGenerated = "true";
      header.append(menu);
      renderGeneratedMenu(menu);
    } else if (menu.dataset.navigationGenerated === "true") {
      renderGeneratedMenu(menu);
    }
    if (!menu.hasAttribute("aria-hidden")) menu.setAttribute("aria-hidden", "true");

    if (button.dataset.navigationBound === "true") return;
    button.dataset.navigationBound = "true";
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = menu.classList.toggle("open");
      menu.setAttribute("aria-hidden", String(!open));
      button.setAttribute("aria-expanded", String(open));
      button.setAttribute("aria-label", t(open ? "closeMenu" : "openMenu"));
    });
    bindMenuLinks(menu, button);
    document.addEventListener("click", (event) => {
      if (!header.contains(event.target)) closeMenu(menu, button);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeMenu(menu, button);
    });
  }

  document.addEventListener("DOMContentLoaded", setup);
  window.addEventListener("nexora-language-changed", () => {
    const menu = document.querySelector("#mobile-nav[data-navigation-generated]");
    if (menu) {
      renderGeneratedMenu(menu);
      bindMenuLinks(menu, document.querySelector("#menu-toggle"));
    }
    const button = document.querySelector("#menu-toggle");
    if (button) button.setAttribute("aria-label", t(button.getAttribute("aria-expanded") === "true" ? "closeMenu" : "openMenu"));
    const existingMenu = document.querySelector("#mobile-nav");
    if (existingMenu) existingMenu.setAttribute("aria-label", t("mobileNavigation"));
  });
})();
