// src/js/fileUpload.js

const uploadBtn = document.getElementById('btn-upload-file');
const statusEl = document.getElementById('file-upload-status');
const tableBody = document.querySelector('#file-upload-table tbody');

// Hook up a project id if you want to associate uploads with a specific project.
const ACTIVE_PROJECT_ID = null;

function fmtBytes(n) {
  if (typeof n !== 'number' || Number.isNaN(n)) return '';
  if (n < 1024) return `${n} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let size = n;
  let idx = -1;
  do {
    size /= 1024;
    idx += 1;
  } while (size >= 1024 && idx < units.length - 1);
  return `${size.toFixed(1)} ${units[idx]}`;
}

function esc(str) {
  return String(str).replace(/[&<>"']/g, (m) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[m]);
}

function renderRows(rows) {
  if (!rows || rows.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="4" style="padding:8px;color:#666">No files found in archive.</td></tr>`;
    return;
  }

  tableBody.innerHTML = rows.map((row) => `
    <tr>
      <td style="padding:6px 4px;border-bottom:1px solid #f0f0f0">${esc(row.zip_path)}</td>
      <td style="padding:6px 4px;text-align:right;border-bottom:1px solid #f0f0f0">${fmtBytes(row.size_bytes)}</td>
      <td style="padding:6px 4px;border-bottom:1px solid #f0f0f0">${esc(row.last_modified_utc)}</td>
      <td style="padding:6px 4px;border-bottom:1px solid #f0f0f0">${esc(row.mime_type)}</td>
    </tr>
  `).join('');
}

async function handleUpload() {
  if (!window.files?.upload) {
    statusEl.textContent = 'Upload API unavailable';
    return;
  }
  if (!window.zipAPI?.scan) {
    statusEl.textContent = 'ZIP API unavailable';
    return;
  }

  statusEl.textContent = 'Selecting file...';
  try {
    const uploadRes = await window.files.upload({
      validate: 'zip',
      projectId: ACTIVE_PROJECT_ID,
    });

    if (!uploadRes || !uploadRes.ok) {
      statusEl.textContent = uploadRes?.error || 'Upload canceled';
      return;
    }

    const uploaded = uploadRes.data || {};
    const zipPath = uploaded.storedPath || uploaded.path;

    statusEl.textContent = 'Scanning archive...';
    const scanRes = await window.zipAPI.scan(zipPath);
    if (!scanRes || !scanRes.ok) {
      statusEl.textContent = scanRes?.error || 'Scan failed';
      return;
    }

    const files = scanRes.data || [];
    renderRows(files);

    const now = Math.floor(Date.now() / 1000);
    const artifactRows = files.map((file) => ({
      project_id: ACTIVE_PROJECT_ID,
      path: file.zip_path,
      name: file.zip_path.split('/').pop() || file.zip_path,
      ext: (file.zip_path.match(/\.[^.]+$/) || [''])[0],
      size_bytes: file.size_bytes,
      created_at: now,
      modified_at: now,
      tag: 'zip-upload',
      sha256: file.sha256 || null,
      meta_json: JSON.stringify({
        mime_type: file.mime_type,
        last_modified_utc: file.last_modified_utc,
        source: 'zip',
        parentZip: zipPath,
      }),
    }));

    let insertedMsg = '';
    if (artifactRows.length > 0) {
      try {
        const dbRes = await window.db.insertArtifacts(artifactRows);
        insertedMsg = ` · Indexed ${dbRes.inserted} entries`;
      } catch (err) {
        console.warn('DB insert failed:', err);
        insertedMsg = ' · Failed to index entries';
      }
    }

    statusEl.textContent = `Uploaded ${uploaded.name || 'archive'}${insertedMsg}`;
  } catch (err) {
    console.error(err);
    statusEl.textContent = 'Upload failed';
  }
}

uploadBtn?.addEventListener('click', () => {
  uploadBtn.disabled = true;
  handleUpload().finally(() => {
    uploadBtn.disabled = false;
  });
});
