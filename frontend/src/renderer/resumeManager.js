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
// API
// ---------------------------------------------------------------------------

async function fetchContributors() {
  try {
    const res = await fetch(`${API_BASE}/showcase/users`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.data) ? data.data : [];
  } catch (_) { return []; }
}

async function fetchProjects() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/recent-projects`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (_) { return []; }
}

async function fetchResumes(userId) {
  try {
    const res = await fetch(`${API_BASE}/resumes?user_id=${userId}`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.data) ? data.data : [];
  } catch (_) { return []; }
}

async function generateResume(userId, projectIds, title) {
  const body = { user_id: Number(userId), create_new: true };
  if (projectIds?.length) body.project_ids = projectIds;
  if (title) body.resume_title = title;

  const res = await fetch(`${API_BASE}/resumes/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
// Resume list
// ---------------------------------------------------------------------------

async function renderResumeList() {
  const container = document.getElementById("resume-list-container");
  if (!container) return;

  const userId = getSelectedUserId();
  if (!userId) {
    container.innerHTML = `<p class="resume-summary-text">Click "New Resume" to create your first resume.</p>`;
    return;
  }

  container.innerHTML = `<p class="resume-summary-text">Loading...</p>`;
  const resumes = await fetchResumes(userId);

  if (!resumes.length) {
    container.innerHTML = `<p class="resume-summary-text">No resumes yet. Click "New Resume" to generate one.</p>`;
    return;
  }

  container.innerHTML = resumes.map((r) => {
    const date = r.updated_at
      ? new Date(r.updated_at).toLocaleDateString()
      : r.created_at ? new Date(r.created_at).toLocaleDateString() : "—";
    const sectionCount = Array.isArray(r.sections) ? r.sections.length : 0;
    return `
      <div class="resume-list-card">
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
  }).join("");

  container.querySelectorAll(".resume-preview-action").forEach((btn) => {
    btn.addEventListener("click", () => openResumePreview(btn.dataset.resumeId));
  });
  container.querySelectorAll(".resume-delete-action").forEach((btn) => {
    btn.addEventListener("click", () => confirmDeleteResume(btn.dataset.resumeId));
  });
}

// ---------------------------------------------------------------------------
// New Resume modal
// ---------------------------------------------------------------------------

async function openNewResumeModal() {
  if (document.getElementById("new-resume-modal")) return;

  const [contributors, projects] = await Promise.all([fetchContributors(), fetchProjects()]);

  const modal = document.createElement("div");
  modal.id = "new-resume-modal";
  modal.innerHTML = `
    <div class="upload-overlay">
      <div class="upload-window">

        <div class="upload-header">
          <h2>New Resume</h2>
          <button id="close-resume-modal">✕</button>
        </div>

        <div class="upload-content">

          <!-- Step 1: Contributor -->
          <div class="resume-modal-section">
            <div class="resume-modal-section-title">Step 1 — Who are you?</div>
            ${contributors.length ? `
              <input id="contributor-search" type="text" class="resume-modal-search" placeholder="Search contributors..." />
              <div class="resume-modal-list" id="contributor-list">
                ${contributors.map((c) => `
                  <label class="resume-modal-radio-row">
                    <input type="radio" name="contributor" value="${c.id}" data-label="${c.username.toLowerCase()}" />
                    <span class="resume-modal-item-name">${c.username}</span>
                  </label>
                `).join("")}
              </div>
            ` : `<p class="resume-summary-text">No contributors found. Upload a project with git history first.</p>`}
          </div>

          <!-- Step 2: Projects -->
          <div class="resume-modal-section">
            <div class="resume-modal-section-title">Step 2 — Select projects to include</div>
            ${projects.length ? `
              <input id="project-search" type="text" class="resume-modal-search" placeholder="Search projects..." />
              <div class="resume-modal-list" id="project-list">
                ${projects.map((p) => `
                  <label class="resume-modal-checkbox-row">
                    <input type="checkbox" class="project-checkbox" value="${p.project_id}" data-label="${p.project_id.toLowerCase()}" checked />
                    <span class="resume-modal-checkbox-label">
                      <span class="resume-modal-item-name">${p.project_id}</span>
                      <span class="resume-modal-item-meta">${p.total_files} files · ${p.total_skills} skills</span>
                    </span>
                  </label>
                `).join("")}
              </div>
            ` : `<p class="resume-summary-text">No projects found. Upload a project first.</p>`}
          </div>

          <!-- Step 3: Title -->
          <div class="resume-modal-section">
            <div class="resume-modal-section-title">Resume title (optional)</div>
            <input id="resume-title-input" type="text" class="resume-modal-search" placeholder="e.g. Backend Developer Resume" />
          </div>

          <div id="resume-modal-error" class="resume-modal-error hidden"></div>

          <button id="resume-generate-btn" class="primary-btn" style="width:100%;margin-top:4px">
            Generate Resume
          </button>

        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Close handlers
  document.getElementById("close-resume-modal").onclick = () => modal.remove();
  modal.querySelector(".upload-overlay").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) modal.remove();
  });

  // Contributor search filter
  document.getElementById("contributor-search")?.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    modal.querySelectorAll("#contributor-list .resume-modal-radio-row").forEach((row) => {
      const label = row.querySelector("input").dataset.label;
      row.style.display = label.includes(q) ? "" : "none";
    });
  });

  // Project search filter
  document.getElementById("project-search")?.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    modal.querySelectorAll("#project-list .resume-modal-checkbox-row").forEach((row) => {
      const label = row.querySelector("input").dataset.label;
      row.style.display = label.includes(q) ? "" : "none";
    });
  });

  // Generate
  document.getElementById("resume-generate-btn").addEventListener("click", async () => {
    const errorEl = document.getElementById("resume-modal-error");
    const selectedContributor = modal.querySelector("input[name='contributor']:checked");
    if (!selectedContributor) {
      errorEl.textContent = "Please select a contributor.";
      errorEl.classList.remove("hidden");
      return;
    }

    const checkedProjects = [...modal.querySelectorAll(".project-checkbox:checked")];
    if (!checkedProjects.length) {
      errorEl.textContent = "Please select at least one project.";
      errorEl.classList.remove("hidden");
      return;
    }

    errorEl.classList.add("hidden");
    const generateBtn = document.getElementById("resume-generate-btn");
    generateBtn.disabled = true;
    generateBtn.textContent = "Generating...";

    const userId = selectedContributor.value;
    const projectIds = checkedProjects.map((cb) => cb.value);
    const title = document.getElementById("resume-title-input")?.value.trim() || "";

    try {
      await generateResume(userId, projectIds, title);
      setSelectedUserId(userId);
      modal.remove();
      await renderResumeList();
    } catch (err) {
      errorEl.textContent = `Failed: ${err.message}`;
      errorEl.classList.remove("hidden");
      generateBtn.disabled = false;
      generateBtn.textContent = "Generate Resume";
    }
  });
}

// ---------------------------------------------------------------------------
// Delete / Preview
// ---------------------------------------------------------------------------

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
  const titleEl = modal?.querySelector("h2");
  if (!modal || !body) return;

  if (titleEl) titleEl.textContent = "Resume Preview";
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
  const sectionsHtml = sections.map((sec) => {
    const items = (sec.items || []).filter((i) => i.is_enabled !== false);
    if (!items.length) return "";
    const itemsHtml = items.map((item) => {
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
    }).join("");
    return `
      <div class="resume-preview-section">
        <h3>${sec.label || sec.key}</h3>
        ${itemsHtml}
      </div>
    `;
  }).join("");

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
  renderResumeList();
  document.getElementById("new-resume-btn")?.addEventListener("click", openNewResumeModal);
}
