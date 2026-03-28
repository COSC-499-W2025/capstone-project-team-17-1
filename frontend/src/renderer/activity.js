function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderActivity(logs) {
  const container = document.getElementById("recent-activity");
  if (!container) return;

  const isNearBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight < 50;

  container.innerHTML = logs.map((log) => {
    const level = (log.level || "INFO").toLowerCase();
    const timestamp = escapeHtml(log.timestamp || "Unknown time");
    const label = escapeHtml(log.level || "INFO");
    const message = escapeHtml(log.message || "No message");

    return `
      <div class="activity-line level-${level}" style="display:block; visibility:visible; opacity:1;">
        <span class="activity-timestamp">${timestamp}</span>
        <span class="activity-tag">[${label}]</span>
        <span class="activity-message">${message}</span>
      </div>
    `;
  }).join("");

  if (isNearBottom) {
    container.scrollTop = container.scrollHeight;
  }
}

export async function loadRecentActivity() {
  const container = document.getElementById("recent-activity");
  if (!container) return;

  try {
    container.innerHTML = `<div class="activity-line">Loading activity...</div>`;

    const res = await fetch("http://127.0.0.1:8002/activity");

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const result = await res.json();
    const logs = Array.isArray(result) ? result : (result.logs || []);

    if (!logs.length) {
      container.innerHTML = `<div class="activity-line">No recent activity.</div>`;
      return;
    }

    renderActivity(logs);
  } catch (err) {
    console.error("Activity fetch failed:", err);
    container.innerHTML = `
      <div class="activity-line level-error">
        Failed to load activity.
      </div>
    `;
  }
}