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

export function initNavigation(options = {}) {
  const { onBeforeNavigate } = options;

  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", async () => {
      const target = tab.dataset.page;
      const tabKey = tab.dataset.tab || "";
      if (typeof onBeforeNavigate === "function") {
        const allowed = await onBeforeNavigate({ tab, tabKey, target });
        if (allowed === false) return;
      }

      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      if (target) switchPage(target);
    });
  });
}
