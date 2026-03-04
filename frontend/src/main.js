const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const os = require("os");
const fs = require("fs");

let apiProcess = null;

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
  });

  win.loadFile("src/index.html");
}

function startAPI() {
  if (apiProcess) {
    console.log("API already running.");
    return;
  }

  const backendName =
    process.platform === "win32"
      ? "capstone_backend.exe"
      : "capstone_backend";

  let backendPath;

  if (app.isPackaged) {
    backendPath = path.join(
      process.resourcesPath,
      "backend",
      backendName
    );
  } else {
    backendPath = path.join(
      __dirname,
      "..",
      "..",
      "src",
      "capstone",
      "dist",
      backendName
    );
  }

  console.log("Backend path:", backendPath);
  console.log("Exists:", fs.existsSync(backendPath));

  if (!fs.existsSync(backendPath)) {
    console.error("Backend executable not found.");
    return;
  }

  apiProcess = spawn(backendPath, [], {
    windowsHide: false,
    stdio: "pipe"
  });

  apiProcess.stdout.on("data", data => {
    console.log("API:", data.toString());
  });

  apiProcess.stderr.on("data", data => {
    console.error("API ERROR:", data.toString());
  });

  apiProcess.on("error", err => {
    console.error("Failed to start backend:", err);
  });
}

function stopAPI() {
  if (!apiProcess) return;

  console.log("Shutting down API...");

  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", apiProcess.pid, "/f", "/t"]);
  } else {
    apiProcess.kill("SIGTERM");
  }

  apiProcess = null;
}

ipcMain.on("close", (event) => {
  event.sender.getOwnerBrowserWindow().close();
  stopAPI();
});

ipcMain.on("minimize", (event) => {
  event.sender.getOwnerBrowserWindow().minimize();
});

ipcMain.on("maximize", (event) => {
  const win = event.sender.getOwnerBrowserWindow();
  if (win.isMaximized()) {
    win.unmaximize();
  } else {
    win.maximize();
  }
});

app.whenReady().then(() => {
  startAPI();
  createWindow();
});

app.on("before-quit", stopAPI);
app.on("window-all-closed", stopAPI);