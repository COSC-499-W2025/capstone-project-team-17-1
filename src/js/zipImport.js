// src/js/zipImport.js (Raunak's issue)

const $pick   = document.getElementById('zip-picker');
const $btn    = document.getElementById('btn-import-zip');
const $tableB = document.querySelector('#zip-table tbody');
const $status = document.getElementById('zip-status');

// If you track a current project, set its ID here (or wire from your UI)
const ACTIVE_PROJECT_ID = null;

function fmtBytes(n) {
  if (n < 1024) return `${n} B`;
  const u = ['KB','MB','GB','TB'];
  let i = -1; do { n /= 1024; i++; } while (n >= 1024 && i < u.length - 1);
  return `${n.toFixed(1)} ${u[i]}`;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
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

$btn.addEventListener('click', async () => {
  $status.textContent = '';
  const f = $pick.files && $pick.files[0];
  if (!f) {
    $status.textContent = 'Pick a .zip first';
    return;
  }

  const selectedPath = f.path || f.name;

  try {
    $btn.disabled = true;
    $status.textContent = 'Validating…';

    // 1) validate
    const v = await window.archiveValidator.validatePath(selectedPath);
    if (!v || !v.ok) {
      $status.textContent = v?.error || 'Invalid file';
      return;
    }

    // 2) scan
    $status.textContent = 'Scanning…';
    const res = await window.zipAPI.scan(selectedPath);
    if (!res.ok) {
      $status.textContent = res.error || 'Scan failed';
      return;
    }

    const files = res.data || [];
    renderRows(files);

    // 3) upsert into DB
    const now = Math.floor(Date.now() / 1000);
    const rowsForDb = files.map(f => ({
      project_id: ACTIVE_PROJECT_ID,                         // set your real project id if available
      path: f.zip_path,
      name: f.zip_path.split('/').pop(),
      ext: (f.zip_path.match(/\.[^.]+$/) || [''])[0],
      size_bytes: f.size_bytes,
      created_at: now,
      modified_at: now,
      tag: 'zip-import',
      sha256: f.sha256 || null,
      meta_json: JSON.stringify({
        mime_type: f.mime_type,
        last_modified_utc: f.last_modified_utc,
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

    // 4) status + dev aid
    $status.textContent = `Found ${files.length} files · ${insertedMsg}`;
    console.table(files);

  } catch (e) {
    console.error(e);
    $status.textContent = 'Unexpected error — check console';
  } finally {
    $btn.disabled = false;
  }
});
