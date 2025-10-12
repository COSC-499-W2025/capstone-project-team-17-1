const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { validateZipInput } = require("./lib/fileValidator");

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
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
