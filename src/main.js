const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { initSchema } = require('./db/init'); 
const { registerArtifactIpc } = require('./ipc/artifacts');
const { validateZipInput } = require("./lib/fileValidator");

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
  initSchema(); 
  registerArtifactIpc(); 
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
