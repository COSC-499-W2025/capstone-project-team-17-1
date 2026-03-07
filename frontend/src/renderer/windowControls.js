export function initWindowControls() {

document.getElementById("close").addEventListener("click", () => window.api.close())
document.getElementById("minimize").addEventListener("click", () => window.api.minimize())
document.getElementById("maximize").addEventListener("click", () => window.api.maximize())

}