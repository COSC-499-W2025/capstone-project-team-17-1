import { initNavigation, switchPage } from "./navigation.js";
import { loadProjects } from "./projects.js";
import { loadRecentProjects } from "./recentProjects.js";
import { loadProjectHealth } from "./projectHealth.js";
import { loadErrorAnalysis } from "./errors.js";
import { loadMostUsedSkills } from "./skills.js";

const API_BASE = "http://127.0.0.1:8002";
const AUTH_TOKEN_KEY = "loom_auth_token";
let authMode = "login";
let currentUser = null;
let privateModeEnabled = false;

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
  const customizationTab = document.getElementById("customization-tab");
  if (!modeBadge || !loginBtn || !logoutBtn || !profilePill || !customizationTab) return;

  modeBadge.textContent = isPrivate ? "Private Mode" : "Public Mode";
  modeBadge.classList.toggle("private", isPrivate);
  modeBadge.classList.toggle("public", !isPrivate);
  loginBtn.classList.toggle("hidden", isPrivate);
  logoutBtn.classList.toggle("hidden", !isPrivate);
  customizationTab.classList.toggle("hidden", !isPrivate);

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
  const submit = document.getElementById("auth-submit");
  const toggleBtn = document.getElementById("auth-toggle");
  const error = document.getElementById("auth-error");
  if (!title || !subtitle || !emailInput || !submit || !toggleBtn || !error) return;

  error.textContent = "";
  if (authMode === "register") {
    title.textContent = "Register";
    subtitle.textContent = "Create account to enter Private Mode";
    emailInput.classList.remove("hidden");
    submit.textContent = "Register";
    toggleBtn.textContent = "Already have an account? Login";
  } else {
    title.textContent = "Login";
    subtitle.textContent = "Enter Private Mode";
    emailInput.classList.add("hidden");
    submit.textContent = "Login";
    toggleBtn.textContent = "Need an account? Register";
  }
}

function setActiveTabByKey(tabKey) {
  document.querySelectorAll(".nav-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === tabKey);
  });
}

function goToPage(tabKey, pageId) {
  switchPage(pageId);
  setActiveTabByKey(tabKey);
}

async function authFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(`${API_BASE}${path}`, { ...options, headers });
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

async function startLoginFlow() {
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

function renderSettingsProfile() {
  const el = document.getElementById("settings-profile");
  if (!el) return;
  if (!currentUser) {
    el.innerHTML = "<h3>User Profile</h3><p>Login to view and edit your profile.</p>";
    return;
  }

  el.innerHTML = `
    <h3>User Profile</h3>
    <div class="profile-grid">
      <div class="label">Username</div><div>${currentUser.username || "-"}</div>
      <div class="label">Email</div><input id="pf-email" value="${currentUser.email || ""}" />
      <div class="label">Full Name</div><input id="pf-full-name" value="${currentUser.full_name || ""}" />
      <div class="label">Phone</div><input id="pf-phone" value="${currentUser.phone_number || ""}" />
      <div class="label">City</div><input id="pf-city" value="${currentUser.city || ""}" />
      <div class="label">State/Region</div><input id="pf-state" value="${currentUser.state_region || ""}" />
      <div class="label">GitHub</div><input id="pf-github" value="${currentUser.github_url || ""}" />
      <div class="label">Portfolio</div><input id="pf-portfolio" value="${currentUser.portfolio_url || ""}" />
    </div>
    <div class="profile-actions">
      <button id="profile-save-btn" class="auth-btn">Save Profile</button>
      <span id="profile-msg"></span>
    </div>
    <hr />
    <h4>Change Password</h4>
    <div class="profile-grid">
      <div class="label">Current Password</div><input id="pw-current" type="password" />
      <div class="label">New Password</div><input id="pw-new" type="password" />
    </div>
    <div class="profile-actions">
      <button id="password-save-btn" class="auth-btn">Update Password</button>
      <span id="password-msg"></span>
    </div>
  `;

  document.getElementById("profile-save-btn")?.addEventListener("click", saveProfile);
  document.getElementById("password-save-btn")?.addEventListener("click", changePassword);
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
    const res = await authFetch("/auth/me", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
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
  const passwordInput = document.getElementById("auth-password");
  const error = document.getElementById("auth-error");
  if (usernameInput) usernameInput.value = "";
  if (emailInput) emailInput.value = "";
  if (passwordInput) passwordInput.value = "";
  if (error) error.textContent = "";
  showAuthModal(false);
  if (!currentUser) goToPage("dashboard", "dashboard-page");
}

async function syncCloudDbAndRefresh() {
  try {
    await authFetch("/cloud/db/download", {
      method: "POST"
    });

    await authFetch("/cloud/projects/download-all", {
      method: "POST"
    });
  } catch (_) {
    // ignore if user has no cloud data yet
  }

  await Promise.all([
    loadProjects(),
    loadRecentProjects(),
    loadProjectHealth(),
    loadErrorAnalysis(),
    loadMostUsedSkills(),
  ]);
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
  goToPage("dashboard", "dashboard-page");
  setAuthFormMode("login");

  initNavigation({
    onBeforeNavigate: async ({ tabKey, target }) => {
      if (!target) return false;
      if (tabKey === "settings") {
        const user = await ensureCurrentUser();
        if (!user) {
          await startLoginFlow();
          return false;
        }
        renderSettingsProfile();
      }
      if (tabKey === "customization") {
        const user = await ensureCurrentUser();
        if (!user) {
          await startLoginFlow();
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
      goToPage("customization", "customization-page");
    } else {
      setAuthToken(null);
      setModeUI(false, null);
      goToPage("dashboard", "dashboard-page");
    }
  } catch (_) {
    setAuthToken(null);
    setModeUI(false, null);
    goToPage("dashboard", "dashboard-page");
  }

  loginBtn.addEventListener("click", startLoginFlow);
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

  const payload =
    authMode === "register"
      ? { username, password, email: email || null }
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

    await authFetch("/cloud/db/download", { method: "POST" });
    await authFetch("/cloud/projects/download-all", { method: "POST" });

    await syncCloudDbAndRefresh();

    showAuthModal(false);
    goToPage("customization", "customization-page");
  } catch (_) {
    error.textContent = "Unable to reach auth service.";
  }
});

 logoutBtn.addEventListener("click", async () => {
  try {
    await authFetch("/auth/logout", { method: "POST" });
  } catch (_) {}

  setAuthToken(null);
  setModeUI(false, null);
  goToPage("dashboard", "dashboard-page");

  await Promise.all([
    loadProjects(),
    loadRecentProjects(),
    loadProjectHealth(),
    loadErrorAnalysis(),
    loadMostUsedSkills(),
  ]);
});
}
