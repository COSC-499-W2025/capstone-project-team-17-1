const fs   = require('node:fs');
const path = require('node:path');
const { openDb } = require('./connection');

/** Run schema.sql once on startup (idempotent). */
function initSchema() {
  const db = openDb();
  const schemaPath = path.join(__dirname, 'schema.sql');
  const sql = fs.readFileSync(schemaPath, 'utf8');

  console.log('[db:init] applying schema from', schemaPath);

  db.exec('PRAGMA foreign_keys = ON');
  db.exec('BEGIN');
  try {
    db.exec(sql);
    db.exec('COMMIT');
  } catch (e) {
    db.exec('ROLLBACK');
    console.error('[db:init] schema failed:', e);
    throw e;
  }

  // Optional: sanity log of created tables
  const tables = db.prepare(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1"
  ).all().map(r => r.name);
  console.log('[db:init] tables:', tables);

  seedDefaultProject();
}

/** Dev-only: ensure a default project + repo row exists. */
function seedDefaultProject() {
  const db = openDb();
  const name = 'Capstone Team Workspace';
  const repoPath = path.resolve(process.cwd());
  const now = Math.floor(Date.now() / 1000);

  const existing = db.prepare('SELECT id FROM project WHERE name=?').get(name);
  const projectId = existing?.id
    ?? db.prepare('INSERT INTO project (name, created_at) VALUES (?, ?)').run(name, now).lastInsertRowid;

  db.prepare(`
    INSERT INTO project_repository (project_id, repo_path, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(project_id) DO UPDATE SET
      repo_path = excluded.repo_path,
      updated_at = excluded.updated_at
  `).run(projectId, repoPath, now);
}

/** Optional helper if you want a plain “apply schema” entry elsewhere. */
function runMigrationsFromFile() {
  const db = openDb();
  const schemaPath = path.join(__dirname, 'schema.sql');
  const sql = fs.readFileSync(schemaPath, 'utf8');
  db.exec('PRAGMA foreign_keys = ON');
  db.exec(sql);
  db.exec('PRAGMA user_version = 1');
}

module.exports = {
  initSchema,
  runMigrationsFromFile,
};
