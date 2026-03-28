const WIDGET_LABELS = {
    "most-used-skills": "Most Used Skills",
    "error-analysis": "Error Analysis",
    "project-health": "Project Health",
    "recent-projects": "Recent Projects",
    "system-health": "System Health",
    "activity-log": "Activity Log",
  };
  
  let paletteState = {
    open: false,
    selectedIndex: 0,
    commands: [],
  };
  
  function inferWidgetKey(text) {
    const t = String(text || "").trim().toLowerCase();
  
    if (t.includes("most used skills")) return "most-used-skills";
    if (t.includes("error analysis")) return "error-analysis";
    if (t.includes("project health")) return "project-health";
    if (t.includes("recent projects")) return "recent-projects";
    if (t.includes("system health")) return "system-health";
    if (t.includes("activity log")) return "activity-log";
  
    return null;
  }
  
  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
  
  function findDashboardCards() {
    const existing = Array.from(document.querySelectorAll(".dashboard-card"));
    if (existing.length) return existing;
  
    const seen = new Set();
    const cards = [];
  
    document.querySelectorAll("h2, h3").forEach((heading) => {
      const key = inferWidgetKey(heading.textContent);
      if (!key) return;
  
      const card =
        heading.closest(".card, .panel, .widget-card, .widget, section, div");
  
      if (!card || seen.has(card)) return;
  
      card.classList.add("dashboard-card");
      card.dataset.widget = key;
      seen.add(card);
      cards.push(card);
    });
  
    return cards;
  }
  
  function injectAmbientLayers() {
    if (!document.querySelector(".aurora-scene")) {
      const scene = document.createElement("div");
      scene.className = "aurora-scene";
      scene.innerHTML = `
        <div class="aurora-blob aurora-a"></div>
        <div class="aurora-blob aurora-b"></div>
        <div class="aurora-blob aurora-c"></div>
        <div class="aurora-grid"></div>
        <div class="aurora-noise"></div>
        <div id="cursor-glow" class="cursor-glow"></div>
      `;
      document.body.prepend(scene);
    }
  
    if (!document.getElementById("widget-spotlight-backdrop")) {
      const backdrop = document.createElement("div");
      backdrop.id = "widget-spotlight-backdrop";
      backdrop.className = "widget-spotlight-backdrop";
      backdrop.addEventListener("click", collapseExpandedCards);
      document.body.appendChild(backdrop);
    }
  
    if (!document.getElementById("command-palette-root")) {
      const root = document.createElement("div");
      root.id = "command-palette-root";
      root.className = "command-palette-root hidden";
      root.innerHTML = `
        <div class="command-palette-overlay"></div>
        <div class="command-palette-panel">
          <div class="command-palette-header">
            <div class="command-palette-kicker">COMMAND PALETTE</div>
            <div class="command-palette-hint">⌘/Ctrl + K</div>
          </div>
          <input
            id="command-palette-input"
            class="command-palette-input"
            type="text"
            placeholder="Search actions, pages, widgets..."
            autocomplete="off"
          />
          <div id="command-palette-list" class="command-palette-list"></div>
        </div>
      `;
      document.body.appendChild(root);
  
      root.querySelector(".command-palette-overlay")?.addEventListener("click", closePalette);
    }
  }
  
  function initCursorGlow() {
    const glow = document.getElementById("cursor-glow");
    if (!glow || document.body.dataset.cursorGlowBound === "true") return;
  
    document.body.dataset.cursorGlowBound = "true";
  
    window.addEventListener("pointermove", (event) => {
      glow.style.transform = `translate(${event.clientX - 140}px, ${event.clientY - 140}px)`;
    });
  }
  
  function initRevealAnimations() {
    const cards = findDashboardCards();
    if (!cards.length) return;
  
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
          }
        });
      },
      { threshold: 0.15 }
    );
  
    cards.forEach((card, index) => {
      card.style.setProperty("--reveal-delay", `${index * 70}ms`);
      observer.observe(card);
    });
  }
  
  function initCardTilt() {
    const cards = findDashboardCards();
  
    cards.forEach((card) => {
      if (card.dataset.tiltBound === "true") return;
      card.dataset.tiltBound = "true";
  
      card.addEventListener("pointermove", (event) => {
        if (card.classList.contains("widget-fullscreen")) return;
  
        const rect = card.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
  
        const rotateY = ((x / rect.width) - 0.5) * 8;
        const rotateX = ((y / rect.height) - 0.5) * -8;
  
        card.style.transform = `translateY(-4px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.01)`;
      });
  
      card.addEventListener("pointerleave", () => {
        if (!card.classList.contains("widget-fullscreen")) {
          card.style.transform = "";
        }
      });
    });
  }
  
  function collapseExpandedCards() {
    document.querySelectorAll(".dashboard-card.widget-fullscreen").forEach((card) => {
      card.classList.remove("widget-fullscreen");
    });
  
    document.body.classList.remove("widget-mode");
    document.getElementById("widget-spotlight-backdrop")?.classList.remove("active");
  }
  
  function toggleCardExpand(card) {
    const alreadyOpen = card.classList.contains("widget-fullscreen");
    collapseExpandedCards();
  
    if (!alreadyOpen) {
      card.classList.add("widget-fullscreen");
      document.body.classList.add("widget-mode");
      document.getElementById("widget-spotlight-backdrop")?.classList.add("active");
    }
  }
  
  function initWidgetExpand() {
    const cards = findDashboardCards();
  
    cards.forEach((card) => {
      if (card.querySelector(".card-expand-btn")) return;
  
      const btn = document.createElement("button");
      btn.className = "card-expand-btn";
      btn.type = "button";
      btn.setAttribute("aria-label", "Expand widget");
      btn.innerHTML = "⤢";
  
      btn.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleCardExpand(card);
      });
  
      card.appendChild(btn);
  
      card.addEventListener("dblclick", () => toggleCardExpand(card));
    });
  
    if (document.body.dataset.expandHotkeysBound !== "true") {
      document.body.dataset.expandHotkeysBound = "true";
  
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          collapseExpandedCards();
          closePalette();
        }
      });
    }
  }
  
  function clickElementByText(text) {
    const candidates = Array.from(
      document.querySelectorAll("button, a, [role='button'], .nav-item, .tab")
    );
  
    const match = candidates.find((el) =>
      el.textContent?.trim().toLowerCase().includes(text.toLowerCase())
    );
  
    if (match) {
      match.click();
      return true;
    }
  
    return false;
  }
  
  function openWidgetByKey(key) {
    const card = document.querySelector(`.dashboard-card[data-widget="${key}"]`);
    if (!card) return false;
  
    toggleCardExpand(card);
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    return true;
  }
  
  function buildCommands() {
    return [
      {
        id: "go-dashboard",
        label: "Go to Dashboard",
        group: "Navigation",
        action: () => clickElementByText("Dashboard"),
      },
      {
        id: "go-projects",
        label: "Go to Projects",
        group: "Navigation",
        action: () => clickElementByText("Projects"),
      },
      {
        id: "go-resume",
        label: "Go to Resume",
        group: "Navigation",
        action: () => clickElementByText("Resume"),
      },
      {
        id: "go-portfolio",
        label: "Go to Portfolio",
        group: "Navigation",
        action: () => clickElementByText("Portfolio"),
      },
      {
        id: "go-job-match",
        label: "Go to Job Match",
        group: "Navigation",
        action: () => clickElementByText("Job Match"),
      },
      {
        id: "go-settings",
        label: "Go to Settings",
        group: "Navigation",
        action: () => clickElementByText("Settings"),
      },
      {
        id: "toggle-private-mode",
        label: "Toggle Private Mode",
        group: "Actions",
        action: () => clickElementByText("Private Mode"),
      },
      {
        id: "run-ai-analysis",
        label: "Run AI Analysis",
        group: "Actions",
        action: () => clickElementByText("Run AI Analysis"),
      },
      ...Object.entries(WIDGET_LABELS).map(([key, label]) => ({
        id: `expand-${key}`,
        label: `Expand ${label}`,
        group: "Widgets",
        action: () => openWidgetByKey(key),
      })),
    ];
  }
  
  function renderPalette(query = "") {
    const list = document.getElementById("command-palette-list");
    if (!list) return;
  
    const q = query.trim().toLowerCase();
    const commands = buildCommands().filter((command) =>
      `${command.label} ${command.group}`.toLowerCase().includes(q)
    );
  
    paletteState.commands = commands;
    paletteState.selectedIndex = Math.min(paletteState.selectedIndex, Math.max(commands.length - 1, 0));
  
    if (!commands.length) {
      list.innerHTML = `<div class="command-empty">No matching actions.</div>`;
      return;
    }
  
    list.innerHTML = commands
      .map((command, index) => `
        <button
          class="command-item ${index === paletteState.selectedIndex ? "active" : ""}"
          data-command-id="${escapeHtml(command.id)}"
          type="button"
        >
          <span class="command-group">${escapeHtml(command.group)}</span>
          <span class="command-label">${escapeHtml(command.label)}</span>
        </button>
      `)
      .join("");
  
    list.querySelectorAll(".command-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        const cmd = paletteState.commands.find((item) => item.id === btn.dataset.commandId);
        if (cmd) {
          closePalette();
          cmd.action();
        }
      });
    });
  }
  
  function openPalette() {
    const root = document.getElementById("command-palette-root");
    const input = document.getElementById("command-palette-input");
    if (!root || !input) return;
  
    paletteState.open = true;
    paletteState.selectedIndex = 0;
    root.classList.remove("hidden");
    renderPalette("");
    requestAnimationFrame(() => input.focus());
  }
  
  function closePalette() {
    const root = document.getElementById("command-palette-root");
    if (!root) return;
  
    paletteState.open = false;
    root.classList.add("hidden");
  }
  
  function initCommandPalette() {
    const input = document.getElementById("command-palette-input");
    if (!input || document.body.dataset.commandPaletteBound === "true") return;
  
    document.body.dataset.commandPaletteBound = "true";
  
    document.addEventListener("keydown", (event) => {
      const isCmdK =
        (event.metaKey || event.ctrlKey) &&
        event.key.toLowerCase() === "k";
  
      if (isCmdK) {
        event.preventDefault();
        if (paletteState.open) closePalette();
        else openPalette();
        return;
      }
  
      if (!paletteState.open) return;
  
      if (event.key === "ArrowDown") {
        event.preventDefault();
        paletteState.selectedIndex = Math.min(
          paletteState.selectedIndex + 1,
          Math.max(paletteState.commands.length - 1, 0)
        );
        renderPalette(input.value);
      }
  
      if (event.key === "ArrowUp") {
        event.preventDefault();
        paletteState.selectedIndex = Math.max(paletteState.selectedIndex - 1, 0);
        renderPalette(input.value);
      }
  
      if (event.key === "Enter") {
        event.preventDefault();
        const cmd = paletteState.commands[paletteState.selectedIndex];
        if (cmd) {
          closePalette();
          cmd.action();
        }
      }
  
      if (event.key === "Escape") {
        event.preventDefault();
        closePalette();
      }
    });
  
    input.addEventListener("input", () => {
      paletteState.selectedIndex = 0;
      renderPalette(input.value);
    });
  }
  
  function initWidgetSearch() {
    const input =
      document.getElementById("widget-search") ||
      Array.from(document.querySelectorAll("input")).find((el) =>
        el.placeholder?.toLowerCase().includes("search widgets")
      );
  
    if (!input || input.dataset.widgetSearchBound === "true") return;
    input.dataset.widgetSearchBound = "true";
  
    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      const cards = findDashboardCards();
  
      cards.forEach((card) => {
        const text = card.textContent?.toLowerCase() || "";
        const match = !query || text.includes(query);
  
        card.classList.toggle("widget-hidden-by-search", !match);
        card.classList.toggle("widget-match", !!query && match);
      });
    });
  }
  
  export function initDashboardFX() {
    injectAmbientLayers();
    findDashboardCards();
    initCursorGlow();
    initRevealAnimations();
    initCardTilt();
    initWidgetExpand();
    initCommandPalette();
    initWidgetSearch();
  }