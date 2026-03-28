let activityState = {
  logs: [],
  filter: "all",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function getContainer() {
  return document.getElementById("recent-activity");
}

function ensureToolbar(container) {
  const parent = container.parentElement;
  if (!parent) return null;

  let toolbar = parent.querySelector(".activity-toolbar");

  if (!toolbar) {
    toolbar = document.createElement("div");
    toolbar.className = "activity-toolbar";
    toolbar.innerHTML = `
      <div class="activity-live-pill">
        <span class="live-dot"></span>
        <span>Live</span>
      </div>
      <div class="activity-filter-group">
        <button type="button" class="activity-filter-btn active" data-filter="all">All</button>
        <button type="button" class="activity-filter-btn" data-filter="info">Info</button>
        <button type="button" class="activity-filter-btn" data-filter="success">Success</button>
        <button type="button" class="activity-filter-btn" data-filter="warning">Warning</button>
        <button type="button" class="activity-filter-btn" data-filter="error">Error</button>
      </div>
    `;

    parent.insertBefore(toolbar, container);

    toolbar.addEventListener("click", (event) => {
      const button = event.target.closest(".activity-filter-btn");
      if (!button) return;

      activityState.filter = button.dataset.filter || "all";
      updateFilterButtons(toolbar);
      renderCurrentActivity();
    });
  }

  updateFilterButtons(toolbar);
  return toolbar;
}

function updateFilterButtons(toolbar) {
  toolbar.querySelectorAll(".activity-filter-btn").forEach((button) => {
    button.classList.toggle("active", button.dataset.filter === activityState.filter);
  });
}

function filteredLogs() {
  if (activityState.filter === "all") return activityState.logs;

  return activityState.logs.filter((log) => {
    return String(log.level || "").toLowerCase() === activityState.filter;
  });
}

function renderActivity(logs) {
  const container = getContainer();
  if (!container) return;

  const prevScrollTop = container.scrollTop;
  const prevScrollHeight = container.scrollHeight;
  const clientH = container.clientHeight;
  const rawDistFromBottom = prevScrollHeight - prevScrollTop - clientH;
  const hasScrollableOverflow = prevScrollHeight > clientH + 1;
  const stickToBottom =
    !hasScrollableOverflow || rawDistFromBottom <= 50;

  const visibleLogs = logs.slice(0, 24);

  container.innerHTML = visibleLogs
    .map((log) => {
      const level = String(log.level || "INFO").toLowerCase();
      const timestamp = escapeHtml(log.timestamp || "Unknown time");
      const label = escapeHtml(log.level || "INFO");
      const message = escapeHtml(log.message || "No message");

      return `
        <div class="activity-line level-${level}">
          <span class="activity-timestamp">${timestamp}</span>
          <span class="activity-tag">[${label}]</span>
          <span class="activity-message">${message}</span>
        </div>
      `;
    })
    .join("");

  requestAnimationFrame(() => {
    if (stickToBottom) {
      container.scrollTop = container.scrollHeight;
      return;
    }
    const maxScroll = Math.max(0, container.scrollHeight - container.clientHeight);
    container.scrollTop = Math.min(Math.max(0, prevScrollTop), maxScroll);
  });
}

function renderCurrentActivity() {
  const container = getContainer();
  if (!container) return;

  const logs = filteredLogs();

  if (!logs.length) {
    container.innerHTML = `<div class="activity-line">No recent activity.</div>`;
    container.scrollTop = 0;
    return;
  }

  renderActivity(logs);
}

/**
 * @param {{ silent?: boolean }} [options]
 * When `silent` is true (e.g. polling), keep existing markup until new data arrives and do not snap scroll
 * unless the user was already at the bottom.
 */
export async function loadRecentActivity(options = {}) {
  const silent = Boolean(options.silent);
  const container = getContainer();
  if (!container) return;

  ensureToolbar(container);

  try {
    if (!silent) {
      container.innerHTML = `<div class="activity-line">Loading activity...</div>`;
    }

    const res = await fetch("http://127.0.0.1:8002/activity");
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const result = await res.json();
    activityState.logs = Array.isArray(result) ? result : (result.logs || []);

    renderCurrentActivity();
  } catch (err) {
    console.error("Activity fetch failed:", err);
    if (!silent) {
      container.innerHTML = `
      <div class="activity-line level-error">
        Failed to load activity.
      </div>
    `;
    }
  }
}