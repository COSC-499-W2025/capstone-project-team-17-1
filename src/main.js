const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { initSchema } = require("./db/init");
const { registerArtifactIpc } = require("./ipc/artifacts");
const { validateZipInput } = require("./lib/fileValidator");
const { ConfigStore } = require("./lib/configStore");
const { registerZipIpc } = require("./ipc/zip");
const { registerFileIpc } = require("./ipc/files");
const { registerProjectIpc } = require('./ipc/projects');
const { getProjectAnalysisById, listProjectSummaries } = require('./db/projectStore');
const { detectTechStack, buildMarkdown } = require("./lib/detectTechStack");
const { buildSkillsSnapshotFromDetails } = require('./services/skillsSnapshot');
const detectSkills = require('./lib/detectSkills');
const scoreSkills = require('./lib/scoreSkills');

ipcMain.handle("tech:detect", async (_event, rootDir) => {
  const root = rootDir || process.cwd();
  const det = await detectTechStack(root);
  const md = buildMarkdown(det);
  return { det, md };
});
ipcMain.handle('skills:get', (_e, args = {}) => {
  try {
    const projectId = args.projectId ?? null;
    let row = projectId ? getProjectAnalysisById(projectId) : (listProjectSummaries()[0] || null);
    if (!row) throw new Error('No project found to analyze.');
    if (!row.details) throw new Error('Project has no analysis details yet.');

    // --- debug: do we actually have per-ext data stored?
    const first = row?.details?.contributorsDetailed?.[0];
    console.log('[skills:get] details?',
      !!row?.details,
      'contributorsDetailed?', Array.isArray(row?.details?.contributorsDetailed),
      'first.linesByExt keys:',
      first && first.metrics && first.metrics.linesByExt ? Object.keys(first.metrics.linesByExt) : []
    );

    const snapshot = buildSkillsSnapshotFromDetails(row);

    // --- debug: did the snapshot build per-author buckets?
    const perAuthorBuckets =
      snapshot.files.filter(f => Object.keys(f.authors || {}).some(a => a && a !== '__project__')).length;
    console.log('[skills:get] snapshot counts',
      { manifests: snapshot.manifests.length, files: snapshot.files.length, contributors: snapshot.contributors.length,
        perAuthorBuckets });

    const raw = detectSkills(snapshot); // presence + confidence

    const scored = scoreSkills({
      contributors: snapshot.contributors,
      contributorSkills: raw.contributorSkills,
      presence: raw.projectSkills      // allow fallback scoring when no per-skill lines
    });

    // ---- fall back to presence if impact is empty ----
    let projectSkills = scored.projectSkills || [];
    if (!projectSkills.length && raw.projectSkills?.length) {
      projectSkills = raw.projectSkills.map(s => ({
        skill: s.skill,
        impact: Math.max(0.4, Math.min(1, s.confidence || 0.6))
      }));
    }

    return {
      projectSkills,                         // used by UI chips
      contributorSkills: scored.contributorSkills,
      presence: raw.projectSkills            // just for inspection if needed
    };
  } catch (err) {
    console.error('[skills:get] failure:', err);
    throw err;
  }
});


// --- GPU workarounds (keep) ---
app.disableHardwareAcceleration();
app.commandLine.appendSwitch("disable-gpu");
app.commandLine.appendSwitch("disable-gpu-compositing");
app.commandLine.appendSwitch("use-angle", "swiftshader");
app.commandLine.appendSwitch("use-gl", "swiftshader");
app.commandLine.appendSwitch("in-process-gpu");
app.commandLine.appendSwitch("no-sandbox");

// Quiet terminal (leave commented unless you want verbose Chromium logs)
// app.commandLine.appendSwitch("enable-logging");
// app.commandLine.appendSwitch("v", "1");
// app.commandLine.appendSwitch("log-file", "gpu.log");

let cfg;

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
      devTools: !app.isPackaged, // allow in dev, block in prod
    },
  });

  win.loadFile(path.join(__dirname, "index.html"));

  // DO NOT auto-open DevTools (prevents Autofill noise)
  // win.webContents.openDevTools({ mode: "detach" });

  // If DevTools is opened manually, drop Autofill spam
  win.webContents.on("console-message", (_e, _level, msg) => {
    if (typeof msg === "string" && msg.includes("Autofill")) return; // swallow
  });
  win.webContents.on("devtools-opened", () => {
    win.webContents.devToolsWebContents?.executeJavaScript("console.clear()");
  });
}

ipcMain.handle("zip:validate", (_event, filePath) => {
  const validationError = validateZipInput(filePath);
  return validationError || { ok: true };
});

app.whenReady().then(() => {
  console.log("Electron ready");

  cfg = new ConfigStore({
    dir: path.join(app.getPath("userData"), "config"),
    defaults: { theme: "system", allowTelemetry: false },
    validate(obj) {
      const allowed = new Set(["theme", "allowTelemetry"]);
      for (const key of Object.keys(obj)) if (!allowed.has(key)) throw new Error(`Unknown key: ${key}`);
      if (!["system", "light", "dark"].includes(obj.theme)) throw new Error("Invalid theme");
      if (typeof obj.allowTelemetry !== "boolean") throw new Error("allowTelemetry must be boolean");
    },
  });

  ipcMain.handle("config:load", () => cfg.load());
  ipcMain.handle("config:get", (_e, key, fallback) => cfg.get(key, fallback));
  ipcMain.handle("config:set", (_e, key, value) => cfg.set(key, value));
  ipcMain.handle("config:merge", (_e, patch) => cfg.merge(patch));
  ipcMain.handle("config:reset", () => cfg.reset());

  initSchema();

  // Defensive cleanup + single registration for artifacts IPC
  ipcMain.removeHandler("artifact.query");
  ipcMain.removeHandler("artifact.insertMany");
  registerArtifactIpc();

  // Register ZIP IPC once
  registerZipIpc(ipcMain);
  registerFileIpc();
  registerProjectIpc();

  console.log("[ipc] registered channels:", ipcMain.eventNames().map(String));

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});


app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
