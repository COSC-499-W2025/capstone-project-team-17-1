// src/js/zipImport.js

const $pick   = document.getElementById('zip-picker');
const $btn    = document.getElementById('btn-import-zip');
const $tableB = document.querySelector('#zip-table tbody');
const $status = document.getElementById('zip-status');

// If you track a current project, wire it up here
const ACTIVE_PROJECT_ID = null;

// Disable Scan until a file is chosen
$btn.disabled = true;

// Enable button when a .zip is chosen
$pick.addEventListener('change', () => {
  const f = $pick.files && $pick.files[0];
  $btn.disabled = !f;
  $status.textContent = f ? 'Ready to scan' : 'Pick a .zip first';
});

// ---------- helpers ----------
function fmtBytes(n) {
  if (typeof n !== 'number' || Number.isNaN(n)) return '';
  if (n < 1024) return `${n} B`;
  const units = ['KB','MB','GB','TB'];
  let i = -1;
  do { n /= 1024; i++; } while (n >= 1024 && i < units.length - 1);
  return `${n.toFixed(1)} ${units[i]}`;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, m => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[m]);
}

function renderRows(rows) {
  if (!rows || rows.length === 0) {
    $tableB.innerHTML = `<tr><td colspan="4" style="padding:8px;color:#666">No files found in archive.</td></tr>`;
    return;
  }
  $tableB.innerHTML = rows.map(r => `
    <tr>
      <td style="padding:6px 4px;border-bottom:1px solid #f0f0f0">${esc(r.zip_path)}</td>
      <td style="padding:6px 4px;text-align:right;border-bottom:1px solid #f0f0f0">${fmtBytes(r.size_bytes)}</td>
      <td style="padding:6px 4px;border-bottom:1px solid #f0f0f0">${esc(r.last_modified_utc)}</td>
      <td style="padding:6px 4px;border-bottom:1px solid #f0f0f0">${esc(r.mime_type)}</td>
    </tr>
  `).join('');
}

// ---------- main click handler ----------
$btn.addEventListener('click', async () => {
  $status.textContent = '';

  // still keep the safety net
  const f = $pick.files && $pick.files[0];
  if (!f) { $status.textContent = 'Pick a .zip first'; return; }

  // Try to get an absolute path (Electron sometimes gives f.path; Chromium may not)
  let zipPath = f.path || null;

  try {
    $btn.disabled = true;

    if (!zipPath) {
      // Fallback to native picker (this returns an absolute path)
      const picked = await window.zipAPI.pick?.();
      if (!picked || !picked.ok) { $status.textContent = 'Pick canceled'; return; }
      zipPath = picked.path;
    }

    // 1) validate
    $status.textContent = 'Validating…';
    const v = await window.archiveValidator.validatePath(zipPath);
    if (!v || !v.ok) { $status.textContent = v?.error || 'InvalidInput'; return; }

    // 2) scan
    $status.textContent = 'Scanning…';
    const res = await window.zipAPI.scan(zipPath);
    if (!res || !res.ok) { $status.textContent = res?.error || 'Scan failed'; return; }

    const files = res.data || [];
    renderRows(files);

    // 3) upsert into DB
    const now = Math.floor(Date.now() / 1000);
    const rowsForDb = files.map(file => ({
      project_id: ACTIVE_PROJECT_ID,
      path: file.zip_path,
      name: file.zip_path.split('/').pop(),
      ext: (file.zip_path.match(/\.[^.]+$/) || [''])[0],
      size_bytes: file.size_bytes,
      created_at: now,
      modified_at: now,
      tag: 'zip-import',
      sha256: file.sha256 || null,
      meta_json: JSON.stringify({
        mime_type: file.mime_type,
        last_modified_utc: file.last_modified_utc,
        source: 'zip'
      })
    }));

    let insertedMsg = 'Insert skipped';
    try {
      const r = await window.db.insertArtifacts(rowsForDb);
      insertedMsg = `Inserted ${r.inserted}`;
      console.log('DB upsert:', r);
    } catch (e) {
      console.warn('DB insert failed:', e);
    }

    // 4) status
    $status.textContent = `Found ${files.length} files · ${insertedMsg}`;
    console.table(files);

  } catch (e) {
    console.error(e);
    $status.textContent = 'Unexpected error — check console';
  } finally {
    // re-enable button only if a file is still selected
    const f2 = $pick.files && $pick.files[0];
    $btn.disabled = !f2;
  }
});
