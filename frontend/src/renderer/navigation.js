export function switchPage(targetId) {
  const pages = document.querySelectorAll(".page");

  pages.forEach(page => {
    page.classList.remove("active");
  });

  const target = document.getElementById(targetId);
  if (target) {
    target.classList.add("active");
  }
}

export function initNavigation() {

document.querySelectorAll(".nav-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");

    const target = tab.dataset.page;
    if (target) switchPage(target);
  });
});

}