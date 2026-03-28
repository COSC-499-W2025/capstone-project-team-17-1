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

function injectFXStyles() {
  if (document.getElementById("dashboard-fx-styles")) return;

  const style = document.createElement("style");
  style.id = "dashboard-fx-styles";
  style.textContent = `
    :root {
      --fx-accent: rgba(90, 170, 255, 0.9);
      --fx-accent-soft: rgba(90, 170, 255, 0.14);
      --fx-shadow:
        0 18px 42px rgba(0, 0, 0, 0.22),
        0 8px 24px rgba(40, 80, 160, 0.10);
    }

    body {
      --scroll-progress: 0;
    }

    body.widget-mode {
      overflow: hidden;
    }

    .aurora-scene {
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      overflow: hidden;
    }

    .scroll-progress {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 3px;
      transform-origin: 0 50%;
      transform: scaleX(var(--scroll-progress));
      background: linear-gradient(
        90deg,
        rgba(90,170,255,0.95),
        rgba(120,200,255,0.95)
      );
      box-shadow: 0 0 14px rgba(90,170,255,0.45);
      z-index: 9999;
    }

    .aurora-blob {
      position: absolute;
      width: 38vw;
      height: 38vw;
      border-radius: 999px;
      filter: blur(60px);
      opacity: 0.20;
      mix-blend-mode: screen;
      animation: floatBlob 18s ease-in-out infinite alternate;
    }

    .aurora-a {
      top: -10vw;
      left: -8vw;
      background: radial-gradient(circle, rgba(90,170,255,0.45), transparent 65%);
    }

    .aurora-b {
      top: 16vh;
      right: -10vw;
      background: radial-gradient(circle, rgba(120,120,255,0.26), transparent 65%);
      animation-duration: 22s;
    }

    .aurora-c {
      bottom: -12vw;
      left: 32vw;
      background: radial-gradient(circle, rgba(90,220,255,0.18), transparent 65%);
      animation-duration: 24s;
    }

    .aurora-grid {
      position: absolute;
      inset: 0;
      background:
        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
      background-size: 56px 56px;
      mask-image: radial-gradient(circle at center, rgba(255,255,255,0.85), transparent 82%);
      opacity: 0.12;
      transform: perspective(900px) rotateX(74deg) scale(1.8) translateY(20%);
      transform-origin: center center;
    }

    .aurora-noise {
      position: absolute;
      inset: 0;
      opacity: 0.05;
      background-image:
        radial-gradient(circle at 20% 30%, rgba(255,255,255,0.5) 0 0.7px, transparent 1px),
        radial-gradient(circle at 70% 50%, rgba(255,255,255,0.4) 0 0.7px, transparent 1px);
      background-size: 180px 180px, 220px 220px;
    }

    .cursor-glow {
      position: fixed;
      width: 240px;
      height: 240px;
      left: 0;
      top: 0;
      border-radius: 999px;
      pointer-events: none;
      z-index: 1;
      background: radial-gradient(circle, rgba(90,170,255,0.16) 0%, rgba(90,170,255,0.05) 35%, transparent 70%);
      filter: blur(10px);
      mix-blend-mode: screen;
      opacity: 0.9;
      transition: opacity 180ms ease;
    }

    .dashboard-card {
      position: relative;
      isolation: isolate;
      overflow: hidden;
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.08);
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      box-shadow: var(--fx-shadow);
      opacity: 0;
      transform: translateY(28px) scale(0.985);
      transition:
        transform 220ms cubic-bezier(.2,.8,.2,1),
        box-shadow 220ms ease,
        opacity 220ms ease,
        filter 220ms ease;
      will-change: transform;
      z-index: 1;
    }

    .dashboard-card::before {
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(
          260px circle at var(--mx, 50%) var(--my, 50%),
          rgba(255,255,255,0.10),
          transparent 42%
        );
      opacity: 0;
      transition: opacity 180ms ease;
      pointer-events: none;
    }

    .dashboard-card.is-hovered::before {
      opacity: 1;
    }

    .dashboard-card.is-visible {
      opacity: 1;
      transform: translateY(0) scale(1);
      transition-delay: var(--reveal-delay, 0ms);
    }

    .dashboard-card.widget-match {
      box-shadow:
        0 18px 42px rgba(0,0,0,0.24),
        0 0 0 1px rgba(90,170,255,0.16),
        0 0 28px rgba(90,170,255,0.12);
    }

    .dashboard-card.widget-hidden-by-search {
      opacity: 0.22 !important;
      transform: scale(0.985);
      filter: grayscale(0.3);
      pointer-events: none;
    }

    .dashboard-card.widget-fullscreen {
      position: fixed !important;
      inset: 5vh 5vw !important;
      width: auto !important;
      height: auto !important;
      margin: 0 !important;
      z-index: 9998 !important;
      transform: none !important;
      border-radius: 26px !important;
      box-shadow:
        0 40px 100px rgba(0,0,0,0.42),
        0 0 0 1px rgba(255,255,255,0.08),
        0 0 60px rgba(90,170,255,0.14) !important;
    }

    .card-expand-btn {
      position: absolute;
      top: 14px;
      right: 14px;
      z-index: 3;
      width: 38px;
      height: 38px;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 12px;
      background: rgba(10,14,24,0.42);
      color: rgba(255,255,255,0.9);
      backdrop-filter: blur(10px);
      box-shadow: 0 6px 20px rgba(0,0,0,0.18);
      cursor: pointer;
      transition: transform 160ms ease, background 160ms ease;
    }

    .card-expand-btn:hover {
      transform: scale(1.06);
      background: rgba(20,30,50,0.62);
    }

    .widget-hotkey-badge {
      position: absolute;
      left: 14px;
      top: 14px;
      z-index: 3;
      min-width: 24px;
      height: 24px;
      padding: 0 8px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      color: rgba(255,255,255,0.86);
      background: rgba(10,14,24,0.42);
      border: 1px solid rgba(255,255,255,0.10);
      backdrop-filter: blur(8px);
    }

    .widget-spotlight-backdrop {
      position: fixed;
      inset: 0;
      z-index: 9990;
      opacity: 0;
      pointer-events: none;
      transition: opacity 220ms ease;
      background:
        radial-gradient(circle at center, rgba(10,16,28,0.14), rgba(4,6,12,0.82));
      backdrop-filter: blur(8px);
    }

    .widget-spotlight-backdrop.active {
      opacity: 1;
      pointer-events: auto;
    }

    .command-palette-root {
      position: fixed;
      inset: 0;
      z-index: 10000;
      display: grid;
      place-items: start center;
      padding-top: 10vh;
    }

    .command-palette-root.hidden {
      display: none;
    }

    .command-palette-overlay {
      position: absolute;
      inset: 0;
      background: rgba(2,6,14,0.50);
      backdrop-filter: blur(8px);
    }

    .command-palette-panel {
      position: relative;
      width: min(720px, 92vw);
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.08);
      background: linear-gradient(180deg, rgba(20,24,34,0.92), rgba(10,13,22,0.94));
      box-shadow:
        0 28px 80px rgba(0,0,0,0.38),
        0 0 0 1px rgba(255,255,255,0.04);
      overflow: hidden;
    }

    .command-palette-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 18px 20px 10px;
      color: rgba(255,255,255,0.72);
      font-size: 12px;
      letter-spacing: 0.14em;
    }

    .command-palette-kicker {
      font-weight: 700;
    }

    .command-palette-input {
      width: calc(100% - 24px);
      margin: 0 12px 12px;
      padding: 15px 18px;
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
      color: white;
      outline: none;
      font-size: 15px;
    }

    .command-palette-input:focus {
      border-color: rgba(90,170,255,0.32);
      box-shadow: 0 0 0 4px rgba(90,170,255,0.10);
    }

    .command-palette-list {
      max-height: 52vh;
      overflow: auto;
      padding: 8px 10px 12px;
    }

    .command-item {
      width: 100%;
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 14px 16px;
      background: transparent;
      border: none;
      color: white;
      border-radius: 14px;
      cursor: pointer;
      text-align: left;
      transition: background 140ms ease, transform 140ms ease;
    }

    .command-item:hover,
    .command-item.active {
      background: rgba(255,255,255,0.06);
      transform: translateX(4px);
    }

    .command-group {
      min-width: 110px;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(150,190,255,0.78);
    }

    .command-label {
      font-size: 15px;
      color: rgba(255,255,255,0.92);
    }

    .command-empty {
      padding: 20px;
      color: rgba(255,255,255,0.6);
      text-align: center;
    }

    @keyframes floatBlob {
      0% { transform: translate3d(0,0,0) scale(1); }
      50% { transform: translate3d(2vw,-2vh,0) scale(1.05); }
      100% { transform: translate3d(-2vw,2vh,0) scale(0.98); }
    }
  `;
  document.head.appendChild(style);
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
      <div class="scroll-progress"></div>
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
    glow.style.transform = `translate(${event.clientX - 120}px, ${event.clientY - 120}px)`;
  });

  window.addEventListener("pointerleave", () => {
    glow.style.opacity = "0";
  });

  window.addEventListener("pointerenter", () => {
    glow.style.opacity = "0.9";
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
    card.style.setProperty("--reveal-delay", `${index * 60}ms`);
    observer.observe(card);
  });
}

function ensureCardDecor(card, index) {
  if (!card.querySelector(".widget-hotkey-badge") && index < 9) {
    const badge = document.createElement("div");
    badge.className = "widget-hotkey-badge";
    badge.textContent = `${index + 1}`;
    card.appendChild(badge);
  }
}

function initCardTilt() {
  const cards = findDashboardCards();

  cards.forEach((card, index) => {
    ensureCardDecor(card, index);

    if (card.dataset.tiltBound === "true") return;
    card.dataset.tiltBound = "true";

    card.addEventListener("pointermove", (event) => {
      if (card.classList.contains("widget-fullscreen")) return;

      const rect = card.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      const px = x / rect.width;
      const py = y / rect.height;

      const rotateY = (px - 0.5) * 8;
      const rotateX = (py - 0.5) * -8;

      card.classList.add("is-hovered");
      card.style.setProperty("--mx", `${px * 100}%`);
      card.style.setProperty("--my", `${py * 100}%`);
      card.style.filter = "brightness(1.02)";
      card.style.transform = `
        translateY(-4px)
        rotateX(${rotateX}deg)
        rotateY(${rotateY}deg)
        scale(1.01)
      `;
    });

    card.addEventListener("pointerleave", () => {
      if (!card.classList.contains("widget-fullscreen")) {
        card.style.transform = "";
      }
      card.style.filter = "";
      card.classList.remove("is-hovered");
    });
  });
}

function collapseExpandedCards() {
  document.querySelectorAll(".dashboard-card.widget-fullscreen").forEach((card) => {
    card.classList.remove("widget-fullscreen");
    card.style.transform = "";
    card.style.filter = "";
  });

  document.querySelectorAll(".card-expand-btn").forEach((btn) => {
    btn.setAttribute("aria-label", "Expand widget");
    btn.innerHTML = "⤢";
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

  const btn = card.querySelector(".card-expand-btn");
  if (btn) {
    const expanded = card.classList.contains("widget-fullscreen");
    btn.setAttribute("aria-label", expanded ? "Collapse widget" : "Expand widget");
    btn.innerHTML = expanded ? "✕" : "⤢";
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

  document.getElementById("widget-spotlight-backdrop")?.addEventListener("click", collapseExpandedCards);
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
  paletteState.selectedIndex = Math.min(
    paletteState.selectedIndex,
    Math.max(commands.length - 1, 0)
  );

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

function initScrollProgress() {
  if (document.body.dataset.scrollFxBound === "true") return;
  document.body.dataset.scrollFxBound = "true";

  const progressEl = document.querySelector(".scroll-progress");

  const update = () => {
    const scrollTop = window.scrollY || document.documentElement.scrollTop || 0;
    const maxScroll =
      Math.max(document.body.scrollHeight, document.documentElement.scrollHeight) -
      window.innerHeight;

    const progress = maxScroll > 0 ? scrollTop / maxScroll : 0;
    document.body.style.setProperty("--scroll-progress", String(progress));

    if (progressEl) {
      progressEl.style.transform = `scaleX(${progress})`;
    }
  };

  update();
  window.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
}

function initWidgetHotkeys() {
  if (document.body.dataset.widgetHotkeysBound === "true") return;
  document.body.dataset.widgetHotkeysBound = "true";

  document.addEventListener("keydown", (event) => {
    if (
      paletteState.open ||
      event.metaKey ||
      event.ctrlKey ||
      event.altKey ||
      /input|textarea|select/i.test(document.activeElement?.tagName || "")
    ) {
      return;
    }

    const index = Number(event.key);
    if (!Number.isInteger(index) || index < 1 || index > 9) return;

    const cards = findDashboardCards();
    const card = cards[index - 1];
    if (!card) return;

    event.preventDefault();
    toggleCardExpand(card);
    card.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

export function initDashboardFX() {
  injectFXStyles();
  injectAmbientLayers();
  findDashboardCards();
  initCursorGlow();
  initRevealAnimations();
  initCardTilt();
  initWidgetExpand();
  initCommandPalette();
  initWidgetSearch();
  initScrollProgress();
  initWidgetHotkeys();
}