// src/db/init.js
const fs   = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
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

  // Dev seeds (okay to keep for now)
  seedArtifacts();
  seedDefaultProject();
}

/** Dev-only: sample artifacts so UI has something to show. */
function seedArtifacts() {
  const db = openDb();
  db.exec("DELETE FROM artifact;");
  db.exec("DELETE FROM sqlite_sequence WHERE name='artifact';");

  const now = Math.floor(Date.now() / 1000);
  const rows = [
    {
      project_id: null,
      path: 'sample/demo-file-1.txt',
      name: 'demo-file.txt',
      ext: 'txt',
      size_bytes: 120,
      created_at: now - 120,
      modified_at: now - 60,
      tag: 'doc',
      sha256: crypto.createHash('sha256').update('demo-file-1').digest('hex'),
      meta_json: JSON.stringify({ note: 'seeded by init.js' }),
    },
    {
      project_id: null,
      path: 'sample/demo-script.js',
      name: 'demo-script.js',
      ext: 'js',
      size_bytes: 1024,
      created_at: now - 300,
      modified_at: now - 240,
      tag: 'code',
      sha256: crypto.createHash('sha256').update('demo-script.js').digest('hex'),
      meta_json: JSON.stringify({ note: 'seeded by init.js' }),
    },
    {
      project_id: null,
      path: 'sample/project-report.pdf',
      name: 'project-report.pdf',
      ext: 'pdf',
      size_bytes: 2048,
      created_at: now - 180,
      modified_at: now - 120,
      tag: 'report',
      sha256: crypto.createHash('sha256').update('project-report.pdf').digest('hex'),
      meta_json: JSON.stringify({ note: 'seeded by init.js' }),
    },
  ];

  const insert = db.prepare(`
    INSERT INTO artifact
      (project_id, path, name, ext, size_bytes, created_at, modified_at, tag, sha256, meta_json)
    VALUES
      (@project_id, @path, @name, @ext, @size_bytes, @created_at, @modified_at, @tag, @sha256, @meta_json)
  `);
  db.transaction((all) => { for (const r of all) insert.run(r); })(rows);

  console.log(`[seed] ${rows.length} demo artifacts inserted`);
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
