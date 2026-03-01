const toggle = document.querySelector(".theme-toggle")

toggle.addEventListener("click", () => {
  document.body.classList.toggle("light")
  document.body.classList.toggle("dark")
})

document.getElementById("close").addEventListener("click", () => window.api.close())
document.getElementById("minimize").addEventListener("click", () => window.api.minimize())
document.getElementById("maximize").addEventListener("click", () => window.api.maximize())