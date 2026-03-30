export function createMiniChart(ctx, color) {
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: color,
        borderWidth: 2,
        tension: 0.4,
        fill: false,
        pointRadius: 0
      }]
    },
    options: {
      animation: false,
      parsing: false,
      normalized: true,
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: { display: false, min: 0, max: 100 }
      }
    }
  });
}

export const cpuChart = createMiniChart(
  document.getElementById("cpu-chart").getContext("2d"),
  "#4da6ff"
);

export const memoryChart = createMiniChart(
  document.getElementById("memory-chart").getContext("2d"),
  "#00ff88"
);

export const gpuChart = createMiniChart(
  document.getElementById("gpu-chart").getContext("2d"),
  "#ffcc00"
);
