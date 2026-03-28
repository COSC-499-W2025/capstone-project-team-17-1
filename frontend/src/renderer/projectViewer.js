import { switchPage } from "./navigation.js";
import { authFetch } from "./auth.js";
import { renderMarkdown } from "./AskSienna/markdown.js";
const MONACO_CDN = "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min";

let _currentProjectId = null;
let _openTabs = [];
let _activeTabPath = null;
let _treeData = null;
let _analysisData = null;
let _collabData = null;
let _expandedDirs = new Set();
let _monacoEditor = null;
let _monacoLoaded = false;
let _monacoLoading = false;
let _currentFileLang = "plaintext";
let _unsavedChanges = false;

// ─── Monaco loader ────────────────────────────────────────────────

function _ensureMonaco() {
  return new Promise((resolve, reject) => {
    if (_monacoLoaded && window.monaco) { resolve(window.monaco); return; }
    if (_monacoLoading) {
      const check = setInterval(() => {
        if (window.monaco) { clearInterval(check); resolve(window.monaco); }
      }, 100);
      return;
    }
    _monacoLoading = true;

    if (!document.getElementById("monaco-loader-script")) {
      const loaderScript = document.createElement("script");
      loaderScript.id = "monaco-loader-script";
      loaderScript.src = `${MONACO_CDN}/vs/loader.js`;
      loaderScript.onload = () => {
        window.require.config({ paths: { vs: `${MONACO_CDN}/vs` } });
        window.require(["vs/editor/editor.main"], () => {
          _monacoLoaded = true;
          _monacoLoading = false;
          resolve(window.monaco);
        });
      };
      loaderScript.onerror = () => {
        _monacoLoading = false;
        reject(new Error("Failed to load Monaco Editor"));
      };
      document.head.appendChild(loaderScript);
    } else if (window.require) {
      window.require.config({ paths: { vs: `${MONACO_CDN}/vs` } });
      window.require(["vs/editor/editor.main"], () => {
        _monacoLoaded = true;
        _monacoLoading = false;
        resolve(window.monaco);
      });
    }
  });
}

function _extToMonacoLang(path) {
  const ext = path.split(".").pop().toLowerCase();
  const map = {
    py: "python", js: "javascript", ts: "typescript", jsx: "javascript",
    tsx: "typescript", java: "java", c: "c", cpp: "cpp", h: "c", hpp: "cpp",
    go: "go", rs: "rust", rb: "ruby", php: "php", swift: "swift",
    html: "html", htm: "html", css: "css", scss: "scss", less: "less",
    json: "json", yaml: "yaml", yml: "yaml", xml: "xml", svg: "xml",
    md: "markdown", mdx: "markdown", sql: "sql", sh: "shell",
    bash: "shell", ps1: "powershell", bat: "bat", dockerfile: "dockerfile",
    txt: "plaintext", log: "plaintext", csv: "plaintext", ini: "ini",
    toml: "plaintext", cfg: "plaintext", env: "plaintext",
    gitignore: "plaintext",
  };
  return map[ext] || "plaintext";
}

// ─── Public entry point ───────────────────────────────────────────

export function openProjectViewer(projectId) {
  _currentProjectId = projectId;
  _openTabs = [];
  _activeTabPath = null;
  _treeData = null;
  _analysisData = null;
  _collabData = null;
  _expandedDirs = new Set();
  _monacoEditor = null;
  _unsavedChanges = false;

  const page = document.getElementById("project-viewer-page");
  if (!page) return;

  document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
  switchPage("project-viewer-page");

  _renderShell(page, projectId);
  _activateViewerTab("view");
  _loadFileTree(projectId);
}

// ─── Shell layout ─────────────────────────────────────────────────

function _renderShell(container, projectId) {
  container.innerHTML = `
    <div class="pv-wrapper">
      <div class="pv-top-bar">
        <button class="pv-back-btn" id="pv-back-btn">&larr; Back</button>
        <h2 class="pv-title">Project: <span class="pv-project-name">${_esc(projectId)}</span></h2>
      </div>
      <div class="pv-tabs">
        <button class="pv-tab active" data-pv-tab="view">View</button>
        <button class="pv-tab" data-pv-tab="analysis">Analysis</button>
        <button class="pv-tab" data-pv-tab="collaboration">Collaboration</button>
      </div>
      <div class="pv-body">
        <div id="pv-view-panel" class="pv-panel active">
          <div class="pv-split">
            <div class="pv-sidebar" id="pv-sidebar">
              <div class="pv-tree-loading">Loading file tree...</div>
            </div>
            <div class="pv-main" id="pv-main">
              <div class="pv-file-tabs" id="pv-file-tabs"></div>
              <div class="pv-editor-toolbar" id="pv-editor-toolbar" style="display:none">
                <button id="pv-save-btn" class="pv-save-btn" title="Save (Ctrl+S)">Save</button>
                <span id="pv-save-status" class="pv-save-status"></span>
              </div>
              <div class="pv-file-content" id="pv-file-content">
                <div class="pv-empty-state">Select a file to view its contents</div>
              </div>
            </div>
          </div>
        </div>
        <div id="pv-analysis-panel" class="pv-panel">
          <div class="pv-analysis-loading">Loading analysis...</div>
        </div>
        <div id="pv-collaboration-panel" class="pv-panel">
          <div class="pv-analysis-loading">Loading collaboration data...</div>
        </div>
      </div>
    </div>
    <div id="pv-sienna-fab" class="pv-sienna-fab" title="Ask Sienna">
      <span class="pv-sienna-icon">&#9733;</span>
    </div>
    <div id="pv-sienna-panel" class="pv-sienna-panel hidden">
      <div class="pv-sienna-header">
        <span>Ask Sienna</span>
        <button id="pv-sienna-close" class="pv-sienna-close">&times;</button>
      </div>
      <div id="pv-sienna-messages" class="pv-sienna-messages">
        <div class="pv-sienna-msg assistant">Hi! I'm Sienna. Ask me anything about this project.</div>
      </div>
      <div class="pv-sienna-input-row">
        <input id="pv-sienna-input" type="text" placeholder="Ask about this project..." />
        <button id="pv-sienna-send" class="pv-sienna-send">Send</button>
      </div>
    </div>
  `;

  document.getElementById("pv-back-btn").addEventListener("click", () => {
    if (_monacoEditor) { _monacoEditor.dispose(); _monacoEditor = null; }
    switchPage("projects-page");
    document.querySelectorAll(".nav-tab").forEach(t => {
      if (t.dataset.tab === "projects") t.classList.add("active");
    });
  });

  container.querySelectorAll(".pv-tab").forEach(tab => {
    tab.addEventListener("click", () => _activateViewerTab(tab.dataset.pvTab));
  });

  document.getElementById("pv-save-btn").addEventListener("click", _saveCurrentFile);

  document.addEventListener("keydown", _handleKeydown);

  _initSienna();
}

function _handleKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") {
    if (_monacoEditor && _activeTabPath) {
      e.preventDefault();
      _saveCurrentFile();
    }
  }
}

// ─── Tab switching ────────────────────────────────────────────────

function _activateViewerTab(tabName) {
  document.querySelectorAll(".pv-tab").forEach(t =>
    t.classList.toggle("active", t.dataset.pvTab === tabName)
  );
  document.querySelectorAll(".pv-panel").forEach(p => p.classList.remove("active"));
  const panel = document.getElementById(`pv-${tabName}-panel`);
  if (panel) panel.classList.add("active");

  if (tabName === "analysis" && !_analysisData) {
    _loadAnalysis(_currentProjectId);
  }
  if (tabName === "collaboration" && !_collabData) {
    _loadCollaboration(_currentProjectId);
  }
}

// ─── File Tree ────────────────────────────────────────────────────

async function _loadFileTree(projectId) {
  const sidebar = document.getElementById("pv-sidebar");
  try {
    const res = await authFetch(`/projects/${encodeURIComponent(projectId)}/tree`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    _treeData = data.tree;
    sidebar.innerHTML = "";
    const treeEl = document.createElement("div");
    treeEl.className = "pv-tree";
    _renderTreeNodes(treeEl, _treeData, 0);
    sidebar.appendChild(treeEl);
  } catch (err) {
    sidebar.innerHTML = `<div class="pv-tree-error">Failed to load file tree</div>`;
    console.error("File tree load failed:", err);
  }
}

function _renderTreeNodes(parent, nodes, depth) {
  nodes.forEach(node => {
    const row = document.createElement("div");
    row.className = `pv-tree-item ${node.type}`;
    row.style.paddingLeft = `${12 + depth * 16}px`;

    if (node.type === "directory") {
      const isExpanded = _expandedDirs.has(node.path);
      row.innerHTML = `<span class="pv-tree-arrow ${isExpanded ? "expanded" : ""}">${isExpanded ? "&#9660;" : "&#9654;"}</span>
        <span class="pv-tree-icon">&#128193;</span>
        <span class="pv-tree-name">${_esc(node.name)}</span>`;
      parent.appendChild(row);

      const childContainer = document.createElement("div");
      childContainer.className = "pv-tree-children";
      childContainer.style.display = isExpanded ? "block" : "none";
      if (node.children) {
        _renderTreeNodes(childContainer, node.children, depth + 1);
      }
      parent.appendChild(childContainer);

      row.addEventListener("click", () => {
        const arrow = row.querySelector(".pv-tree-arrow");
        const visible = childContainer.style.display !== "none";
        childContainer.style.display = visible ? "none" : "block";
        arrow.classList.toggle("expanded", !visible);
        arrow.innerHTML = visible ? "&#9654;" : "&#9660;";
        if (visible) _expandedDirs.delete(node.path);
        else _expandedDirs.add(node.path);
      });
    } else {
      const icon = _fileIcon(node.name);
      row.innerHTML = `<span class="pv-tree-icon">${icon}</span>
        <span class="pv-tree-name">${_esc(node.name)}</span>`;
      row.addEventListener("click", () => _openFile(node.path, node.name));
      parent.appendChild(row);
    }
  });
}

function _fileIcon(name) {
  const ext = name.split(".").pop().toLowerCase();
  const iconMap = {
    py: "&#128013;", js: "&#9883;", ts: "&#9883;", jsx: "&#9883;", tsx: "&#9883;",
    json: "{ }", html: "&#127760;", css: "&#127912;", md: "&#128196;",
    png: "&#128444;", jpg: "&#128444;", jpeg: "&#128444;", gif: "&#128444;",
    svg: "&#128444;", ico: "&#128444;", webp: "&#128444;",
    sql: "&#128451;", yml: "&#9881;", yaml: "&#9881;", toml: "&#9881;",
    txt: "&#128196;", log: "&#128196;", sh: "&#128427;", bash: "&#128427;",
  };
  return iconMap[ext] || "&#128196;";
}

// ─── File tabs + content ──────────────────────────────────────────

function _openFile(path, name) {
  if (!_openTabs.find(t => t.path === path)) {
    _openTabs.push({ path, name });
  }
  _activeTabPath = path;
  _renderFileTabs();
  _loadFileContent(path);
}

function _renderFileTabs() {
  const container = document.getElementById("pv-file-tabs");
  if (!container) return;
  container.innerHTML = "";
  _openTabs.forEach(tab => {
    const el = document.createElement("div");
    el.className = `pv-file-tab ${tab.path === _activeTabPath ? "active" : ""}`;
    el.innerHTML = `<span class="pv-file-tab-name">${_esc(tab.name)}</span>
      <span class="pv-file-tab-close">&times;</span>`;
    el.querySelector(".pv-file-tab-name").addEventListener("click", () => {
      _activeTabPath = tab.path;
      _renderFileTabs();
      _loadFileContent(tab.path);
    });
    el.querySelector(".pv-file-tab-close").addEventListener("click", (e) => {
      e.stopPropagation();
      _openTabs = _openTabs.filter(t => t.path !== tab.path);
      if (_activeTabPath === tab.path) {
        _activeTabPath = _openTabs.length ? _openTabs[_openTabs.length - 1].path : null;
      }
      _renderFileTabs();
      if (_activeTabPath) _loadFileContent(_activeTabPath);
      else {
        if (_monacoEditor) { _monacoEditor.dispose(); _monacoEditor = null; }
        document.getElementById("pv-editor-toolbar").style.display = "none";
        document.getElementById("pv-file-content").innerHTML =
          '<div class="pv-empty-state">Select a file to view its contents</div>';
      }
    });
    container.appendChild(el);
  });
}

async function _loadFileContent(path) {
  const contentEl = document.getElementById("pv-file-content");
  const toolbar = document.getElementById("pv-editor-toolbar");
  contentEl.innerHTML = '<div class="pv-loading">Loading...</div>';
  toolbar.style.display = "none";
  if (_monacoEditor) { _monacoEditor.dispose(); _monacoEditor = null; }
  _unsavedChanges = false;

  try {
    const res = await authFetch(
      `/projects/${encodeURIComponent(_currentProjectId)}/file?path=${encodeURIComponent(path)}`
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.type === "image") {
      contentEl.innerHTML = `<div class="pv-image-viewer">
        <img src="data:${data.mime};base64,${data.content}" alt="${_esc(path)}" />
      </div>`;
    } else if (data.type === "text") {
      toolbar.style.display = "flex";
      document.getElementById("pv-save-status").textContent = "";
      _currentFileLang = _extToMonacoLang(path);

      contentEl.innerHTML = `<div id="pv-monaco-container" style="width:100%;height:100%;min-height:0;flex:1;"></div>`;

      try {
        await _ensureMonaco();
        const container = document.getElementById("pv-monaco-container");
        if (!container) return;

        _monacoEditor = window.monaco.editor.create(container, {
          value: data.content || "",
          language: _currentFileLang,
          theme: "vs-dark",
          automaticLayout: true,
          minimap: { enabled: true },
          fontSize: 13,
          fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          wordWrap: "on",
          tabSize: 2,
          renderWhitespace: "selection",
          bracketPairColorization: { enabled: true },
          padding: { top: 12 },
        });

        _monacoEditor.onDidChangeModelContent(() => {
          _unsavedChanges = true;
          document.getElementById("pv-save-status").textContent = "Unsaved changes";
          document.getElementById("pv-save-status").className = "pv-save-status unsaved";
        });

        _monacoEditor.addAction({
          id: "save-file",
          label: "Save File",
          keybindings: [window.monaco.KeyMod.CtrlCmd | window.monaco.KeyCode.KeyS],
          run: () => _saveCurrentFile(),
        });

      } catch {
        contentEl.innerHTML = `<div class="pv-code-viewer">
          <div class="pv-code-header"><span>${_esc(path)}</span><span class="pv-code-lang">${_esc(data.language || "")}</span></div>
          <pre class="pv-code"><code>${_highlightCode(data.content, data.language)}</code></pre>
        </div>`;
      }
    } else {
      contentEl.innerHTML = `<div class="pv-binary-viewer">
        <p>Binary file &mdash; ${_formatBytes(data.size)}</p>
        <p class="pv-binary-hint">Preview not available for this file type.</p>
      </div>`;
    }
  } catch (err) {
    contentEl.innerHTML = `<div class="pv-error">Failed to load file: ${_esc(path)}</div>`;
    console.error("File content load failed:", err);
  }
}

// ─── Save file ────────────────────────────────────────────────────

async function _saveCurrentFile() {
  if (!_monacoEditor || !_activeTabPath) return;

  const statusEl = document.getElementById("pv-save-status");
  const saveBtn = document.getElementById("pv-save-btn");
  const code = _monacoEditor.getValue();

  statusEl.textContent = "Saving...";
  statusEl.className = "pv-save-status saving";
  saveBtn.disabled = true;

  try {
    const res = await authFetch(`/projects/update-file`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: _currentProjectId,
        file_path: _activeTabPath,
        updated_code: code,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    _unsavedChanges = false;
    statusEl.textContent = "Saved";
    statusEl.className = "pv-save-status saved";
    setTimeout(() => {
      if (statusEl.textContent === "Saved") statusEl.textContent = "";
    }, 3000);
  } catch (err) {
    statusEl.textContent = `Save failed: ${err.message}`;
    statusEl.className = "pv-save-status error";
    console.error("Save failed:", err);
  } finally {
    saveBtn.disabled = false;
  }
}

// ─── Analysis Dashboard ───────────────────────────────────────────

async function _loadAnalysis(projectId) {
  const panel = document.getElementById("pv-analysis-panel");
  try {
    const [analysisRes, collabRes] = await Promise.all([
      authFetch(`/projects/${encodeURIComponent(projectId)}/analysis`),
      authFetch(`/projects/collaboration/${encodeURIComponent(projectId)}`).catch(() => null),
    ]);

    if (!analysisRes.ok) throw new Error(`HTTP ${analysisRes.status}`);
    const data = await analysisRes.json();
    _analysisData = data.analysis;

    let collabInfo = null;
    if (collabRes && collabRes.ok) {
      collabInfo = await collabRes.json();
    }

    _renderAnalysisDashboard(panel, _analysisData, collabInfo);
  } catch (err) {
    panel.innerHTML = `<div class="pv-analysis-error">
      <p>No analysis data available for this project.</p>
      <p class="pv-analysis-hint">Upload and analyze the project to see insights here.</p>
    </div>`;
    console.error("Analysis load failed:", err);
  }
}

function _renderAnalysisDashboard(container, data, collabInfo) {
  const fs = data.file_summary || {};
  const languages = data.languages || {};
  const frameworks = data.frameworks || [];
  const collab = data.collaboration || {};
  const skills = data.skills || [];
  const skillTimeline = data.skill_timeline || {};
  const warnings = data.warnings || [];
  const scanDuration = data.scan_duration_seconds;

  const langTotal = Object.values(languages).reduce((a, b) => a + b, 0) || 1;
  const langEntries = Object.entries(languages).sort((a, b) => b[1] - a[1]);

  const skillsArray = Array.isArray(skills)
    ? skills.sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
    : [];

  const topSkillsByYear = data.top_skills_by_year || {};
  const years = Object.keys(topSkillsByYear).sort();

  const isGit = Boolean(collabInfo && (collabInfo.is_git_project || collabInfo.is_github));
  const contributors = (collabInfo && collabInfo.contributors) || [];

  container.innerHTML = `
    <div class="pv-analysis-dashboard">
      <div class="pv-analysis-cards">
        <div class="pv-stat-card">
          <div class="pv-stat-value">${fs.file_count ?? "—"}</div>
          <div class="pv-stat-label">Files Scanned</div>
        </div>
        <div class="pv-stat-card">
          <div class="pv-stat-value">${langEntries.length}</div>
          <div class="pv-stat-label">Languages</div>
        </div>
        <div class="pv-stat-card">
          <div class="pv-stat-value">${frameworks.length}</div>
          <div class="pv-stat-label">Frameworks</div>
        </div>
        <div class="pv-stat-card">
          <div class="pv-stat-value">${scanDuration != null ? scanDuration.toFixed(2) + "s" : "—"}</div>
          <div class="pv-stat-label">Scan Duration</div>
        </div>
        <div class="pv-stat-card">
          <div class="pv-stat-value">${data.warning_count ?? warnings.length}</div>
          <div class="pv-stat-label">Warnings</div>
        </div>
      </div>

      <div class="pv-analysis-grid">
        <div class="pv-analysis-section">
          <h3>Languages</h3>
          <div class="pv-lang-chart">
            ${langEntries.map(([lang, count]) => {
              const pct = Math.round((count / langTotal) * 100);
              return `<div class="pv-lang-row">
                <span class="pv-lang-name">${_esc(lang)}</span>
                <div class="pv-lang-bar-bg">
                  <div class="pv-lang-bar-fill" style="width:${pct}%"></div>
                </div>
                <span class="pv-lang-pct">${pct}%</span>
              </div>`;
            }).join("")}
          </div>
        </div>

        <div class="pv-analysis-section">
          <h3>Frameworks</h3>
          <div class="pv-framework-tags">
            ${frameworks.length
              ? frameworks.map(f => `<span class="pv-tag">${_esc(f)}</span>`).join("")
              : '<span class="pv-no-data">No frameworks detected</span>'}
          </div>
        </div>

        <div class="pv-analysis-section">
          <h3>Collaboration</h3>
          <div class="pv-collab-info">
            ${collab.primary_contributor
              ? `<div class="pv-collab-row"><span class="pv-collab-label">Primary Contributor</span><span class="pv-collab-value">${_esc(collab.primary_contributor)}</span></div>`
              : ""}
            ${collab.contributors
              ? `<div class="pv-collab-row"><span class="pv-collab-label">Contributors</span><span class="pv-collab-value">${Array.isArray(collab.contributors) ? collab.contributors.length : collab.contributors}</span></div>`
              : ""}
            ${collab.classification
              ? `<div class="pv-collab-row"><span class="pv-collab-label">Classification</span><span class="pv-collab-value">${_esc(collab.classification)}</span></div>`
              : ""}
            ${collab.bot_contributors && collab.bot_contributors.length
              ? `<div class="pv-collab-row"><span class="pv-collab-label">Bots</span><span class="pv-collab-value">${collab.bot_contributors.join(", ")}</span></div>`
              : ""}
            ${!collab.primary_contributor && !collab.contributors
              ? '<span class="pv-no-data">No collaboration data available</span>'
              : ""}
          </div>
        </div>

        <div class="pv-analysis-section">
          <h3>Skills</h3>
          <div class="pv-skills-chart">
            ${skillsArray.length ? skillsArray.slice(0, 15).map(s => {
              const conf = Math.round((s.confidence || 0) * 100);
              return `<div class="pv-skill-row">
                <span class="pv-skill-name">${_esc(s.skill || s.name || "")}</span>
                <div class="pv-skill-bar-bg">
                  <div class="pv-skill-bar-fill" style="width:${conf}%"></div>
                </div>
                <span class="pv-skill-pct">${conf}%</span>
              </div>`;
            }).join("") : '<span class="pv-no-data">No skills data available</span>'}
          </div>
        </div>

        ${isGit && contributors.length ? `
        <div class="pv-analysis-section pv-full-width">
          <h3>Contributor Rankings</h3>
          <div class="pv-contributor-ranking">
            <div class="pv-ranking-header">
              <span class="pv-rank-col">#</span>
              <span class="pv-rank-name-col">Contributor</span>
              <span class="pv-rank-stat-col">Commits</span>
              <span class="pv-rank-stat-col">PRs</span>
              <span class="pv-rank-stat-col">Reviews</span>
              <span class="pv-rank-stat-col">Score</span>
            </div>
            ${contributors.slice(0, 10).map((c, i) => `
              <div class="pv-ranking-row ${i === 0 ? 'pv-rank-first' : ''}">
                <span class="pv-rank-col">${i + 1}</span>
                <span class="pv-rank-name-col">${_esc(c.name)}</span>
                <span class="pv-rank-stat-col">${c.commits}</span>
                <span class="pv-rank-stat-col">${c.prs_created}</span>
                <span class="pv-rank-stat-col">${c.pr_reviews}</span>
                <span class="pv-rank-stat-col pv-rank-score">${c.score}</span>
              </div>
            `).join("")}
          </div>
        </div>
        ` : ""}

        <div class="pv-analysis-section pv-full-width">
          <h3>Skill Timeline</h3>
          <div class="pv-timeline">
            ${years.length ? years.map(year => {
              const yearSkills = topSkillsByYear[year] || [];
              const skillNames = Array.isArray(yearSkills)
                ? yearSkills.map(s => typeof s === "string" ? s : (s.skill || s.name || ""))
                : Object.keys(yearSkills);
              return `<div class="pv-timeline-row">
                <div class="pv-timeline-year">
                  <span class="pv-timeline-dot"></span>
                  <span>${_esc(year)}</span>
                </div>
                <div class="pv-timeline-skills">
                  ${skillNames.map(sk => `<span class="pv-tag">${_esc(sk)}</span>`).join("")}
                </div>
              </div>`;
            }).join("") : '<span class="pv-no-data">No timeline data available</span>'}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ─── Collaboration Tab ────────────────────────────────────────────

async function _loadCollaboration(projectId) {
  const panel = document.getElementById("pv-collaboration-panel");
  try {
    const res = await authFetch(`/projects/collaboration/${encodeURIComponent(projectId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    _collabData = await res.json();
    _renderCollaborationTab(panel, _collabData);
  } catch (err) {
    panel.innerHTML = `<div class="pv-analysis-error">
      <p>No collaboration data available for this project.</p>
      <p class="pv-analysis-hint">Collaboration data is extracted from project analysis.</p>
    </div>`;
    console.error("Collaboration load failed:", err);
  }
}

function _renderCollaborationTab(container, data) {
  const isGit = Boolean(data.is_git_project || data.is_github);
  const contributors = data.contributors || [];
  const first = data.first_commit_date;
  const last = data.last_commit_date;
  const durationDays = data.project_duration_days || 0;
  const bots = data.bot_contributors || [];

  const durationText = durationDays > 0
    ? `${Math.floor(durationDays / 365)}y ${Math.floor((durationDays % 365) / 30)}m ${durationDays % 30}d`
    : "—";

  container.innerHTML = `
    <div class="pv-analysis-dashboard">
      <h2 class="pv-collab-title">Project Collaboration</h2>

      ${!isGit ? '<div class="pv-collab-notice"><span class="pv-notice-icon">&#9432;</span> Advanced Git metrics are only available for Git-imported projects. Showing basic collaboration data.</div>' : ''}

      <div class="pv-analysis-cards">
        <div class="pv-stat-card">
          <div class="pv-stat-value">${data.total_contributors || contributors.length}</div>
          <div class="pv-stat-label">Total Contributors</div>
        </div>
        <div class="pv-stat-card">
          <div class="pv-stat-value">${_esc(data.classification || "—")}</div>
          <div class="pv-stat-label">Classification</div>
        </div>
        <div class="pv-stat-card">
          <div class="pv-stat-value">${bots.length}</div>
          <div class="pv-stat-label">Bot Contributors</div>
        </div>
        <div class="pv-stat-card">
          <div class="pv-stat-value">${durationDays || "—"}</div>
          <div class="pv-stat-label">Days Active</div>
        </div>
      </div>

      <div class="pv-analysis-grid">
        <div class="pv-analysis-section">
          <h3>Project Timeline</h3>
          <div class="pv-collab-info">
            <div class="pv-collab-row">
              <span class="pv-collab-label">Project Start</span>
              <span class="pv-collab-value">${first ? _formatDate(first) : "—"}</span>
            </div>
            <div class="pv-collab-row">
              <span class="pv-collab-label">Last Activity</span>
              <span class="pv-collab-value">${last ? _formatDate(last) : "—"}</span>
            </div>
            <div class="pv-collab-row">
              <span class="pv-collab-label">Duration</span>
              <span class="pv-collab-value">${durationText}</span>
            </div>
            <div class="pv-collab-row">
              <span class="pv-collab-label">Primary Contributor</span>
              <span class="pv-collab-value">${_esc(data.primary_contributor || "—")}</span>
            </div>
          </div>
        </div>

        <div class="pv-analysis-section">
          <h3>Activity Period</h3>
          <div class="pv-activity-period">
            ${first && last ? `
              <div class="pv-period-visual">
                <div class="pv-period-bar">
                  <div class="pv-period-fill"></div>
                </div>
                <div class="pv-period-labels">
                  <span>${_formatMonthYear(first)}</span>
                  <span>${_formatMonthYear(last)}</span>
                </div>
              </div>
            ` : '<span class="pv-no-data">No date information available</span>'}
            ${bots.length ? `
              <div class="pv-bot-list">
                <span class="pv-collab-label">Bot Contributors:</span>
                <div class="pv-framework-tags" style="margin-top:8px">
                  ${bots.map(b => `<span class="pv-tag pv-tag-bot">${_esc(b)}</span>`).join("")}
                </div>
              </div>
            ` : ""}
          </div>
        </div>

        <div class="pv-analysis-section pv-full-width">
          <h3>Contributor Details</h3>
          ${contributors.length ? `
            <div class="pv-contributor-table">
              <div class="pv-ranking-header">
                <span class="pv-rank-col">#</span>
                <span class="pv-rank-name-col">Name</span>
                <span class="pv-rank-stat-col">Commits</span>
                ${isGit ? `
                  <span class="pv-rank-stat-col">PRs Created</span>
                  <span class="pv-rank-stat-col">PR Reviews</span>
                  <span class="pv-rank-stat-col">Lines Changed</span>
                  <span class="pv-rank-stat-col">Score</span>
                ` : ''}
              </div>
              ${contributors.map((c, i) => `
                <div class="pv-ranking-row ${i === 0 ? 'pv-rank-first' : ''}">
                  <span class="pv-rank-col">${i + 1}</span>
                  <span class="pv-rank-name-col">${_esc(c.name)}</span>
                  <span class="pv-rank-stat-col">${c.commits}</span>
                  ${isGit ? `
                    <span class="pv-rank-stat-col">${c.prs_created}</span>
                    <span class="pv-rank-stat-col">${c.pr_reviews}</span>
                    <span class="pv-rank-stat-col">${c.lines_changed}</span>
                    <span class="pv-rank-stat-col pv-rank-score">${c.score}</span>
                  ` : ''}
                </div>
              `).join("")}
            </div>
          ` : '<span class="pv-no-data">No contributor data available</span>'}
        </div>
      </div>
    </div>
  `;
}

// ─── Ask Sienna ───────────────────────────────────────────────────

function _initSienna() {
  const fab = document.getElementById("pv-sienna-fab");
  const panel = document.getElementById("pv-sienna-panel");
  const close = document.getElementById("pv-sienna-close");
  const input = document.getElementById("pv-sienna-input");
  const send = document.getElementById("pv-sienna-send");
  const messages = document.getElementById("pv-sienna-messages");

  if (!fab || !panel) return;

  fab.addEventListener("click", () => {
    panel.classList.toggle("hidden");
    if (!panel.classList.contains("hidden")) input?.focus();
  });

  close?.addEventListener("click", () => panel.classList.add("hidden"));

  const history = [];

  const handleSend = () => {
    const text = input?.value?.trim();
    if (!text) return;
    _addSiennaMessage(messages, "user", text);
    history.push({ role: "user", content: text });
    input.value = "";
    _getSiennaResponse(messages, text, history);
  };

  send?.addEventListener("click", handleSend);
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSend();
  });
}

function _addSiennaMessage(container, role, text) {
  const msg = document.createElement("div");
  msg.className = `pv-sienna-msg ${role}`;
  if (role === "assistant") {
    msg.innerHTML = renderMarkdown(text || "");
  } else {
    msg.textContent = text;
  }
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

async function _getSiennaResponse(container, question, history = []) {
  _addSiennaMessage(container, "assistant", "Thinking...");
  const thinkingEl = container.lastChild;

  try {
    const res = await authFetch("/sienna/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: question,
        project_id: _currentProjectId,
        debug: /debug|bug|error|issue|fix|inspect|trace|review code|broken|failing/i.test(question),
        history: history.slice(-10),
      }),
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = payload?.detail || "I couldn't process that right now.";
      thinkingEl.innerHTML = renderMarkdown(detail);
      history.push({ role: "assistant", content: detail });
      return;
    }
    const answer = String(payload?.text || payload?.reply || "").trim()
      || "I can only help with your Loom projects or Loom features.";
    thinkingEl.innerHTML = renderMarkdown(answer);
    history.push({ role: "assistant", content: answer });
  } catch {
    const fallback = "Sorry, I couldn't process that question right now.";
    thinkingEl.innerHTML = renderMarkdown(fallback);
    history.push({ role: "assistant", content: fallback });
  }
}

// ─── Syntax highlighting fallback (lightweight) ───────────────────

function _highlightCode(code, language) {
  const escaped = _esc(code);
  const lines = escaped.split("\n");
  return lines.map((line, i) => {
    const num = `<span class="pv-line-num">${i + 1}</span>`;
    const highlighted = _highlightLine(line, language);
    return `<span class="pv-code-line">${num}${highlighted}</span>`;
  }).join("\n");
}

function _highlightLine(line, language) {
  let result = line;
  result = result.replace(/(["'`])(?:(?!\1|\\).|\\.)*?\1/g,
    '<span class="pv-hl-string">$&</span>');
  if (["python", "bash", "ruby", "yaml"].includes(language)) {
    result = result.replace(/(#.*)$/, '<span class="pv-hl-comment">$1</span>');
  } else {
    result = result.replace(/(\/\/.*)$/, '<span class="pv-hl-comment">$1</span>');
  }
  const keywords = [
    "import", "from", "export", "default", "function", "const", "let", "var",
    "class", "def", "return", "if", "else", "elif", "for", "while", "try",
    "catch", "except", "finally", "async", "await", "yield", "new", "this",
    "self", "true", "false", "True", "False", "None", "null", "undefined",
    "interface", "type", "enum", "struct", "pub", "fn", "impl", "use",
    "package", "module", "require", "extends", "implements",
  ];
  const kwRegex = new RegExp(`\\b(${keywords.join("|")})\\b`, "g");
  result = result.replace(kwRegex, '<span class="pv-hl-keyword">$&</span>');
  result = result.replace(/\b(\d+\.?\d*)\b/g, '<span class="pv-hl-number">$&</span>');
  return result;
}

// ─── Helpers ──────────────────────────────────────────────────────

function _esc(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function _formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++; }
  return `${val.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function _formatDate(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  } catch { return dateStr; }
}

function _formatMonthYear(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short" });
  } catch { return dateStr; }
}
