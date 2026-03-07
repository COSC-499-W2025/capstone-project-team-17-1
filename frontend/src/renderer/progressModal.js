let progressTimer = null;

export function openProgressModal(initialText) {
  const existing = document.getElementById("progress-modal");
  if (existing) return;

  const modal = document.createElement("div");
  modal.id = "progress-modal";
  modal.innerHTML = `
    <div class="upload-overlay">
      <div class="progress-window">
        <div class="progress-title">Importing Project</div>
        <div id="progress-text" class="progress-text">${initialText || "Working..."}</div>

        <div class="progress-bar">
          <div id="progress-fill" class="progress-fill" style="width: 0%"></div>
        </div>

        <div id="progress-percent" class="progress-percent">0%</div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  let p = 0;
  progressTimer = setInterval(() => {
    p = Math.min(90, p + 3);
    setProgress(p, document.getElementById("progress-text")?.textContent || "Working...");
  }, 250);
}

export function setProgress(percent, text) {
  const fill = document.getElementById("progress-fill");
  const label = document.getElementById("progress-percent");
  const t = document.getElementById("progress-text");

  if (fill) fill.style.width = `${percent}%`;
  if (label) label.textContent = `${percent}%`;
  if (t && text) t.textContent = text;
}

export function closeProgressModal() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  document.getElementById("progress-modal")?.remove();
}