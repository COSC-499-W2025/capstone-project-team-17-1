const { app, BrowserWindow, ipcMain } = require("electron")
const path = require("path")

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,  
    minHeight: 900,   
    frame: false,
    titleBarStyle: "hidden",
    roundedCorners: true,
    backgroundColor: "#0b1120",
    icon: path.join(__dirname, "assets/icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })

  win.loadFile("src/index.html")
}

ipcMain.on("close", (event) => {
  event.sender.getOwnerBrowserWindow().close()
})

ipcMain.on("minimize", (event) => {
  event.sender.getOwnerBrowserWindow().minimize()
})

ipcMain.on("maximize", (event) => {
  const win = event.sender.getOwnerBrowserWindow()
  if (win.isMaximized()) {
    win.unmaximize()
  } else {
    win.maximize()
  }
})

app.whenReady().then(createWindow)