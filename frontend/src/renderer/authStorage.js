/**
 * Central auth token + "remember me" persistence.
 * - remember ON: token in localStorage (survives app restart)
 * - remember OFF: token in sessionStorage only (cleared when the session ends)
 * Preference is stored in localStorage even when the token is session-only.
 */

export const AUTH_TOKEN_KEY = "loom_auth_token";
export const REMEMBER_LOGIN_STORAGE_KEY = "loom_remember_login";

/**
 * One-time migration: existing installs had token in localStorage with no preference key.
 * Treat that as "remember me" so users are not logged out on upgrade.
 */
export function migrateLegacyAuthStorage() {
  try {
    if (localStorage.getItem(REMEMBER_LOGIN_STORAGE_KEY) != null) return;
    const localTok = localStorage.getItem(AUTH_TOKEN_KEY);
    const sessTok = sessionStorage.getItem(AUTH_TOKEN_KEY);
    if (localTok && !sessTok) {
      localStorage.setItem(REMEMBER_LOGIN_STORAGE_KEY, "1");
    }
  } catch (_) {
    /* ignore */
  }
}

/** @returns {boolean | null} true/false, or null if never set (legacy / fresh install) */
export function getRememberLoginPreference() {
  try {
    const v = localStorage.getItem(REMEMBER_LOGIN_STORAGE_KEY);
    if (v === "0") return false;
    if (v === "1") return true;
    return null;
  } catch (_) {
    return null;
  }
}

export function setRememberLoginPreference(persist) {
  try {
    localStorage.setItem(REMEMBER_LOGIN_STORAGE_KEY, persist ? "1" : "0");
  } catch (_) {
    /* ignore */
  }
}

export function clearStoredAuthTokens() {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
  } catch (_) {
    /* ignore */
  }
}

export function getStoredAuthToken() {
  try {
    const pref = getRememberLoginPreference();
    if (pref === false) {
      return sessionStorage.getItem(AUTH_TOKEN_KEY);
    }
    if (pref === true) {
      return localStorage.getItem(AUTH_TOKEN_KEY);
    }
    const localTok = localStorage.getItem(AUTH_TOKEN_KEY);
    if (localTok) return localTok;
    return sessionStorage.getItem(AUTH_TOKEN_KEY);
  } catch (_) {
    return null;
  }
}

/**
 * @param {string | null} token
 * @param {{ persistent: boolean }} options
 */
export function setStoredAuthToken(token, { persistent }) {
  if (!token) {
    clearStoredAuthTokens();
    return;
  }
  setRememberLoginPreference(persistent);
  try {
    if (persistent) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
      sessionStorage.removeItem(AUTH_TOKEN_KEY);
    } else {
      sessionStorage.setItem(AUTH_TOKEN_KEY, token);
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch (_) {
    /* ignore */
  }
}

/**
 * Move the current token between storages without changing the string (settings toggle).
 * @param {string} token
 * @param {boolean} persistent
 */
export function relocateStoredAuthToken(token, persistent) {
  if (!token) return;
  setStoredAuthToken(token, { persistent });
}
