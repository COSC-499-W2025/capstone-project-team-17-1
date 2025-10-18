const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { initSchema } = require('./db/init');
const { registerArtifactIpc } = require('./ipc/artifacts');
const { validateZipInput } = require("./lib/fileValidator");
const { ConfigStore } = require("./lib/configStore");
const { registerZipIpc } = require("./ipc/zip"); // importing zip parser (Raunak's issue) 

//----------------- Caution: most of following commands are used to banned GPU rendering ----------------- //
// to resolve an unknown bug affecting only Eren's computer, 
// testing has confirmed it does not impact other's devices or team projects, so please do not remove it
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
//----------------- END -----------------//

let cfg; // ConfigStore instance hydrated after app is ready.

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js")
    }
  });
  win.loadFile(path.join(__dirname, "index.html"));
  win.webContents.openDevTools({ mode: "detach" });
}

ipcMain.handle("zip:validate", (_event, filePath) => {
  const validationError = validateZipInput(filePath);
  if (validationError) {
    return validationError;
  }

  return { ok: true };
});

app.whenReady().then(() => {
  console.log("Electron ready");
  cfg = new ConfigStore({
    dir: path.join(app.getPath("userData"), "config"),
    defaults: { theme: "system", allowTelemetry: false },
    validate(obj) {
      const allowed = new Set(["theme", "allowTelemetry"]);
      for (const key of Object.keys(obj)) {
        if (!allowed.has(key)) throw new Error(`Unknown key: ${key}`);
      }
      if (!["system", "light", "dark"].includes(obj.theme)) {
        throw new Error("Invalid theme");
      }
      if (typeof obj.allowTelemetry !== "boolean") {
        throw new Error("allowTelemetry must be boolean");
      }
    }
  });

  ipcMain.handle("config:load", () => cfg.load());
  ipcMain.handle("config:get", (_event, key, fallback) => cfg.get(key, fallback));
  ipcMain.handle("config:set", (_event, key, value) => cfg.set(key, value));
  ipcMain.handle("config:merge", (_event, patch) => cfg.merge(patch));
  ipcMain.handle("config:reset", () => cfg.reset());

  initSchema(); 
  registerArtifactIpc(); 
  registerArtifactIpc();
  registerZipIpc(ipcMain);
  
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
