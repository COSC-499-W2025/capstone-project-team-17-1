/**
 * Safe dashboard startup: wait for backend health, then load widgets with retry.
 * Skeleton loader stays visible until health is OK; individual API failures do not block the UI.
 *
 * `_dashboardRevealEpoch` coordinates reveal with guest→login reloads: a stale initDashboard
 * completion must not hide the skeleton while post-login data is still loading.
 */

const API_BASE = "http://127.0.0.1:8002";
const HEALTH_URL = `${API_BASE}/api/health`;
const RETRY_DELAY_MS = 1000;
const DEFAULT_RETRIES = 30;

let _dashboardRevealEpoch = 0;

function getDashboardShellEls() {
  const loaderEl = document.getElementById("dashboard-loader");
  const contentEl = document.getElementById("dashboard-content");
  return { loaderEl, contentEl };
}

function tryRevealDashboard(epoch) {
  const { loaderEl, contentEl } = getDashboardShellEls();
  if (!loaderEl || !contentEl) return;
  if (epoch !== _dashboardRevealEpoch) return;
  loaderEl.classList.add("hidden");
  contentEl.classList.remove("hidden");
}

/** Show skeleton grid and hide real dashboard (e.g. after login from guest mode). */
export function showDashboardSkeleton() {
  const { loaderEl, contentEl } = getDashboardShellEls();
  if (!loaderEl || !contentEl) return;
  loaderEl.classList.remove("hidden");
  contentEl.classList.add("hidden");
}

/**
 * Bump reveal epoch and show skeleton. Returns token for `finishPostLoginDashboardReload`.
 */
export function beginPostLoginDashboardReload() {
  _dashboardRevealEpoch++;
  showDashboardSkeleton();
  return _dashboardRevealEpoch;
}

/** Hide skeleton if this reload is still the active one (avoids races with initDashboard). */
export function finishPostLoginDashboardReload(epoch) {
  tryRevealDashboard(epoch);
}

/**
 * Attempts to fetch url; retries every RETRY_DELAY_MS up to `retries` times.
 * @param {string} url - Full URL to fetch
 * @param {number} retries - Max number of attempts
 * @returns {Promise<Response>} - Resolves with response on success
 * @throws {Error} - If all retries fail
 */
export async function waitForAPI(url, retries = DEFAULT_RETRIES) {
  let lastErr;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, { method: "GET" });
      if (res.ok) return res;
      lastErr = new Error(`HTTP ${res.status}`);
    } catch (err) {
      lastErr = err;
    }
    if (i < retries - 1) {
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
    }
  }
  throw lastErr;
}

const LOADER_RETRIES = 3;

/**
 * Runs a loader with retries and catches errors so one failure does not break the dashboard.
 * @param {() => Promise<void>} fn - Async loader function
 * @param {string} label - Name for logging
 */
async function runSafe(fn, label) {
  let lastErr;
  for (let attempt = 0; attempt < LOADER_RETRIES; attempt++) {
    try {
      await fn();
      return;
    } catch (err) {
      lastErr = err;
      if (attempt < LOADER_RETRIES - 1) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
      }
    }
  }
  console.warn(`[Dashboard] ${label} failed after ${LOADER_RETRIES} attempts:`, lastErr);
}

async function runDashboardWidgetLoads(deps) {
  await Promise.all([
    runSafe(deps.loadMostUsedSkills, "Most used skills"),
    runSafe(deps.loadRecentProjects, "Recent projects"),
    runSafe(deps.loadProjectHealth, "Project health"),
    runSafe(deps.loadErrorAnalysis, "Error analysis"),
    runSafe(deps.loadRecentActivity, "Recent activity"),
  ]);
}

/**
 * Waits for backend health, loads all dashboard widgets (each in try/catch),
 * then hides the skeleton loader and shows the real dashboard content.
 * @param {object} deps - Injected loaders to avoid circular deps
 */
export async function initDashboard(deps) {
  const epochAtStart = _dashboardRevealEpoch;
  const { loaderEl, contentEl } = getDashboardShellEls();
  if (!loaderEl || !contentEl) return;

  try {
    await waitForAPI(HEALTH_URL);
  } catch (err) {
    console.warn("[Dashboard] Health check failed after retries:", err);
    runSafe(() => {}, "");
  }

  await runDashboardWidgetLoads(deps);

  runSafe(deps.startMetrics, "System metrics");

  tryRevealDashboard(epochAtStart);
}
