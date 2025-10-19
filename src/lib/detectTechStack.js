#!/usr/bin/env node
const fs = require("fs");
const fsp = require("fs/promises");
const path = require("path");

const PKG_FRAMEWORK_HINTS = {
  // web/js
  react: "React",
  "react-dom": "React",
  next: "Next.js",
  vue: "Vue",
  "@angular/core": "Angular",
  svelte: "Svelte",
  vite: "Vite",
  express: "Express",
  koa: "Koa",
  fastify: "Fastify",
  electron: "Electron",
  "semantic-release": "semantic-release",
  "eslint": "ESLint",
  "prettier": "Prettier",
  jest: "Jest",
  "ts-node": "TypeScript",
  typescript: "TypeScript",
  nestjs: "NestJS",
};

const PIP_FRAMEWORK_HINTS = {
  django: "Django",
  flask: "Flask",
  fastapi: "FastAPI",
  numpy: "NumPy",
  pandas: "pandas",
};

function exists(p) {
  try {
    return fs.existsSync(p);
  } catch {
    return false;
  }
}

async function readJsonSafe(file) {
  try {
    const txt = await fsp.readFile(file, "utf8");
    return JSON.parse(txt);
  } catch {
    return null;
  }
}

async function readTextSafe(file) {
  try {
    return await fsp.readFile(file, "utf8");
  } catch {
    return null;
  }
}

function uniq(arr) {
  return [...new Set(arr.filter(Boolean))];
}

/**
 * Detect stack signals from repo root
 * @param {string} root
 * @returns {Promise<{languages: string[], frameworks: Array<{name:string, version?:string}>, tools: string[], packageManagers: string[], runTips: string[]}>}
 */
async function detectTechStack(root = process.cwd()) {
  const languages = [];
  const frameworks = [];
  const tools = [];
  const packageManagers = [];
  const runTips = [];

  // --- Node / JS / TS ---
  const pkgPath = path.join(root, "package.json");
  if (exists(pkgPath)) {
    const pkg = await readJsonSafe(pkgPath);
    languages.push("JavaScript");
    if (pkg?.type === "module") tools.push("ESM");
    if (pkg?.devDependencies?.typescript || pkg?.dependencies?.typescript) {
      languages.push("TypeScript");
    }
    const allDeps = { ...(pkg?.dependencies || {}), ...(pkg?.devDependencies || {}) };
    for (const [dep, ver] of Object.entries(allDeps)) {
      if (PKG_FRAMEWORK_HINTS[dep]) {
        frameworks.push({ name: PKG_FRAMEWORK_HINTS[dep], version: ver?.toString() });
      }
    }
    if (exists(path.join(root, "pnpm-lock.yaml"))) packageManagers.push("pnpm");
    if (exists(path.join(root, "yarn.lock"))) packageManagers.push("yarn");
    if (exists(path.join(root, "package-lock.json"))) packageManagers.push("npm");
    if (pkg?.scripts?.start) runTips.push("npm run start");
    if (pkg?.scripts?.dev) runTips.push("npm run dev");
    tools.push("Node.js");
  }

  // --- Python ---
  const reqTxt = path.join(root, "requirements.txt");
  const pyProj = path.join(root, "pyproject.toml");
  if (exists(reqTxt) || exists(pyProj)) {
    languages.push("Python");
    tools.push(exists(pyProj) ? "poetry/pyproject" : "pip");
    const reqContent = (exists(reqTxt) && fs.readFileSync(reqTxt, "utf8")) || "";
    for (const line of reqContent.split(/\r?\n/)) {
      const m = line.trim().match(/^([A-Za-z0-9_\-]+)\s*([=><!~]=\s*[^#\s]+)?/);
      if (!m) continue;
      const lib = m[1].toLowerCase();
      const ver = (m[2] || "").replace(/^[^0-9]*/, "").trim() || undefined;
      if (PIP_FRAMEWORK_HINTS[lib]) {
        frameworks.push({ name: PIP_FRAMEWORK_HINTS[lib], version: ver });
      }
    }
  }

  // --- .NET / C# ---
  const csproj = findFirstFileByGlob(root, /\.csproj$/);
  if (csproj) {
    languages.push("C#");
    tools.push(".NET");
    const xml = await readTextSafe(csproj);
    const tfm = xml?.match(/<TargetFramework>([^<]+)<\/TargetFramework>/i)?.[1];
    frameworks.push({ name: ".NET", version: tfm });
  }

  // --- Java / Kotlin (Gradle or Maven) ---
  if (exists(path.join(root, "pom.xml"))) {
    languages.push("Java");
    tools.push("Maven");
  }
  if (exists(path.join(root, "build.gradle")) || exists(path.join(root, "build.gradle.kts"))) {
    languages.push("Java/Kotlin");
    tools.push("Gradle");
    const gradleKts = await readTextSafe(path.join(root, "build.gradle.kts"));
    if (gradleKts && /spring-boot/i.test(gradleKts)) frameworks.push({ name: "Spring Boot" });
  }

  // --- Rust ---
  if (exists(path.join(root, "Cargo.toml"))) {
    languages.push("Rust");
    tools.push("Cargo");
  }

  // --- Go ---
  if (exists(path.join(root, "go.mod"))) {
    languages.push("Go");
    tools.push("Go modules");
  }

  

  // --- Ruby ---
  if (exists(path.join(root, "Gemfile"))) {
    languages.push("Ruby");
    const gemfile = await readTextSafe(path.join(root, "Gemfile"));
    if (/gem\s+['"]rails['"]/.test(gemfile)) frameworks.push({ name: "Ruby on Rails" });
    tools.push("Bundler");
  }

  // --- Unity ---
  const unityVersion = await readTextSafe(path.join(root, "ProjectSettings", "ProjectVersion.txt"));
  if (unityVersion || exists(path.join(root, "Assets"))) {
    languages.push("C#");
    frameworks.push({ name: "Unity", version: unityVersion?.match(/m_EditorVersion:\s*([^\s]+)/)?.[1] });
    tools.push("Unity Editor");
  }

  // --- Package managers from lock files (generic) ---
  if (!packageManagers.length) {
    if (exists(path.join(root, "bun.lockb"))) packageManagers.push("bun");
  }

  const result = {
    languages: uniq(languages),
    frameworks: dedupeFrameworks(frameworks),
    tools: uniq(tools),
    packageManagers: uniq(packageManagers),
    runTips: uniq(runTips),
  };
  return result;
}

function dedupeFrameworks(frws) {
  const map = new Map();
  for (const f of frws) {
    const key = f.name.toLowerCase();
    if (!map.has(key)) map.set(key, f);
    else if (f.version && !map.get(key).version) map.set(key, f);
  }
  return [...map.values()];
}

function findFirstFileByGlob(root, regex) {
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (entry.isFile() && regex.test(entry.name)) return path.join(root, entry.name);
  }
  return null;
}

/** Turn detection result into markdown string */
function buildMarkdown(det) {
  const fwList = det.frameworks.length
    ? det.frameworks.map(f => `- ${f.name}${f.version ? ` (${f.version})` : ""}`).join("\n")
    : "- None detected";
  const md = `# Tech Stack

## Languages
${det.languages.length ? det.languages.map(l => `- ${l}`).join("\n") : "- Unknown"}

## Frameworks & Libraries
${fwList}

## Tools
${det.tools.length ? det.tools.map(t => `- ${t}`).join("\n") : "- None"}

## Package Managers
${det.packageManagers.length ? det.packageManagers.map(p => `- ${p}`).join("\n") : "- Not detected"}

## How to Run (quick tips)
${det.runTips.length ? det.runTips.map(t => `- ${t}`).join("\n") : "- See project README for run instructions"}
`;
  return md;
}

async function main() {
  const dry = process.argv.includes("--dry");
  const det = await detectTechStack(process.cwd());
  const md = buildMarkdown(det);
  if (dry) {
    process.stdout.write(md);
  } else {
    await fsp.writeFile(path.join(process.cwd(), "TECH_STACK.md"), md, "utf8");
    console.log("TECH_STACK.md written.");
  }
}

if (require.main === module) {
  main().catch((e) => {
    console.error("Detection failed:", e);
    process.exit(1);
  });
}

module.exports = { detectTechStack, buildMarkdown };
