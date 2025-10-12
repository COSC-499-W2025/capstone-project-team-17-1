const { app, BrowserWindow } = require("electron");

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700
  });
  win.loadFile("index.html");
  win.webContents.openDevTools({ mode: "detach" }); // helps if something fails
}

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
