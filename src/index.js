// index.js
const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { validateZipInput } = require("./lib/fileValidator");
const { ConfigStore } = require("./lib/configStore"); // <-- add

let cfg; // ConfigStore instance

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  if (!app.isPackaged) win.webContents.openDevTools({ mode: "detach" });
  win.loadFile(path.join(__dirname, "index.html"));
}

// existing zip validator IPC
ipcMain.handle("zip:validate", (_event, filePath) => {
  const validationError = validateZipInput(filePath);
  return validationError ? validationError : { ok: true };
});

app.whenReady().then(() => {
  // init ConfigStore in a writable location
  cfg = new ConfigStore({
    dir: path.join(app.getPath("userData"), "config"),
    defaults: { theme: "system", allowTelemetry: false },
    validate(obj) {
      const allowed = new Set(["theme", "allowTelemetry"]);
      for (const k of Object.keys(obj)) if (!allowed.has(k)) throw new Error(`Unknown key: ${k}`);
      if (!["system", "light", "dark"].includes(obj.theme)) throw new Error("Invalid theme");
      if (typeof obj.allowTelemetry !== "boolean") throw new Error("allowTelemetry must be boolean");
    }
  });

  // IPC for config
  ipcMain.handle("config:load", () => cfg.load());
  ipcMain.handle("config:get", (_e, key, fallback) => cfg.get(key, fallback));
  ipcMain.handle("config:set", (_e, key, value) => cfg.set(key, value));
  ipcMain.handle("config:merge", (_e, patch) => cfg.merge(patch));
  ipcMain.handle("config:reset", () => cfg.reset());

  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
