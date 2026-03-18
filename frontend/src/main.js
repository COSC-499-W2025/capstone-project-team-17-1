const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const os = require("os");
const fs = require("fs");
const net = require("net");

let apiProcess = null;
let apiProcessMode = "binary";
const API_HOST = "127.0.0.1";
const API_PORT = 8002;

function isPortInUse(host, port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();

    const finish = (inUse) => {
      socket.destroy();
      resolve(inUse);
    };

    socket.setTimeout(500);
    socket.once("connect", () => finish(true));
    socket.once("timeout", () => finish(false));
    socket.once("error", () => finish(false));
    socket.connect(port, host);
  });
}

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

async function startAPI() {
  if (apiProcess) {
    console.log("API already running.");
    return;
  }

  if (await isPortInUse(API_HOST, API_PORT)) {
    console.log(`Backend already available at http://${API_HOST}:${API_PORT}; reusing it.`);
    return;
  }

  if (app.isPackaged) {
    const backendName =
      process.platform === "win32"
        ? "capstone_backend.exe"
        : "capstone_backend";
    const backendPath = path.join(
      process.resourcesPath,
      "backend",
      backendName
    );
    console.log("Backend path:", backendPath);
    console.log("Exists:", fs.existsSync(backendPath));
    if (!fs.existsSync(backendPath)) {
      console.error("Backend executable not found.");
      return;
    }
    apiProcessMode = "binary";
    apiProcess = spawn(backendPath, [], {
      windowsHide: false,
      stdio: "pipe"
    });
  } else {
    const repoRoot = path.join(__dirname, "..", "..");
    const venvPython =
      process.platform === "win32"
        ? path.join(repoRoot, ".venv", "Scripts", "python.exe")
        : path.join(repoRoot, ".venv", "bin", "python");
    const pythonCmd = fs.existsSync(venvPython)
      ? venvPython
      : process.platform === "win32"
        ? "python"
        : "python3";
    const env = {
      ...process.env,
      PYTHONPATH: [path.join(repoRoot, "src"), process.env.PYTHONPATH || ""]
        .filter(Boolean)
        .join(path.delimiter)
    };
    apiProcessMode = "python";
    apiProcess = spawn(pythonCmd, ["-m", "capstone.run_server"], {
      cwd: repoRoot,
      windowsHide: false,
      stdio: "pipe",
      env
    });
  }

  apiProcess.stdout.on("data", data => {
    console.log("API:", data.toString());
  });

  apiProcess.stderr.on("data", data => {
    console.error("API ERROR:", data.toString());
  });

  apiProcess.on("error", err => {
    console.error(`Failed to start backend (${apiProcessMode}):`, err);
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
