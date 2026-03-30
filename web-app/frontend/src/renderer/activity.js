import { API_BASE } from "./config.js";

function renderActivity(logs) {
  const container = document.getElementById("recent-activity");

  const isNearBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight < 50;

  container.innerHTML = logs.map(log => {
    const level = (log.level || "info").toLowerCase();

    return `
      <div class="activity-line level-${level}">
        <span class="activity-timestamp">${log.timestamp}</span>
        <span class="activity-tag">[${log.level}]</span>
        ${log.message}
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
    const res = await fetch(`${API_BASE}/activity`);
    const result = await res.json();

    const logs = result.logs || [];

    if (logs.length === 0) {
      container.innerHTML = `<div class="activity-line">No recent activity.</div>`;
      return;
    }

    renderActivity(logs);

  } catch (err) {
    console.error("Activity fetch failed:", err);
  }
}