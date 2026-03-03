const { app, BrowserWindow, ipcMain } = require("electron")
const path = require("path")
const { spawn } = require("child_process");

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
  })

  win.loadFile("src/index.html")
}

ipcMain.on("close", (event) => {
  event.sender.getOwnerBrowserWindow().close()
  if (apiProcess) {
    console.log("Shutting down API...");

    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", apiProcess.pid, "/f", "/t"]);
    } else {
      apiProcess.kill("SIGTERM");
    }

    apiProcess = null;
  }
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
function startAPI() {
   if (apiProcess) {
    console.log("API already running.");
    return;
   }
  const pythonPath = path.join(
    __dirname,
    "..",
    "..",
    ".venv",
    "Scripts",
    "python.exe"
  );

  console.log("Using Python:", pythonPath);

  apiProcess = spawn(pythonPath, [
    "-m",
    "uvicorn",
    "capstone.api.server:app",
    "--reload",
    "--port",
    "8002"
  ], {
    cwd: path.join(__dirname, "..", ".."),
    windowsHide: true
  });

  apiProcess.stdout.on("data", (data) => {
    console.log(`API: ${data}`);
  });

  apiProcess.stderr.on("data", (data) => {
    console.error(`API Error: ${data}`);
  });

  apiProcess.on("close", (code) => {
    console.log(`API exited with code ${code}`);
  });
}

app.whenReady().then(() => {
  startAPI();
  createWindow();
});

app.on("before-quit", () => {
  if (apiProcess) {
    console.log("Shutting down API...");

    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", apiProcess.pid, "/f", "/t"]);
    } else {
      apiProcess.kill("SIGTERM");
    }

    apiProcess = null;
  }
});

app.on("window-all-closed", () => {
if (apiProcess) {
    console.log("Shutting down API...");

    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", apiProcess.pid, "/f", "/t"]);
    } else {
      apiProcess.kill("SIGTERM");
    }

    apiProcess = null;
  }
});