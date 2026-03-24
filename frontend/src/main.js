const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const os = require("os");
const fs = require("fs");
const net = require("net");
const http = require("http");

require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

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
    const existingBackend = await probeExistingBackend(API_HOST, API_PORT);
    if (existingBackend.ok) {
      console.log(`Backend already available at http://${API_HOST}:${API_PORT}; reusing verified Capstone API.`);
      return;
    }

    const message =
      `Port ${API_PORT} is already in use by a different service.\n\n` +
      `The app will not reuse it because that can break features like starring/saving projects.\n\n` +
      `Details: ${existingBackend.reason}`;
    console.error(message);
    dialog.showErrorBox("Backend Port Conflict", message);
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

function httpGetJson(host, port, pathName) {
  return new Promise((resolve, reject) => {
    const req = http.get(
      {
        host,
        port,
        path: pathName,
        timeout: 1500,
      },
      (res) => {
        let body = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => {
          body += chunk;
        });
        res.on("end", () => {
          try {
            resolve({
              statusCode: res.statusCode || 0,
              json: body ? JSON.parse(body) : null,
            });
          } catch (error) {
            reject(error);
          }
        });
      }
    );

    req.on("timeout", () => {
      req.destroy(new Error("request timed out"));
    });
    req.on("error", reject);
  });
}

async function probeExistingBackend(host, port) {
  try {
    const [root, debug] = await Promise.all([
      httpGetJson(host, port, "/"),
      httpGetJson(host, port, "/__debug/routers"),
    ]);

    const rootOk = root.statusCode === 200 && root.json?.message === "Capstone API is running";
    const debugOk =
      debug.statusCode === 200 &&
      Array.isArray(debug.json?.routes) &&
      debug.json.routes.includes("/projects") &&
      debug.json.routes.includes("/auth/me");

    if (rootOk && debugOk) {
      return { ok: true, reason: "verified Capstone API" };
    }

    return {
      ok: false,
      reason: `unexpected responses from existing service on ${host}:${port}`,
    };
  } catch (error) {
    return {
      ok: false,
      reason: error instanceof Error ? error.message : String(error),
    };
  }
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

ipcMain.handle("ai:chat", async (_event, messages) => {
  const lastMessage = messages?.[messages.length - 1]?.content?.trim() || "";
  const lower = lastMessage.toLowerCase();

  if (!lastMessage) {
    return { reply: "Please type a message." };
  }

  if (lower.includes("resume")) {
    return {
      reply:
        "For your resume, focus on impact. Start bullets with action verbs, include numbers, and keep each bullet outcome-focused."
    };
  }

  if (lower.includes("portfolio")) {
    return {
      reply:
        "Your portfolio should highlight your best 2–3 projects, your exact role, the tech stack, and what problem you solved."
    };
  }

  if (lower.includes("project")) {
    return {
      reply:
        "A strong project summary includes: problem, approach, stack, challenges, and measurable result."
    };
  }

  if (lower.includes("job")) {
    return {
      reply:
        "For job matching, compare role requirements against your projects, skills, and keywords from the posting."
    };
  }

  if (lower.includes("hello") || lower.includes("hey") || lower.includes("hi")) {
    return {
      reply:
        "Hey — I’m Loom Copilot. Ask me about your resume, portfolio, projects, or jobs."
    };
  }

  return {
    reply:
      "I’m running in demo mode right now. The chatbot flow works, and a real AI model can be plugged in later."
  };
});
app.whenReady().then(() => {
  startAPI();
  createWindow();
});

app.on("before-quit", stopAPI);
app.on("window-all-closed", stopAPI);
