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

function formatTimestamp(value) {
  if (value === null || value === undefined || value === '') return 'N/A';

  let date;
  if (value instanceof Date) {
    date = value;
  } else if (typeof value === 'number' && Number.isFinite(value)) {
    const ms = value > 1e12 ? value : value * 1000;
    date = new Date(ms);
  } else if (typeof value === 'string') {
    const candidate = new Date(value);
    if (Number.isNaN(candidate.getTime())) return value;
    date = candidate;
  } else {
    return String(value);
  }

  if (Number.isNaN(date.getTime())) return 'N/A';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
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
    tableBody.innerHTML = `<tr><td colspan="4" style="padding:8px 12px;color:#666">No files found in archive.</td></tr>`;
    return;
  }

  tableBody.innerHTML = rows.map((row) => {
    const path = row.zip_path || row.path || '';
    const size = fmtBytes(row.size_bytes);
    const modified = formatTimestamp(row.last_modified_utc || row.modifiedAt || row.modified_at);
    const format = row.format || '';
    return `
      <tr>
        <td style="padding:8px 12px;border-bottom:1px solid #e6e8ef;word-break:break-all;">${esc(path)}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #e6e8ef;white-space:nowrap;">${esc(size)}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #e6e8ef;white-space:nowrap;">${esc(modified)}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #e6e8ef;">${esc(format)}</td>
      </tr>
    `;
  }).join('');
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
        format: file.format || null,
        created_utc: file.created_utc,
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
