// src/js/zipImport.js

const $pick   = document.getElementById('zip-picker');
const $btn    = document.getElementById('btn-import-zip');
const $tableB = document.querySelector('#zip-table tbody');
const $status = document.getElementById('zip-status');

const ACTIVE_PROJECT_ID = null;

// ✅ keep the button disabled until a file is picked
$btn.disabled = true;

// ✅ enable the button when a .zip is chosen (and show a hint)
$pick.addEventListener('change', () => {
  const f = $pick.files && $pick.files[0];
  $btn.disabled = !f;
  $status.textContent = f ? 'Ready to scan' : 'Pick a .zip first';
});

function fmtBytes(n) { /* unchanged */ }
function esc(s) { /* unchanged */ }
function renderRows(rows) { /* unchanged */ }

$btn.addEventListener('click', async () => {
  $status.textContent = '';
  const f = $pick.files && $pick.files[0];
  if (!f) {                      // still keep the safety net
    $status.textContent = 'Pick a .zip first';
    return;
  }

  const selectedPath = f.path || f.name;

  try {
    $btn.disabled = true;
    $status.textContent = 'Validating…';
    const v = await window.archiveValidator.validatePath(selectedPath);
    if (!v || !v.ok) { $status.textContent = v?.error || 'Invalid file'; return; }

    $status.textContent = 'Scanning…';
    const res = await window.zipAPI.scan(selectedPath);
    if (!res || !res.ok) { $status.textContent = res?.error || 'Scan failed'; return; }

    const files = res.data || [];
    renderRows(files);

    const now = Math.floor(Date.now() / 1000);
    const rowsForDb = files.map(f => ({
      project_id: ACTIVE_PROJECT_ID,
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

    $status.textContent = `Found ${files.length} files · ${insertedMsg}`;
    console.table(files);
  } catch (e) {
    console.error(e);
    $status.textContent = 'Unexpected error — check console';
  } finally {
    // re-evaluate whether a file is still selected
    const f2 = $pick.files && $pick.files[0];
    $btn.disabled = !f2;
  }
});
