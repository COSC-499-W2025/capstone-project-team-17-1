const LAST_PAGE_KEY = "loom_last_page";

function saveLastPage(tabKey, pageId) {
  if (!tabKey || !pageId) return;
  localStorage.setItem(LAST_PAGE_KEY, JSON.stringify({ tabKey, pageId }));
}

export function getLastPage() {
  try {
    const raw = localStorage.getItem(LAST_PAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.tabKey || !parsed?.pageId) return null;
    return parsed;
  } catch (_) {
    return null;
  }
}

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
      if (target) {
        switchPage(target);
        saveLastPage(tabKey, target);
      }
    });
  });
}
