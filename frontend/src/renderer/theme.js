export function initThemeToggle() {

const toggle = document.querySelector(".theme-toggle")

toggle.addEventListener("click", () => {
  document.body.classList.toggle("light")
  document.body.classList.toggle("dark")
})

}