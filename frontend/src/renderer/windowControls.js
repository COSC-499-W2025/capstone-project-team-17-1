export function initWindowControls() {
  const isMac = window.api?.platform === "darwin";
  const winControls = document.getElementById("win-controls");

  if (!isMac && winControls) {
    winControls.classList.remove("hidden");
    document.body.classList.add("win-platform");
  }

  document.getElementById("close")?.addEventListener("click", () => window.api.close());
  document.getElementById("minimize")?.addEventListener("click", () => window.api.minimize());
  document.getElementById("maximize")?.addEventListener("click", () => window.api.maximize());
}
