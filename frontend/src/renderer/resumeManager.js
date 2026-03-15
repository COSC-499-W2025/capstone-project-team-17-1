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
          attachEditListeners(inner);
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


// ---------------------------------------------------------------------------
// Editable resume renderer
// ---------------------------------------------------------------------------

function ce(field, value, ctx = "") {
  return `<span contenteditable="true" data-field="${field}" ${ctx} class="re-editable">${value ?? ""}</span>`;
}

function ceHeader(field, value, ctx = "") {
  // Header metadata fields save via data-header-field (collected as full metadata dict)
  return `<span contenteditable="true" data-header-field="${field}" ${ctx} class="re-editable">${value ?? ""}</span>`;
}

// Build HTML for a single item card (reused for initial render + after add)
function buildItemHtml(rid, sid, sectionKey, item) {
  const iid  = item.id;
  const ctx  = `data-resume-id="${rid}" data-section-id="${sid}" data-item-id="${iid}"`;
  const del  = `<button class="re-item-delete" title="Delete item" aria-label="Delete item">×</button>`;
  const bullets = (item.bullets || []).filter(Boolean);

  if (sectionKey === "core_skill") {
    return `
      <div class="re-item">
        ${del}
        <div class="re-item-header">
          <span class="re-item-header-left">
            ${ce("title", item.title, ctx)}
            <span class="re-sep">: </span>
            ${ce("content", item.content, ctx)}
          </span>
        </div>
      </div>`;
  }

  if (sectionKey === "summary") {
    return `
      <div class="re-item">
        ${del}
        <div class="re-item-content re-editable" contenteditable="true" data-field="content" ${ctx}>${item.content || item.title || ""}</div>
      </div>`;
  }

  // education / experience / project / custom
  // Line 1: title (bold) + date range (right-aligned)
  // Line 2: subtitle (muted, own row)
  // Line 3+: location, content, bullets
  return `
    <div class="re-item">
      ${del}
      <div class="re-item-header">
        <span class="re-item-header-left">${ce("title", item.title, ctx)}</span>
        <span class="re-item-date">
          ${ce("start_date", item.start_date || "", ctx)}
          <span class="re-date-sep"> – </span>
          ${ce("end_date", item.end_date || "", ctx)}
        </span>
      </div>
      ${item.subtitle !== undefined ? `<div class="re-item-subtitle">${ce("subtitle", item.subtitle || "", ctx)}</div>` : ""}
      ${item.location ? `<div class="re-item-meta">${ce("location", item.location, ctx)}</div>` : ""}
      ${item.content  ? `<div class="re-item-content re-editable" contenteditable="true" data-field="content" ${ctx}>${item.content}</div>` : ""}
      ${bullets.length ? `
        <ul class="re-bullets">
          ${bullets.map((b) => `<li contenteditable="true" data-field="bullet" ${ctx} class="re-editable">${b}</li>`).join("")}
        </ul>` : ""}
    </div>`;
}

function buildResumeHtml(resume) {
  const rid = resume.id;
  const sections = (resume.sections || []).filter((s) => s.is_enabled !== false);

  const headerSec    = sections.find((s) => s.key === "header");
  const otherSections = sections.filter((s) => s.key !== "header");

  // === Hero: resume document title + target role ===
  const heroHtml = `
    <div class="re-hero">
      <div class="re-title">${ce("title", resume.title || "Resume", `data-resume-id="${rid}"`)}</div>
      <div class="re-role">${ce("target_role", resume.target_role || "", `data-resume-id="${rid}"`)}</div>
    </div>`;

  // === Header section — contact card (no item-delete, no add-item) ===
  let headerSecHtml = "";
  if (headerSec?.items?.length) {
    const item = headerSec.items[0];
    const meta = item.metadata || {};
    const sid  = headerSec.id, iid = item.id;
    const ctx  = `data-resume-id="${rid}" data-section-id="${sid}" data-item-id="${iid}"`;

    const fullName  = meta.full_name     || item.content || "Your Name";
    const location  = meta.location      || "";
    const email     = meta.email         || "";
    const phone     = meta.phone         || "";
    const github    = meta.github_url    || "";
    const portfolio = meta.portfolio_url || "";

    const contactParts = [
      location && ceHeader("location", location, ctx),
      email    && ceHeader("email",    email,    ctx),
      phone    && ceHeader("phone",    phone,    ctx),
    ].filter(Boolean).join(`<span class="re-sep"> · </span>`);

    const linkParts = [
      github    && ceHeader("github_url",    github,    ctx),
      portfolio && ceHeader("portfolio_url", portfolio, ctx),
    ].filter(Boolean).join(`<span class="re-sep"> · </span>`);

    headerSecHtml = `
      <div class="re-section">
        <div class="re-section-head">
          <div class="re-section-label">${ce("label", headerSec.label || "Header", `data-resume-id="${rid}" data-section-id="${sid}"`)}</div>
        </div>
        <div class="re-section-body">
          <div class="re-item">
            <div class="re-item-header">
              <span>${ceHeader("full_name", fullName, ctx)}</span>
            </div>
            ${contactParts ? `<div class="re-item-meta">${contactParts}</div>` : ""}
            ${linkParts    ? `<div class="re-item-meta-links">${linkParts}</div>` : ""}
          </div>
        </div>
      </div>`;
  }

  // === Other sections ===
  const sectionsHtml = otherSections.map((sec) => {
    const sid  = sec.id;
    const key  = sec.key || "";
    const items = (sec.items || []).filter((i) => i.is_enabled !== false);

    const itemsHtml = items.map((item) => buildItemHtml(rid, sid, key, item)).join("");

    return `
      <div class="re-section" data-section-id="${sid}">
        <div class="re-section-head">
          <div class="re-section-label">${ce("label", sec.label || sec.key, `data-resume-id="${rid}" data-section-id="${sid}"`)}</div>
          <button class="re-section-delete" data-resume-id="${rid}" data-section-id="${sid}" title="Delete section">×</button>
        </div>
        <div class="re-section-body" data-resume-id="${rid}" data-section-id="${sid}" data-section-key="${key}">
          ${itemsHtml}
        </div>
        <button class="re-add-item-btn" data-resume-id="${rid}" data-section-id="${sid}" data-section-key="${key}">+ Add item</button>
      </div>`;
  }).join("");

  return `
    <div class="re-sheet">
      ${heroHtml}
      ${headerSecHtml}
      ${sectionsHtml || ""}
      <button class="re-add-section-btn" data-resume-id="${rid}">+ Add section</button>
    </div>`;
}

// Default item fields per section type (used when adding a new item)
function defaultItemPayload(sectionKey) {
  switch (sectionKey) {
    case "education":
      return { title: "University", subtitle: "Degree", start_date: "", end_date: "", location: "" };
    case "experience":
      return { title: "Event", subtitle: "", start_date: "", end_date: "", location: "", content: "Content" };
    case "project":
      return { title: "Project Name", subtitle: "Tech Stack", start_date: "", end_date: "", content: "" };
    case "core_skill":
      return { title: "Skill Category", content: "skill1, skill2" };
    case "summary":
      return { title: "Summary", content: "Write your professional summary here." };
    default:
      return { title: "Title", subtitle: "", content: "Content" };
  }
}

// Recalculate maxHeight of the nearest accordion expand panel after content changes
function recalcExpand(container) {
  const inner  = container.closest(".resume-list-expand-inner");
  const expand = inner?.closest(".resume-list-expand");
  if (expand && inner) {
    requestAnimationFrame(() => {
      expand.style.maxHeight = inner.scrollHeight + 32 + "px";
    });
  }
}

function attachEditListeners(container) {
  // --- shared helpers (closed over container for header-field saves) ---
  function showSaved(el) {
    const existing = el.parentElement?.querySelector(".re-saved");
    if (existing) existing.remove();
    const tag = document.createElement("span");
    tag.className = "re-saved";
    tag.textContent = "Saved ✓";
    el.parentElement?.appendChild(tag);
    setTimeout(() => tag.remove(), 2000);
  }

  async function save(el) {
    const rid   = el.dataset.resumeId;
    const sid   = el.dataset.sectionId;
    const iid   = el.dataset.itemId;
    const value = el.innerText.trim();

    if (el.dataset.headerField) {
      const allHeaderEls = container.querySelectorAll(`[data-header-field][data-item-id="${iid}"]`);
      const meta = {};
      allHeaderEls.forEach((hel) => { meta[hel.dataset.headerField] = hel.innerText.trim(); });
      try {
        await authFetch(`/resumes/${rid}/sections/${sid}/items/${iid}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: meta.full_name || "", metadata: meta }),
        });
        showSaved(el);
      } catch (err) { console.error("Auto-save failed:", err); }
      return;
    }

    const field = el.dataset.field;
    try {
      if (iid) {
        if (field === "bullet") {
          const bullets = [...el.closest(".re-bullets").querySelectorAll("li")]
            .map((li) => li.innerText.trim()).filter(Boolean);
          await authFetch(`/resumes/${rid}/sections/${sid}/items/${iid}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bullets }),
          });
        } else {
          await authFetch(`/resumes/${rid}/sections/${sid}/items/${iid}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ [field]: value }),
          });
        }
      } else if (sid) {
        await authFetch(`/resumes/${rid}/sections/${sid}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ [field]: value }),
        });
      } else {
        await authFetch(`/resumes/${rid}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ [field]: value }),
        });
        if (field === "title") {
          const listTitle = document.querySelector(`.resume-list-card[data-resume-id="${rid}"] .resume-list-title`);
          if (listTitle) listTitle.textContent = value || "Untitled Resume";
        }
      }
      showSaved(el);
    } catch (err) { console.error("Auto-save failed:", err); }
  }

  // --- init a single contenteditable element ---
  function initEditable(el) {
    el.dataset.original = el.innerText.trim();

    el.addEventListener("paste", (e) => {
      e.preventDefault();
      const text = e.clipboardData.getData("text/plain");
      const sel = window.getSelection();
      if (!sel.rangeCount) return;
      sel.deleteFromDocument();
      sel.getRangeAt(0).insertNode(document.createTextNode(text));
      sel.collapseToEnd();
    });

    if (!el.dataset.headerField && el.dataset.field === "bullet") {
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const newLi = document.createElement("li");
          newLi.contentEditable = "true";
          newLi.className = "re-editable";
          newLi.dataset.field = "bullet";
          newLi.dataset.resumeId = el.dataset.resumeId;
          newLi.dataset.sectionId = el.dataset.sectionId;
          newLi.dataset.itemId = el.dataset.itemId;
          el.after(newLi);
          newLi.focus();
          initEditable(newLi);
        } else if (e.key === "Backspace" && el.innerText.trim() === "") {
          e.preventDefault();
          const prev = el.previousElementSibling;
          el.remove();
          prev?.focus();
          save(el);
        }
      });
    } else {
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter") e.preventDefault();
      });
    }

    el.addEventListener("blur", () => {
      if (el.innerText.trim() !== el.dataset.original) {
        el.dataset.original = el.innerText.trim();
        save(el);
      }
    });
  }

  // init all existing editable fields in container
  function initAllEditables(root) {
    root.querySelectorAll(".re-editable[data-field], .re-editable[data-header-field]").forEach(initEditable);
  }

  initAllEditables(container);

  // --- single delegated click handler on the root container ---
  container.addEventListener("click", async (e) => {

    // Delete item
    const delItemBtn = e.target.closest(".re-item-delete");
    if (delItemBtn) {
      const card   = delItemBtn.closest(".re-item");
      const anyEl  = card?.querySelector("[data-resume-id]");
      if (!anyEl) return;
      const { resumeId: rid, sectionId: sid, itemId: iid } = anyEl.dataset;
      if (!confirm("Delete this item?")) return;
      try {
        await authFetch(`/resumes/${rid}/sections/${sid}/items/${iid}`, { method: "DELETE" });
        card.remove();
        recalcExpand(container);
      } catch (_) { alert("Failed to delete item."); }
      return;
    }

    // Delete section
    const delSecBtn = e.target.closest(".re-section-delete");
    if (delSecBtn) {
      const { resumeId: rid, sectionId: sid } = delSecBtn.dataset;
      const secEl = container.querySelector(`.re-section[data-section-id="${sid}"]`);
      if (!confirm("Delete this entire section?")) return;
      try {
        await authFetch(`/resumes/${rid}/sections/${sid}`, { method: "DELETE" });
        secEl?.remove();
        recalcExpand(container);
      } catch (_) { alert("Failed to delete section."); }
      return;
    }

    // Add item
    const addItemBtn = e.target.closest(".re-add-item-btn");
    if (addItemBtn) {
      const { resumeId: rid, sectionId: sid, sectionKey: key } = addItemBtn.dataset;
      try {
        const res  = await authFetch(`/resumes/${rid}/sections/${sid}/items`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(defaultItemPayload(key)),
        });
        const data = await res.json();
        const item = data.data;
        const body = container.querySelector(`.re-section-body[data-section-id="${sid}"]`);
        if (body && item) {
          const tmp = document.createElement("div");
          tmp.innerHTML = buildItemHtml(rid, sid, key, item).trim();
          const newCard = tmp.firstElementChild;
          body.appendChild(newCard);
          initAllEditables(newCard);
          newCard.querySelector(".re-editable")?.focus();
          recalcExpand(container);
        }
      } catch (_) { alert("Failed to add item."); }
      return;
    }

    // Add section
    const addSecBtn = e.target.closest(".re-add-section-btn");
    if (addSecBtn) {
      const rid = addSecBtn.dataset.resumeId;
      const key = `custom_${Date.now()}`;
      try {
        const secRes  = await authFetch(`/resumes/${rid}/sections`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ label: "New Section", key }),
        });
        const secData = await secRes.json();
        const sec     = secData.data;
        if (!sec) return;

        const itemRes  = await authFetch(`/resumes/${rid}/sections/${sec.id}/items`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(defaultItemPayload(key)),
        });
        const itemData = await itemRes.json();
        const item     = itemData.data;

        const itemHtml = item ? buildItemHtml(rid, sec.id, key, item) : "";
        const tmp = document.createElement("div");
        tmp.innerHTML = `
          <div class="re-section" data-section-id="${sec.id}">
            <div class="re-section-head">
              <div class="re-section-label">${ce("label", sec.label, `data-resume-id="${rid}" data-section-id="${sec.id}"`)}</div>
              <button class="re-section-delete" data-resume-id="${rid}" data-section-id="${sec.id}" title="Delete section">×</button>
            </div>
            <div class="re-section-body" data-resume-id="${rid}" data-section-id="${sec.id}" data-section-key="${key}">
              ${itemHtml}
            </div>
            <button class="re-add-item-btn" data-resume-id="${rid}" data-section-id="${sec.id}" data-section-key="${key}">+ Add item</button>
          </div>`.trim();
        const newSec = tmp.firstElementChild;
        addSecBtn.before(newSec);
        initAllEditables(newSec);
        recalcExpand(container);
      } catch (_) { alert("Failed to add section."); }
    }
  });
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
