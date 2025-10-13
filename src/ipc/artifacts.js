const { ipcMain } = require('electron');
const { openDb } = require('../db/connection');

// Helpers to normalize IPC responses with a consistent shape.
function ok(data)  { return { ok: true, data }; }
function fail(err) { return { ok: false, error: String(err && err.message || err) }; }

function registerArtifactIpc() {
  // Handle artifact list queries coming from renderer processes.
  ipcMain.handle('artifact.query', async (_e, params = {}) => {
    try {
      const db = openDb();
      const where = [];
      const args  = [];

      // Build the WHERE clause dynamically based on provided filters.
      if (params.projectId) { where.push('project_id = ?'); args.push(params.projectId); }
      if (params.tag)       { where.push('tag = ?');        args.push(params.tag); }
      if (params.from)      { where.push('modified_at >= ?'); args.push(params.from); }
      if (params.to)        { where.push('modified_at < ?');  args.push(params.to); }
      if (params.q)         { where.push('(name LIKE ? OR path LIKE ?)'); args.push(`%${params.q}%`, `%${params.q}%`); }

      const sql = `
        SELECT id, project_id, path, name, ext, size_bytes, created_at, modified_at, tag
        FROM artifact
        ${where.length ? 'WHERE ' + where.join(' AND ') : ''}
        ORDER BY modified_at DESC
        LIMIT ? OFFSET ?`;
      args.push(params.limit ?? 100, params.offset ?? 0);

      const rows = db.prepare(sql).all(...args);
      return ok(rows);
    } catch (err) {
      console.error('[ipc] artifact.query error:', err);
      return fail(err);
    }
  });

  // Handle bulk artifact upserts to keep the database in sync with incoming data.
  ipcMain.handle('artifact.insertMany', async (_e, rows = []) => {
    try {
      const db = openDb();
      const insert = db.prepare(`
        INSERT OR IGNORE INTO artifact
        (project_id, path, name, ext, size_bytes, created_at, modified_at, tag, sha256, meta_json)
        VALUES (@project_id, @path, @name, @ext, @size_bytes, @created_at, @modified_at, @tag, @sha256, @meta_json)
      `);
      // Use a transaction so either the whole batch is inserted or none of it is.
      const tx = db.transaction((batch) => { for (const r of batch) insert.run(r); });
      tx(rows);
      return ok({ inserted: rows.length });
    } catch (err) {
      console.error('[ipc] artifact.insertMany error:', err);
      return fail(err);
    }
  });
}

module.exports = { registerArtifactIpc };