// Pages protégées : ouverture et fermeture du panneau de filtres.
document.addEventListener("DOMContentLoaded", () => {
  const panel = document.getElementById("filters-panel");
  const overlay = document.querySelector(".filters-overlay");
  const button = document.querySelector("[data-filters-open][aria-controls]");
  if (!panel) return;

  function toggle(open) {
    panel.hidden = !open;
    overlay.hidden = !open;
    if (button) button.setAttribute("aria-expanded", String(open));
    if (open) panel.querySelector("input, button").focus();
  }

  document.querySelectorAll("[data-filters-open]").forEach((el) =>
    el.addEventListener("click", () => toggle(true)));
  document.querySelectorAll("[data-filters-close]").forEach((el) =>
    el.addEventListener("click", () => toggle(false)));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) toggle(false);
  });
});
