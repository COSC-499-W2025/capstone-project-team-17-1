import { cpuChart, memoryChart, gpuChart } from "./chart.js"

let cpuHistory = []
let memoryHistory = []
let gpuHistory = []

function updateArc(element, value) {
  const circumference = 126;
  const offset = circumference - (value / 100) * circumference;

  element.style.strokeDashoffset = offset;

  // 🔥 dynamic color
  element.style.stroke = getUsageColor(value);
}

function getUsageColor(value) {
  const clamp = Math.max(0, Math.min(100, value));

  let r, g;

  if (clamp <= 50) {
    // Green → Yellow
    const ratio = clamp / 50;
    r = Math.floor(0 + ratio * 255);
    g = 255;
  } else {
    // Yellow → Red
    const ratio = (clamp - 50) / 50;
    r = 255;
    g = Math.floor(255 - ratio * 255);
  }

  return `rgb(${r}, ${g}, 0)`;
}

function updateMiniChart(chart, data) {
  chart.data.labels = data.map((_, i) => i)
  chart.data.datasets[0].data = data
  chart.update()
}

async function fetchMetrics() {
  const metricsRes = await fetch("http://127.0.0.1:8002/system/system-metrics");
  const metrics = await metricsRes.json();

  const healthRes = await fetch("http://127.0.0.1:8002/health");
  const health = await healthRes.json();

  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("system-status");

  if (health.status === "ok") {
    statusDot.className = "status-dot active";
    statusText.innerText = "System Running";
  } else {
    statusDot.className = "status-dot inactive";
    statusText.innerText = "System Offline";
  }

  updateArc(document.getElementById("cpu-arc"), metrics.cpu.usage);
  updateArc(document.getElementById("memory-arc"), metrics.memory.usage);

  if (metrics.gpu.detected) {
  const gpuUsage = metrics.gpu.usage || 0;

  updateArc(document.getElementById("gpu-arc"), gpuUsage);

  document.getElementById("gpu-label").innerText = "GPU";

  // 🔥 ADD THIS
  document.getElementById("gpu-value").innerText =
    Math.round(gpuUsage) + "%";

  document.getElementById("gpu-temp").innerText =
    metrics.gpu.temperature ? metrics.gpu.temperature + "°C" : "--°C";

} else {
  const storageUsage = metrics.storage.usage || 0;

  updateArc(document.getElementById("gpu-arc"), storageUsage);

  document.getElementById("gpu-label").innerText = "Storage";

  // 🔥 ALSO ADD THIS
  document.getElementById("gpu-value").innerText =
    Math.round(storageUsage) + "%";

  document.getElementById("gpu-temp").innerText = "";
}

  document.getElementById("cpu-value").innerText =
    Math.round(metrics.cpu.usage) + "%";

  document.getElementById("cpu-temp").innerText =
    metrics.cpu.temperature ? metrics.cpu.temperature + "°C" : "--°C";

  document.getElementById("memory-value").innerText =
    Math.round(metrics.memory.usage) + "%";

  cpuHistory.push(metrics.cpu.usage || 0);
memoryHistory.push(metrics.memory.usage || 0);
gpuHistory.push(
  metrics.gpu && metrics.gpu.detected
    ? metrics.gpu.usage || 0
    : metrics.storage.usage || 0
);

if (cpuHistory.length > 40) {
  cpuHistory.shift();
  memoryHistory.shift();
  gpuHistory.shift();
}

function updateMiniChart(chart, data) {
  chart.data.labels = data.map((_, i) => i);
  chart.data.datasets[0].data = data;
  chart.update();
}

updateMiniChart(cpuChart, cpuHistory);
updateMiniChart(memoryChart, memoryHistory);
updateMiniChart(gpuChart, gpuHistory);
}


export function startMetrics() {
  fetchMetrics()
  setInterval(fetchMetrics, 1000)
}