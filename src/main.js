const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { initSchema } = require("./db/init");
const { registerArtifactIpc } = require("./ipc/artifacts");
const { registerProjectIpc } = require("./ipc/projects");
const { validateZipInput } = require("./lib/fileValidator");
const { ConfigStore } = require("./lib/configStore");


const { registerZipIpc } = require("./ipc/zip");
const { refreshAllProjectAnalysis } = require("./services/projectAnalyzer");

// --- GPU workarounds (leave as-is) ---
app.disableHardwareAcceleration();
app.commandLine.appendSwitch('disable-gpu');
app.commandLine.appendSwitch('disable-gpu-compositing');
app.commandLine.appendSwitch('use-angle', 'swiftshader');
app.commandLine.appendSwitch('use-gl', 'swiftshader');
app.commandLine.appendSwitch('in-process-gpu');
app.commandLine.appendSwitch('no-sandbox');
app.commandLine.appendSwitch('enable-logging');
app.commandLine.appendSwitch('v', '1');
app.commandLine.appendSwitch('log-file', 'gpu.log');

let cfg;

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  win.loadFile(path.join(__dirname, "index.html"));

  // Open DevTools only when not packaged (prevents Autofill noise)
  if (!app.isPackaged) {
    win.webContents.openDevTools({ mode: "detach" });
  }
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
    }
  });

  ipcMain.handle("config:load", () => cfg.load());
  ipcMain.handle("config:get", (_e, key, fallback) => cfg.get(key, fallback));
  ipcMain.handle("config:set", (_e, key, value) => cfg.set(key, value));
  ipcMain.handle("config:merge", (_e, patch) => cfg.merge(patch));
  ipcMain.handle("config:reset", () => cfg.reset());

  // init DB schema once
initSchema();

// ensure single registration for artifact IPC
ipcMain.removeHandler('artifact.query');
ipcMain.removeHandler('artifact.insertMany');
registerArtifactIpc();

// (from develop) project IPCs
if (typeof registerProjectIpc === 'function') {
  registerProjectIpc(ipcMain);
}

// (from your branch) ZIP IPC
registerZipIpc(ipcMain);

console.log('[ipc] registered channels:', ipcMain.eventNames().map(String));

// (from develop) kick off initial project analysis
if (typeof refreshAllProjectAnalysis === 'function') {
  refreshAllProjectAnalysis({ logger: console }).catch((err) => {
    console.error('[main] initial project analysis failed:', err);
  });
}

// window wiring
createWindow();
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

