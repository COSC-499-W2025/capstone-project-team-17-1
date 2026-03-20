export function initWindowControls() {
  const closeButton = document.getElementById("close");
  const minimizeButton = document.getElementById("minimize");
  const maximizeButton = document.getElementById("maximize");

  closeButton?.addEventListener("click", () => window.api.close());
  minimizeButton?.addEventListener("click", () => window.api.minimize());
  maximizeButton?.addEventListener("click", () => window.api.maximize());
}
