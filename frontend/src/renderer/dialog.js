// ---------------------------------------------------------------------------
// Shared custom dialog utilities (replaces native confirm/alert to avoid
// Electron focus-loss issues on Windows)
// ---------------------------------------------------------------------------

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

/**
 * Custom confirm dialog — returns Promise<boolean>.
 */
export function confirmDialog(message, okLabel = "Delete") {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "dialog-overlay";
    overlay.innerHTML = `
      <div class="dialog-box">
        <div class="dialog-icon dialog-icon--danger">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <p class="dialog-message">${escapeHtml(message)}</p>
        <div class="dialog-actions">
          <button class="dialog-btn dialog-btn--cancel">Cancel</button>
          <button class="dialog-btn dialog-btn--danger">${escapeHtml(okLabel)}</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => overlay.classList.add("dialog-visible"));

    const finish = (val) => {
      overlay.classList.remove("dialog-visible");
      overlay.addEventListener("transitionend", () => overlay.remove(), { once: true });
      // Fallback removal in case transitionend doesn't fire
      setTimeout(() => overlay.remove(), 200);
      resolve(val);
    };

    overlay.querySelector(".dialog-btn--danger").addEventListener("click", () => finish(true));
    overlay.querySelector(".dialog-btn--cancel").addEventListener("click", () => finish(false));
    overlay.addEventListener("keydown", (e) => {
      if (e.key === "Escape") finish(false);
      if (e.key === "Enter") finish(true);
    });
    // Click backdrop to cancel
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) finish(false);
    });
    overlay.querySelector(".dialog-btn--cancel").focus();
  });
}

/**
 * Custom alert dialog — returns Promise<void>.
 */
export function alertDialog(message) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "dialog-overlay";
    overlay.innerHTML = `
      <div class="dialog-box">
        <div class="dialog-icon dialog-icon--info">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </div>
        <p class="dialog-message">${escapeHtml(message)}</p>
        <div class="dialog-actions">
          <button class="dialog-btn dialog-btn--primary">OK</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    requestAnimationFrame(() => overlay.classList.add("dialog-visible"));

    const finish = () => {
      overlay.classList.remove("dialog-visible");
      overlay.addEventListener("transitionend", () => overlay.remove(), { once: true });
      setTimeout(() => overlay.remove(), 200);
      resolve();
    };

    overlay.querySelector(".dialog-btn--primary").addEventListener("click", finish);
    overlay.addEventListener("keydown", (e) => {
      if (e.key === "Escape" || e.key === "Enter") finish();
    });
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) finish();
    });
    overlay.querySelector(".dialog-btn--primary").focus();
  });
}
