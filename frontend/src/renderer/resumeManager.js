const API_BASE = "http://127.0.0.1:8002";

const CONTRIBUTOR_KEY = "loom_contributor_id";

function getSelectedUserId() {
  return localStorage.getItem(CONTRIBUTOR_KEY);
}

function setSelectedUserId(id) {
  if (id) localStorage.setItem(CONTRIBUTOR_KEY, String(id));
  else localStorage.removeItem(CONTRIBUTOR_KEY);
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

async function fetchContributors() {
  try {
    const res = await fetch(`${API_BASE}/showcase/users`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.data) ? data.data : [];
  } catch (_) {
    return [];
  }
}

async function fetchResumes(userId) {
  try {
    const res = await fetch(`${API_BASE}/resumes?user_id=${userId}`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.data) ? data.data : [];
  } catch (_) {
    return [];
  }
}

async function generateResume(userId) {
  const res = await fetch(`${API_BASE}/resumes/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: Number(userId), create_new: true }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to generate resume");
  return data.data;
}

async function deleteResume(resumeId) {
  const res = await fetch(`${API_BASE}/resumes/${resumeId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete resume");
}

async function fetchResumeDetail(resumeId) {
  const res = await fetch(`${API_BASE}/resumes/${resumeId}`);
  if (!res.ok) throw new Error("Failed to fetch resume");
  const data = await res.json();
  return data.data;
}

// ---------------------------------------------------------------------------
// Render: contributor selector
// ---------------------------------------------------------------------------

async function renderContributorSelector() {
  const container = document.getElementById("contributor-selector-container");
  if (!container) return;

  container.innerHTML = `<span class="resume-meta-label">Loading contributors...</span>`;

  const contributors = await fetchContributors();

  if (!contributors.length) {
    container.innerHTML = `<span class="resume-meta-label">No contributors found. Upload a project first.</span>`;
    return;
  }

  const savedId = getSelectedUserId();

  const options = contributors
    .map(
      (c) =>
        `<option value="${c.id}" ${String(c.id) === savedId ? "selected" : ""}>${c.username}</option>`
    )
    .join("");

  container.innerHTML = `
    <div class="contributor-selector-row">
      <label class="resume-meta-label" for="contributor-select">I am:</label>
      <select id="contributor-select" class="contributor-select">
        <option value="">— select contributor —</option>
        ${options}
      </select>
    </div>
  `;

  const select = document.getElementById("contributor-select");
  select?.addEventListener("change", async () => {
    const id = select.value;
    setSelectedUserId(id || null);
    await renderResumeList();
  });

  // Auto-load if already saved
  if (savedId) await renderResumeList();
}

// ---------------------------------------------------------------------------
// Render: resume list
// ---------------------------------------------------------------------------

async function renderResumeList() {
  const container = document.getElementById("resume-list-container");
  if (!container) return;

  const userId = getSelectedUserId();
  if (!userId) {
    container.innerHTML = `<p class="resume-summary-text">Select a contributor above to see their resumes.</p>`;
    return;
  }

  container.innerHTML = `<p class="resume-summary-text">Loading resumes...</p>`;

  const resumes = await fetchResumes(userId);

  if (!resumes.length) {
    container.innerHTML = `<p class="resume-summary-text">No resumes yet. Click "New Resume" to generate one.</p>`;
    return;
  }

  container.innerHTML = resumes
    .map((r) => {
      const date = r.updated_at
        ? new Date(r.updated_at).toLocaleDateString()
        : r.created_at
        ? new Date(r.created_at).toLocaleDateString()
        : "—";
      const sectionCount = Array.isArray(r.sections) ? r.sections.length : 0;
      return `
        <div class="resume-list-card" data-resume-id="${r.id}">
          <div class="resume-list-card-body">
            <div class="resume-list-title">${r.title || "Untitled Resume"}</div>
            <div class="resume-list-meta">
              ${r.target_role ? `<span>${r.target_role}</span> · ` : ""}
              <span>${sectionCount} section${sectionCount !== 1 ? "s" : ""}</span> ·
              <span>Updated ${date}</span>
            </div>
          </div>
          <div class="resume-list-actions">
            <button class="secondary-btn resume-preview-action" data-resume-id="${r.id}">Preview</button>
            <button class="danger-btn resume-delete-action" data-resume-id="${r.id}">Delete</button>
          </div>
        </div>
      `;
    })
    .join("");

  // Attach listeners
  container.querySelectorAll(".resume-preview-action").forEach((btn) => {
    btn.addEventListener("click", () => openResumePreview(btn.dataset.resumeId));
  });
  container.querySelectorAll(".resume-delete-action").forEach((btn) => {
    btn.addEventListener("click", () => confirmDeleteResume(btn.dataset.resumeId));
  });
}

// ---------------------------------------------------------------------------
// Actions: generate, delete, preview
// ---------------------------------------------------------------------------

async function handleNewResume() {
  const userId = getSelectedUserId();
  if (!userId) {
    alert("Please select a contributor first.");
    return;
  }

  const btn = document.getElementById("new-resume-btn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Generating...";
  }

  try {
    await generateResume(userId);
    await renderResumeList();
  } catch (err) {
    alert(`Failed to generate resume: ${err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "New Resume";
    }
  }
}

async function confirmDeleteResume(resumeId) {
  if (!confirm("Delete this resume?")) return;
  try {
    await deleteResume(resumeId);
    await renderResumeList();
  } catch (_) {
    alert("Failed to delete resume.");
  }
}

async function openResumePreview(resumeId) {
  const modal = document.getElementById("resume-preview-modal");
  const body = document.getElementById("resume-preview-body");
  const title = modal?.querySelector("h2");
  if (!modal || !body) return;

  if (title) title.textContent = "Resume Preview";
  body.innerHTML = `<p class="resume-summary-text">Loading...</p>`;
  modal.classList.remove("hidden");

  try {
    const resume = await fetchResumeDetail(resumeId);
    body.innerHTML = buildResumeHtml(resume);
  } catch (_) {
    body.innerHTML = `<p class="resume-summary-text">Failed to load resume.</p>`;
  }
}

function buildResumeHtml(resume) {
  const sections = (resume.sections || []).filter((s) => s.is_enabled !== false);

  const sectionsHtml = sections
    .map((sec) => {
      const items = (sec.items || []).filter((i) => i.is_enabled !== false);
      if (!items.length) return "";

      const itemsHtml = items
        .map((item) => {
          const dates = [item.start_date, item.end_date].filter(Boolean).join(" – ");
          const bullets = (item.bullets || []).filter(Boolean);
          return `
            <div class="resume-preview-project">
              ${item.title ? `<div class="resume-preview-project-title">${item.title}${item.subtitle ? ` — <span style="font-weight:normal">${item.subtitle}</span>` : ""}</div>` : ""}
              ${dates || item.location ? `<div class="resume-preview-project-meta">${[dates, item.location].filter(Boolean).join(" · ")}</div>` : ""}
              ${item.content ? `<p style="margin:4px 0">${item.content}</p>` : ""}
              ${bullets.length ? `<ul>${bullets.map((b) => `<li>${b}</li>`).join("")}</ul>` : ""}
            </div>
          `;
        })
        .join("");

      return `
        <div class="resume-preview-section">
          <h3>${sec.label || sec.key}</h3>
          ${itemsHtml}
        </div>
      `;
    })
    .join("");

  return `
    <div class="resume-preview-sheet">
      <div class="resume-preview-hero">
        <h1>${resume.title || "Resume"}</h1>
        ${resume.target_role ? `<p class="resume-preview-role">${resume.target_role}</p>` : ""}
      </div>
      ${sectionsHtml || `<p class="resume-summary-text">No content yet.</p>`}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

export function initResumeManager() {
  renderContributorSelector();

  document.getElementById("new-resume-btn")?.addEventListener("click", handleNewResume);
}
