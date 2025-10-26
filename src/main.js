const { app, BrowserWindow, ipcMain, screen, nativeImage } = require("electron");
const path = require("path");
const { initSchema } = require("./db/init");
const { registerArtifactIpc } = require("./ipc/artifacts");
const { validateZipInput } = require("./lib/fileValidator");
const { ConfigStore } = require("./lib/configStore");
const { registerZipIpc } = require("./ipc/zip");
const { registerFileIpc } = require("./ipc/files");
const { registerProjectIpc } = require('./ipc/projects');
const { detectTechStack, buildMarkdown } = require("./lib/detectTechStack");

ipcMain.handle("tech:detect", async (_event, rootDir) => {
  const root = rootDir || process.cwd();
  const det = await detectTechStack(root);
  const md = buildMarkdown(det);
  return { det, md };
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
function iconPathForPlatform() {
  // icons created in /build by your scripts
  const base = path.join(__dirname, "..", "build");
  if (process.platform === "win32")  return path.join(base, "app.ico");
  if (process.platform === "darwin") return path.join(base, "app.icns");
  return path.join(base, "icon.png");
}

function createWindow() {
  const display = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
  const { width, height, x, y } = display.workArea; // excludes taskbar/dock
  const iconPath = iconPathForPlatform();
  const img = nativeImage.createFromPath(iconPath);
  const { workArea } = screen.getPrimaryDisplay();
  console.log("[icon]", iconPath, "loaded?", !img.isEmpty()); // should print true
  // macOS dock icon in dev
  if (process.platform === "darwin") {
    const img = nativeImage.createFromPath(iconPath);
    if (!img.isEmpty()) app.dock.setIcon(img);
  }

  // Windows taskbar identity (helps show your icon & notifications properly)
  if (process.platform === "win32") {
    app.setAppUserModelId("com.yourteam.loom");
  }

  const win = new BrowserWindow({
    x: workArea.x, y: workArea.y, width: workArea.width, height: workArea.height,
    show: false,
    show: false,                 // create hidden
    title: "Loom",
    icon: iconPath,
    fullscreen: false,           // we want windowed, not OS fullscreen
    fullscreenable: true,
    backgroundColor: '#0b1220',   // matches your page
    autoHideMenuBar: true,       // optional: hide menu bar
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
      devTools: !app.isPackaged,
    },
  });

  win.loadFile(path.join(__dirname, "welcome.html"));

  // maximize to fill the work area when ready
  win.once("ready-to-show", () => {
    try { win.maximize(); } catch {}
    win.show();
  });
  win.once("ready-to-show", () => win.setTitle("Loom"));

  // keep it windowed even if something tries to toggle fullscreen
  win.on("enter-full-screen", () => win.setFullScreen(false));
  ipcMain.on("start-app", () => {
    win.loadFile(path.join(__dirname, "index.html"));
  });
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
