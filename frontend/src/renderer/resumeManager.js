import { authFetch } from "./auth.js";

// ---------------------------------------------------------------------------
// API — all requests carry Bearer token via authFetch
// ---------------------------------------------------------------------------

async function fetchContributors() {
  try {
    const res = await authFetch("/showcase/users");
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.data) ? data.data : [];
  } catch (_) { return []; }
}

async function fetchProjects() {
  try {
    const res = await authFetch("/dashboard/recent-projects");
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (_) { return []; }
}

async function fetchResumes() {
  try {
    // user_id is resolved server-side from Bearer token
    const res = await authFetch("/resumes");
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data.data) ? data.data : [];
  } catch (_) { return []; }
}

async function generateResume(projectIds, title, contributorId) {
  const body = { create_new: true };
  if (projectIds?.length) body.project_ids = projectIds;
  if (title) body.resume_title = title;
  // Only pass user_id when user explicitly chose a contributor (collaborative project)
  if (contributorId) body.user_id = Number(contributorId);

  const res = await authFetch("/resumes/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to generate resume");
  return data.data;
}

async function deleteResume(resumeId) {
  const res = await authFetch(`/resumes/${resumeId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete resume");
}

async function fetchResumeDetail(resumeId) {
  const res = await authFetch(`/resumes/${resumeId}`);
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

  container.innerHTML = `<p class="resume-summary-text">Loading...</p>`;
  const resumes = await fetchResumes();

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
      <div class="resume-list-card" data-resume-id="${r.id}">
        <div class="resume-list-card-header">
          <div class="resume-list-card-body">
            <div class="resume-list-title">${r.title || "Untitled Resume"}</div>
            <div class="resume-list-meta">
              ${r.target_role ? `<span>${r.target_role}</span> · ` : ""}
              <span>${sectionCount} section${sectionCount !== 1 ? "s" : ""}</span> ·
              <span>Updated ${date}</span>
            </div>
          </div>
          <div class="resume-list-actions">
            <button class="danger-btn resume-delete-action" data-resume-id="${r.id}">Delete</button>
            <span class="resume-expand-chevron">▾</span>
          </div>
        </div>
        <div class="resume-list-expand">
          <div class="resume-list-expand-inner"></div>
        </div>
      </div>
    `;
  }).join("");

  container.querySelectorAll(".resume-list-card").forEach((card) => {
    const header = card.querySelector(".resume-list-card-header");
    const expandEl = card.querySelector(".resume-list-expand");
    const inner = card.querySelector(".resume-list-expand-inner");
    const chevron = card.querySelector(".resume-expand-chevron");
    const resumeId = card.dataset.resumeId;
    let loaded = false;

    header.addEventListener("click", async (e) => {
      if (e.target.closest(".resume-delete-action")) return;

      const isOpen = card.classList.contains("expanded");
      if (isOpen) {
        card.classList.remove("expanded");
        expandEl.style.maxHeight = "0";
        chevron.style.transform = "";
        return;
      }

      card.classList.add("expanded");
      chevron.style.transform = "rotate(180deg)";

      if (!loaded) {
        inner.innerHTML = `<p class="resume-summary-text" style="padding:16px">Loading...</p>`;
        expandEl.style.maxHeight = "200px";
        try {
          const resume = await fetchResumeDetail(resumeId);
          inner.innerHTML = buildResumeHtml(resume);
          loaded = true;
        } catch (_) {
          inner.innerHTML = `<p class="resume-summary-text" style="padding:16px">Failed to load.</p>`;
        }
      }

      // Let the DOM paint before measuring real height
      requestAnimationFrame(() => {
        expandEl.style.maxHeight = inner.scrollHeight + 32 + "px";
      });
    });
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

  const projectListHtml = projects.length
    ? projects.map((p) => {
        const isCollab = (p.contributor_count || 0) > 1;
        const badgeClass = isCollab ? "badge-collaborative" : "badge-individual";
        const badgeLabel = isCollab ? "Collaborative" : "Individual";
        return `
          <label class="resume-modal-checkbox-row">
            <input type="checkbox" class="project-checkbox"
              value="${p.project_id}"
              data-label="${p.project_id.toLowerCase()}"
              data-collaborative="${isCollab}" />
            <span class="resume-modal-checkbox-label">
              <span class="resume-modal-item-name">
                ${p.project_id}
                <span class="project-classification-badge ${badgeClass}" style="margin-left:6px">${badgeLabel}</span>
              </span>
              <span class="resume-modal-item-meta">${p.total_files} files · ${p.total_skills} skills</span>
            </span>
          </label>
        `;
      }).join("")
    : `<p class="resume-summary-text">No projects found. Upload a project first.</p>`;

  const contributorListHtml = contributors.length
    ? contributors.map((c) => `
        <label class="resume-modal-radio-row">
          <input type="radio" name="contributor" value="${c.id}" data-label="${c.username.toLowerCase()}" />
          <span class="resume-modal-item-name">${c.username}</span>
        </label>
      `).join("")
    : `<p class="resume-summary-text">No contributors found for these projects.</p>`;

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

          <!-- Projects -->
          <div class="resume-modal-section">
            <div class="resume-modal-section-title">Select projects to include</div>
            <input id="project-search" type="text" class="resume-modal-search" placeholder="Search projects..." />
            <div class="resume-modal-list" id="project-list">
              ${projectListHtml}
            </div>
          </div>

          <!-- Contributor — hidden until a collaborative project is selected -->
          <div class="resume-modal-section hidden" id="contributor-section">
            <div class="resume-modal-section-title">Who are you?</div>
            <input id="contributor-search" type="text" class="resume-modal-search" placeholder="Search contributors..." />
            <div class="resume-modal-list" id="contributor-list">
              ${contributorListHtml}
            </div>
          </div>

          <!-- Title -->
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

  // Close
  document.getElementById("close-resume-modal").onclick = () => modal.remove();
  modal.querySelector(".upload-overlay").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) modal.remove();
  });

  // Show/hide contributor section based on whether any checked project is collaborative
  function updateContributorSection() {
    const checkedBoxes = [...modal.querySelectorAll(".project-checkbox:checked")];
    const hasCollaborative = checkedBoxes.some((cb) => cb.dataset.collaborative === "true");
    const section = document.getElementById("contributor-section");
    section.classList.toggle("hidden", !hasCollaborative);
  }

  modal.addEventListener("change", (e) => {
    if (e.target.classList.contains("project-checkbox")) updateContributorSection();
  });

  // Project search
  document.getElementById("project-search")?.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    modal.querySelectorAll("#project-list .resume-modal-checkbox-row").forEach((row) => {
      row.style.display = row.querySelector("input").dataset.label.includes(q) ? "" : "none";
    });
  });

  // Contributor search
  document.getElementById("contributor-search")?.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    modal.querySelectorAll("#contributor-list .resume-modal-radio-row").forEach((row) => {
      row.style.display = row.querySelector("input").dataset.label.includes(q) ? "" : "none";
    });
  });

  // Generate
  document.getElementById("resume-generate-btn").addEventListener("click", async () => {
    const errorEl = document.getElementById("resume-modal-error");
    const checkedProjects = [...modal.querySelectorAll(".project-checkbox:checked")];

    if (!checkedProjects.length) {
      errorEl.textContent = "Please select at least one project.";
      errorEl.classList.remove("hidden");
      return;
    }

    const hasCollaborative = checkedProjects.some((cb) => cb.dataset.collaborative === "true");
    const selectedContributor = modal.querySelector("input[name='contributor']:checked");

    if (hasCollaborative && !selectedContributor) {
      errorEl.textContent = "Please select who you are for the collaborative project(s).";
      errorEl.classList.remove("hidden");
      return;
    }

    errorEl.classList.add("hidden");
    const generateBtn = document.getElementById("resume-generate-btn");
    generateBtn.disabled = true;
    generateBtn.textContent = "Generating...";

    const projectIds = checkedProjects.map((cb) => cb.value);
    const title = document.getElementById("resume-title-input")?.value.trim() || "";
    // Only pass contributorId for collaborative projects; individual projects use session user
    const contributorId = selectedContributor?.value || null;

    try {
      await generateResume(projectIds, title, contributorId);
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
  document.getElementById("new-resume-btn")?.addEventListener("click", openNewResumeModal);

  document.addEventListener("auth:mode-changed", (e) => {
    if (e.detail?.isPrivate) {
      // Logged in: backend resolves user_id from token, just render
      renderResumeList();
    } else {
      // Logged out / public mode
      const container = document.getElementById("resume-list-container");
      if (container) {
        container.innerHTML = `<p class="resume-summary-text">Click "New Resume" to create your first resume.</p>`;
      }
    }
  });
}
