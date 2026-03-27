import { getLastPage, initNavigation, switchPage } from "./navigation.js";
import { loadProjects } from "./projects.js";
import { loadRecentProjects } from "./recentProjects.js";
import { loadProjectHealth } from "./projectHealth.js";
import { loadErrorAnalysis } from "./errors.js";
import { loadMostUsedSkills } from "./skills.js";
import { refreshConsentUI, renderConsentSettings, setConsentSettingsMessage } from "./consentBanner.js";
import { maybeShowOnboardingForAudience, reopenOnboarding } from "./onboarding.js";
import { shouldRequireLoginForTab, shouldRequireLoginForSettingsTab } from "./authShared.mjs";
import { notifyPortfolioDataUpdated } from "./portfolioState.js";

const API_BASE = "http://127.0.0.1:8002";
const AUTH_TOKEN_KEY = "loom_auth_token";
let authMode = "login";
let currentUser = null;
let privateModeEnabled = false;
let pendingPublicPage = null;
let _educationEntries = [];
let latestConsentState = {
  local_consent: false,
  external_consent: false,
  bannerVisible: false,
};

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function setAuthToken(token) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

function showAuthModal(show) {
  const modal = document.getElementById("auth-modal");
  if (!modal) return;
  modal.classList.toggle("hidden", !show);
}

function setModeUI(isPrivate, user) {
  const modeBadge = document.getElementById("mode-badge");
  const loginBtn = document.getElementById("login-btn");
  const logoutBtn = document.getElementById("logout-btn");
  const profilePill = document.getElementById("profile-pill");
  const jobMatchTab = document.getElementById("job-match-tab");
  if (!modeBadge || !loginBtn || !logoutBtn || !profilePill || !jobMatchTab) return;

  modeBadge.textContent = isPrivate ? "Private Mode" : "Public Mode";
  modeBadge.classList.toggle("private", isPrivate);
  modeBadge.classList.toggle("public", !isPrivate);
  loginBtn.classList.toggle("hidden", isPrivate);
  logoutBtn.classList.toggle("hidden", !isPrivate);
  jobMatchTab.classList.remove("hidden");
  jobMatchTab.setAttribute("aria-hidden", "false");
  jobMatchTab.tabIndex = 0;

  if (isPrivate && user) {
    profilePill.textContent = user.username || `User ${user.id || ""}`;
    profilePill.classList.remove("hidden");
    currentUser = user;
    privateModeEnabled = true;
  } else {
    profilePill.classList.add("hidden");
    currentUser = null;
    privateModeEnabled = false;
  }

  // Let other UI modules react 
  document.dispatchEvent(
    new CustomEvent("auth:mode-changed", {
      detail: {
        isPrivate: privateModeEnabled,
        user: currentUser,
      },
    })
  );
}

export function isPrivateMode() {
  return privateModeEnabled;
}

export function getCurrentUser() {
  return currentUser;
}

function setAuthFormMode(mode) {
  authMode = mode === "register" ? "register" : "login";
  const title = document.getElementById("auth-title");
  const subtitle = document.getElementById("auth-subtitle");
  const emailInput = document.getElementById("auth-email");
  const githubUrlInput = document.getElementById("auth-github-url");
  const submit = document.getElementById("auth-submit");
  const toggleBtn = document.getElementById("auth-toggle");
  const error = document.getElementById("auth-error");
  if (!title || !subtitle || !emailInput || !submit || !toggleBtn || !error) return;

  error.textContent = "";
  if (authMode === "register") {
    title.textContent = "Register";
    subtitle.textContent = "Create account to enter Private Mode";
    emailInput.classList.remove("hidden");
    githubUrlInput?.classList.remove("hidden");
    submit.textContent = "Register";
    toggleBtn.textContent = "Already have an account? Login";
  } else {
    title.textContent = "Login";
    subtitle.textContent = "Enter Private Mode";
    emailInput.classList.add("hidden");
    githubUrlInput?.classList.add("hidden");
    submit.textContent = "Login";
    toggleBtn.textContent = "Need an account? Register";
  }
}

function setActiveTabByKey(tabKey) {
  document.querySelectorAll(".nav-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === tabKey);
  });
}

function activateSettingsTab(tab = "general") {
  document.querySelectorAll(".settings-nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.settingsTab === tab);
  });
  document.querySelectorAll(".settings-tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `settings-tab-${tab}`);
  });
}

async function ensureConsentState() {
  // Reuse the shared consent 
  try {
    latestConsentState = await refreshConsentUI();
  } catch (_) {
    latestConsentState = {
      local_consent: false,
      external_consent: false,
      bannerVisible: false,
    };
  }
  return latestConsentState;
}

function showConsentRequiredSettings(message = "Grant consent in Privacy & Consent before using Ask Sienna.") {
  // Ask Sienna is gated by consent
  showSavedPage("settings", "settings-page");
  activateSettingsTab("privacy");
  renderSettingsProfile();
  setConsentSettingsMessage(message);
}

function goToPage(tabKey, pageId) {
  switchPage(pageId);
  setActiveTabByKey(tabKey);
  localStorage.setItem("loom_last_page", JSON.stringify({ tabKey, pageId }));
}

function showSavedPage(tabKey, pageId) {
  if (!tabKey || !pageId) return;
  switchPage(pageId);
  setActiveTabByKey(tabKey);
}

function getActivePageSnapshot() {
  const activeTab = document.querySelector(".nav-tab.active");
  const activePage = document.querySelector(".page.active");
  const tabKey = activeTab?.dataset.tab || "";
  const pageId = activePage?.id || activeTab?.dataset.page || "";
  if (!tabKey || !pageId) return null;
  return { tabKey, pageId };
}

function restoreLastAllowedPage({ requirePrivate = false } = {}) {
  const lastPage = getLastPage();
  const privateOnlyTabs = new Set(["customization"]);

  if (lastPage?.tabKey && lastPage?.pageId) {
    const requiresPrivateTab = privateOnlyTabs.has(lastPage.tabKey);
    if (!requiresPrivateTab || requirePrivate) {
      goToPage(lastPage.tabKey, lastPage.pageId);
      if (lastPage.tabKey === "settings") {
        renderSettingsProfile();
      }
      return true;
    }
  }

  return false;
}

function restoreSavedPageOptimistically() {
  const lastPage = getLastPage();
  if (!lastPage?.tabKey || !lastPage?.pageId) return false;
  showSavedPage(lastPage.tabKey, lastPage.pageId);
  return true;
}

export async function authFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(`${API_BASE}${path}`, { ...options, headers });
}

export function hasAuthToken() {
  return Boolean(getAuthToken());
}

async function ensureCurrentUser() {
  if (currentUser) return currentUser;
  if (!getAuthToken()) return null;
  try {
    const res = await authFetch("/auth/me");
    if (!res.ok) return null;
    const data = await res.json();
    currentUser = data.user || null;
    if (currentUser) setModeUI(true, currentUser);
    return currentUser;
  } catch (_) {
    return null;
  }
}

export async function openLoginFlow() {
  let mode = "login";
  try {
    const res = await authFetch("/auth/bootstrap");
    if (res.ok) {
      const boot = await res.json();
      mode = boot.has_users ? "login" : "register";
    }
  } catch (_) {}
  setAuthFormMode(mode);
  showAuthModal(true);
}

export async function openSettingsAndPromptLogin(settingsTab = "account") {
  showSavedPage("settings", "settings-page");
  const fallbackSettingsTab = shouldRequireLoginForSettingsTab(settingsTab, currentUser)
    ? "privacy"
    : settingsTab;
  pendingPublicPage = {
    tabKey: "settings",
    pageId: "settings-page",
    settingsTab: fallbackSettingsTab,
  };
  activateSettingsTab(fallbackSettingsTab);
  renderSettingsProfile();
  if (shouldRequireLoginForSettingsTab(settingsTab, currentUser)) {
    setConsentSettingsMessage("");
    await openLoginFlow();
  }
}

function renderSettingsProfile() {
  // ── Account tab: profile form ──────────────────────────────────
  const profileEl = document.getElementById("settings-profile");
  if (profileEl) {
    if (!currentUser) {
      profileEl.innerHTML = `<p class="settings-login-prompt">Login to view and edit your profile.</p>`;
    } else {
      profileEl.innerHTML = `
        <div class="settings-card-header">
          <h3>User Profile</h3>
          <p class="settings-card-desc">Update your personal information and public links.</p>
        </div>
        <div class="settings-form-grid">
          <label class="settings-form-label">Username</label>
          <div class="settings-form-value">${currentUser.username || "-"}</div>
          <label class="settings-form-label" for="pf-email">Email</label>
          <input id="pf-email" class="settings-input" value="${currentUser.email || ""}" />
          <label class="settings-form-label" for="pf-full-name">Full Name</label>
          <input id="pf-full-name" class="settings-input" value="${currentUser.full_name || ""}" />
          <label class="settings-form-label" for="pf-phone">Phone</label>
          <input id="pf-phone" class="settings-input" value="${currentUser.phone_number || ""}" />
          <label class="settings-form-label" for="pf-city">City</label>
          <input id="pf-city" class="settings-input" value="${currentUser.city || ""}" />
          <label class="settings-form-label" for="pf-state">State / Region</label>
          <input id="pf-state" class="settings-input" value="${currentUser.state_region || ""}" />
          <label class="settings-form-label" for="pf-github">GitHub URL</label>
          <input id="pf-github" class="settings-input" value="${currentUser.github_url || ""}" />
          <label class="settings-form-label" for="pf-portfolio">Portfolio URL</label>
          <input id="pf-portfolio" class="settings-input" value="${currentUser.portfolio_url || ""}" />
        </div>

        <div class="settings-edu-section">
          <div class="settings-edu-section-header">
            <span class="settings-edu-section-title">Education</span>
            <span class="settings-edu-section-desc">Optional. Add your academic background.</span>
          </div>
          <div id="edu-cards-container" class="edu-cards-container"></div>
          <div class="edu-add-zone" id="edu-add-zone">
            <button class="edu-add-btn" id="edu-add-btn" title="Add education">＋</button>
          </div>
        </div>

        <div class="settings-form-actions">
          <button id="profile-save-btn" class="settings-save-btn">Save Profile</button>
          <span id="profile-msg" class="settings-feedback-msg"></span>
        </div>
      `;
      document.getElementById("profile-save-btn")?.addEventListener("click", saveProfile);
      document.getElementById("edu-add-btn")?.addEventListener("click", () => {
        _educationEntries.push({ university: "", degree: "", start_date: "", end_date: "" });
        _renderEduCards();
      });
      // Load education from backend then render
      authFetch("/auth/me/education").then(r => r.json()).then(data => {
        _educationEntries = Array.isArray(data.data) ? data.data : [];
        _renderEduCards();
      }).catch(() => { _educationEntries = []; _renderEduCards(); });
    }
  }

  // ── Security tab: change password ────────────────────────────
  const securityEl = document.getElementById("settings-security");
  if (securityEl) {
    if (!currentUser) {
      securityEl.innerHTML = `<p class="settings-login-prompt">Login to manage security settings.</p>`;
    } else {
      securityEl.innerHTML = `
        <div class="settings-card-header">
          <h3>Change Password</h3>
          <p class="settings-card-desc">Update your account password. New password must be at least 6 characters.</p>
        </div>
        <div class="settings-form-grid">
          <label class="settings-form-label" for="pw-current">Current Password</label>
          <input id="pw-current" class="settings-input" type="password" placeholder="Current password" />
          <label class="settings-form-label" for="pw-new">New Password</label>
          <input id="pw-new" class="settings-input" type="password" placeholder="New password (min 6 chars)" />
        </div>
        <div class="settings-form-actions">
          <button id="password-save-btn" class="settings-save-btn">Update Password</button>
          <span id="password-msg" class="settings-feedback-msg"></span>
        </div>
      `;
      document.getElementById("password-save-btn")?.addEventListener("click", changePassword);
    }
  }

  // ── Privacy tab: consent ──────────────────────────────────────
  renderConsentSettings();
}

function _renderEduCards() {
  const container = document.getElementById("edu-cards-container");
  if (!container) return;
  container.innerHTML = "";
  _educationEntries.forEach((entry, idx) => {
    const isCurrent = !entry.end_date || entry.end_date.toLowerCase() === "present";
    const card = document.createElement("div");
    card.className = "edu-card";
    card.innerHTML = `
      <button class="edu-card-delete" title="Remove" data-idx="${idx}">×</button>
      <div class="edu-card-fields">
        <input class="settings-input edu-university" placeholder="University / School" value="${entry.university || ""}" data-idx="${idx}" data-field="university" />
        <input class="settings-input edu-degree" placeholder="Degree (e.g. BSc Computer Science)" value="${entry.degree || ""}" data-idx="${idx}" data-field="degree" />
        <div class="edu-card-dates">
          <input class="settings-input edu-start" placeholder="Start (e.g. Sep 2020)" value="${entry.start_date || ""}" data-idx="${idx}" data-field="start_date" />
          <input class="settings-input edu-end" placeholder="End (e.g. May 2024)" value="${isCurrent ? "" : (entry.end_date || "")}" data-idx="${idx}" data-field="end_date" ${isCurrent ? "disabled" : ""} />
          <label class="edu-current-label">
            <input type="checkbox" class="edu-current-chk" data-idx="${idx}" ${isCurrent && entry.university ? "checked" : ""} />
            <span>Current</span>
          </label>
        </div>
        <div class="edu-card-location">
          <input class="settings-input edu-city" placeholder="City" value="${entry.city || ""}" data-idx="${idx}" data-field="city" />
          <input class="settings-input edu-state" placeholder="State / Province" value="${entry.state || ""}" data-idx="${idx}" data-field="state" />
        </div>
      </div>
    `;
    // delete
    card.querySelector(".edu-card-delete").addEventListener("click", () => {
      _educationEntries.splice(idx, 1);
      _renderEduCards();
    });
    // field edits
    card.querySelectorAll("[data-field]").forEach(input => {
      input.addEventListener("input", e => {
        _educationEntries[e.target.dataset.idx][e.target.dataset.field] = e.target.value;
      });
    });
    // current checkbox
    card.querySelector(".edu-current-chk").addEventListener("change", e => {
      const i = parseInt(e.target.dataset.idx);
      if (e.target.checked) {
        _educationEntries[i].end_date = "Present";
      } else {
        _educationEntries[i].end_date = "";
      }
      _renderEduCards();
    });
    container.appendChild(card);
  });
}

async function saveProfile() {
  const msg = document.getElementById("profile-msg");
  if (msg) msg.textContent = "Saving...";
  const payload = {
    email: document.getElementById("pf-email")?.value.trim() || null,
    full_name: document.getElementById("pf-full-name")?.value.trim() || null,
    phone_number: document.getElementById("pf-phone")?.value.trim() || null,
    city: document.getElementById("pf-city")?.value.trim() || null,
    state_region: document.getElementById("pf-state")?.value.trim() || null,
    github_url: document.getElementById("pf-github")?.value.trim() || null,
    portfolio_url: document.getElementById("pf-portfolio")?.value.trim() || null,
  };

  try {
    const [res, eduRes] = await Promise.all([
      authFetch("/auth/me", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
      authFetch("/auth/me/education", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          education: _educationEntries.filter(e => (e.university || "").trim()),
        }),
      }),
    ]);
    const data = await res.json();
    if (!res.ok) {
      if (msg) msg.textContent = `Failed: ${data.detail || "save failed"}`;
      return;
    }
    currentUser = data.user || currentUser;
    setModeUI(true, currentUser);
    if (msg) msg.textContent = "Profile saved successfully.";
  } catch (_) {
    if (msg) msg.textContent = "Failed: network error";
  }
}

async function changePassword() {
  const msg = document.getElementById("password-msg");
  const currentPassword = document.getElementById("pw-current")?.value || "";
  const newPassword = document.getElementById("pw-new")?.value || "";

  if (!currentPassword || !newPassword) {
    if (msg) msg.textContent = "Please fill in both password fields.";
    return;
  }

  if (newPassword.length < 6) {
    if (msg) msg.textContent = "New password must be at least 6 characters.";
    return;
  }

  if (msg) msg.textContent = "Saving...";

  try {
    const res = await authFetch("/auth/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      if (msg) msg.textContent = `Failed: ${data.detail || "update failed"}`;
      return;
    }

    const currentEl = document.getElementById("pw-current");
    const newEl = document.getElementById("pw-new");
    if (currentEl) currentEl.value = "";
    if (newEl) newEl.value = "";

    if (msg) msg.textContent = "Password updated successfully.";
  } catch (_) {
    if (msg) msg.textContent = "Failed: network error";
  }
}

function closeModalToPublic() {
  const usernameInput = document.getElementById("auth-username");
  const emailInput = document.getElementById("auth-email");
  const githubUrlInput = document.getElementById("auth-github-url");
  const passwordInput = document.getElementById("auth-password");
  const error = document.getElementById("auth-error");
  if (usernameInput) usernameInput.value = "";
  if (emailInput) emailInput.value = "";
  if (githubUrlInput) githubUrlInput.value = "";
  if (passwordInput) passwordInput.value = "";
  if (error) error.textContent = "";
  showAuthModal(false);
  if (!currentUser && pendingPublicPage?.tabKey && pendingPublicPage?.pageId) {
    showSavedPage(pendingPublicPage.tabKey, pendingPublicPage.pageId);
    if (pendingPublicPage.tabKey === "settings") {
      activateSettingsTab(pendingPublicPage.settingsTab || "privacy");
      renderSettingsProfile();
    }
    pendingPublicPage = null;
    return;
  }
  pendingPublicPage = null;
  if (!currentUser && !restoreLastAllowedPage()) {
    goToPage("dashboard", "dashboard-page");
  }
}

async function syncCloudDbAndRefresh() {
  await Promise.all([
    loadProjects(),
    loadRecentProjects(),
    loadProjectHealth(),
    loadErrorAnalysis(),
    loadMostUsedSkills(),
  ]);
  notifyPortfolioDataUpdated();
}  

export async function initAuthFlow() {
  const loginBtn = document.getElementById("login-btn");
  const logoutBtn = document.getElementById("logout-btn");
  const submit = document.getElementById("auth-submit");
  const toggleBtn = document.getElementById("auth-toggle");
  const cancelBtn = document.getElementById("auth-cancel");
  const closeBtn = document.getElementById("auth-close");
  const modal = document.getElementById("auth-modal");
  const usernameInput = document.getElementById("auth-username");
  const emailInput = document.getElementById("auth-email");
  const passwordInput = document.getElementById("auth-password");
  const error = document.getElementById("auth-error");

  if (!loginBtn || !logoutBtn || !submit || !toggleBtn || !cancelBtn || !modal || !usernameInput || !passwordInput || !error) {
    initNavigation();
    return;
  }

  setModeUI(false, null);
  setAuthFormMode("login");
  goToPage("dashboard", "dashboard-page");

  // ── Settings tab switching ────────────────────────────────────
  document.querySelectorAll(".settings-nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.settingsTab;
      if (shouldRequireLoginForSettingsTab(tab, currentUser)) {
        // Public mode can only stay on the consent tab inside Setting
        activateSettingsTab("privacy");
        renderSettingsProfile();
        openSettingsAndPromptLogin(tab);
        return;
      }
      setConsentSettingsMessage("");
      activateSettingsTab(tab);
    });
  });

  // Tutorial button (static HTML — bound once here)
  document.getElementById("show-tutorial-btn")?.addEventListener("click", () => {
    reopenOnboarding();
  });

  // ── Logout confirmation modal ─────────────────────────────────
  const logoutModal = document.getElementById("logout-confirm-modal");
  const logoutCancelBtn = document.getElementById("logout-cancel-btn");
  const logoutConfirmBtn = document.getElementById("logout-confirm-btn");

  function showLogoutModal() {
    logoutModal?.classList.remove("hidden");
  }
  function hideLogoutModal() {
    logoutModal?.classList.add("hidden");
  }

  async function performLogout() {
    logoutBtn.disabled = true;
    setAuthToken(null);
    setModeUI(false, null);
    goToPage("dashboard", "dashboard-page");

    try {
      await authFetch("/auth/logout", { method: "POST" });
    } catch (_) {}

    await Promise.all([
      loadProjects(),
      loadRecentProjects(),
      loadProjectHealth(),
      loadErrorAnalysis(),
      loadMostUsedSkills(),
    ]);
    notifyPortfolioDataUpdated();
    await refreshConsentUI();

    logoutBtn.disabled = false;
  }

  logoutCancelBtn?.addEventListener("click", hideLogoutModal);
  logoutConfirmBtn?.addEventListener("click", async () => {
    hideLogoutModal();
    await performLogout();
  });
  logoutModal?.addEventListener("click", (e) => {
    if (e.target === logoutModal) hideLogoutModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !logoutModal?.classList.contains("hidden")) {
      hideLogoutModal();
    }
  });

  initNavigation({
    onBeforeNavigate: async ({ tabKey, target }) => {
      if (!target) return false;
      if (tabKey === "job-match" && !isPrivateMode()) {
        await openLoginFlow();
        return false;
      }
      if (tabKey === "chat") {
        const consentState = await ensureConsentState();
        if (!consentState?.external_consent) {
          // Block Sienna before opening the page 
          showConsentRequiredSettings();
          return false;
        }
      }
      if (tabKey === "settings") {
        const user = await ensureCurrentUser();
        renderSettingsProfile();
        if (user) {
          activateSettingsTab("general");
        } else {
          activateSettingsTab("privacy");
          setConsentSettingsMessage("");
        }
      }
      if (tabKey === "customization") {
        const user = await ensureCurrentUser();
        if (shouldRequireLoginForTab(tabKey, user)) {
          await openLoginFlow();
          return false;
        }
      }
      return true;
    },
  });

    try {
    const user = await ensureCurrentUser();

    if (user) {
      setModeUI(true, user);
      await syncCloudDbAndRefresh();
      const consentState = await ensureConsentState();
      if (!consentState?.bannerVisible) {
        maybeShowOnboardingForAudience(user.username || user.id || "guest");
      }
      if (!restoreLastAllowedPage({ requirePrivate: true })) {
        goToPage("dashboard", "dashboard-page");
      }
    } else {
      setAuthToken(null);
      setModeUI(false, null);
      if (!restoreLastAllowedPage()) {
        goToPage("dashboard", "dashboard-page");
      }
      // Public mode: load data from guest DB (CURRENT_USER is None on backend)
      await Promise.all([
        loadProjects(),
        loadRecentProjects(),
        loadProjectHealth(),
        loadErrorAnalysis(),
        loadMostUsedSkills(),
      ]);
      notifyPortfolioDataUpdated();
      const consentState = await ensureConsentState();
      if (!consentState?.bannerVisible) {
        maybeShowOnboardingForAudience("guest");
      }
    }
  } catch (_) {
    setAuthToken(null);
    setModeUI(false, null);
    if (!restoreLastAllowedPage()) {
      goToPage("dashboard", "dashboard-page");
    }
  }

  loginBtn.addEventListener("click", openLoginFlow);
  toggleBtn.addEventListener("click", () => {
    setAuthFormMode(authMode === "login" ? "register" : "login");
  });
  cancelBtn.addEventListener("click", closeModalToPublic);
  closeBtn?.addEventListener("click", closeModalToPublic);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModalToPublic();
  });

  submit.addEventListener("click", async () => {
  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  const email = emailInput ? emailInput.value.trim() : "";
  error.textContent = "";

  if (!username || !password) {
    error.textContent = "Username and password are required.";
    return;
  }

  const githubUrl = document.getElementById("auth-github-url")?.value.trim() || "";
  const payload =
    authMode === "register"
      ? { username, password, email: email || null, github_url: githubUrl || null }
      : { username, password };

  const path = authMode === "register" ? "/auth/register" : "/auth/login";

  try {
    const res = await authFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      error.textContent = data.detail || "Authentication failed.";
      return;
    }

    setAuthToken(data.token);
    setModeUI(true, data.user);
    showAuthModal(false);
    pendingPublicPage = null;
    goToPage("dashboard", "dashboard-page");

    await syncCloudDbAndRefresh();
    const consentState = await ensureConsentState();
    if (!consentState?.bannerVisible) {
      maybeShowOnboardingForAudience(data.user?.username || data.user?.id || "guest");
    }
  } catch (_) {
    error.textContent = "Unable to reach auth service.";
  }
});

 logoutBtn.addEventListener("click", () => {
    showLogoutModal();
  });

 window.addEventListener("consent:state-changed", (event) => {
  latestConsentState = {
    local_consent: Boolean(event.detail?.local_consent),
    external_consent: Boolean(event.detail?.external_consent),
    bannerVisible: Boolean(event.detail?.bannerVisible),
  };
  if (event.detail?.bannerVisible) return;
  maybeShowOnboardingForAudience(currentUser?.username || currentUser?.id || "guest");
 });
}
