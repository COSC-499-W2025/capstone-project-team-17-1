const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { openDb } = require('./connection');

function initSchema() {
  const db = openDb();
  // Load the schema definition that initializes all required tables.
  const sql = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf-8');

  db.exec('BEGIN');
  try {
    // Apply the schema inside a transaction so partial failures are rolled back.
    db.exec(sql); 
    db.exec('COMMIT');
  } catch (e) {
    db.exec('ROLLBACK');
    throw e;
  }

  // For right now test we create a few sample data in db
  sampleDataInsert();
  seedSampleProject();
}

//------------------- This whole function is used to clean the existed db and generate sample data to test, remove it at later development ---------------------//
function sampleDataInsert() {
  const db = openDb();

  // Reset the artifact table so the seed data starts from a clean slate.
  db.exec('DELETE FROM artifact;');
  db.exec('DELETE FROM sqlite_sequence WHERE name = \'artifact\';');

  const now = Math.floor(Date.now() / 1000);

  // try edit the data below and rerun "npm start" to test the data changing
  const sampleRows = [
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
      meta_json: JSON.stringify({ note: 'sample data inserted by init.js' }),
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
      meta_json: JSON.stringify({ note: 'seed .js artifact inserted by init.js' }),
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
      meta_json: JSON.stringify({ note: 'seed .pdf artifact inserted by init.js' }),
    },
  ];

  // Prepare a reusable statement to insert each artifact row efficiently.
  const insert = db.prepare(`
    INSERT INTO artifact
    (project_id, path, name, ext, size_bytes, created_at, modified_at, tag, sha256, meta_json)
    VALUES (@project_id, @path, @name, @ext, @size_bytes, @created_at, @modified_at, @tag, @sha256, @meta_json)
  `);

  // Batch insert all rows inside a transaction for integrity and speed.
  const tx = db.transaction((rows) => {
    for (const row of rows) insert.run(row);
  });
  tx(sampleRows);
  console.log(`[seed] ${sampleRows.length} demo artifacts inserted`);
}

function seedSampleProject() {
  const db = openDb();
  const defaultProjectName = 'Capstone Team Workspace';
  const repoPath = path.resolve(process.cwd());
  const now = Math.floor(Date.now() / 1000);

  const existing = db.prepare('SELECT id FROM project WHERE name = ?').get(defaultProjectName);
  let projectId = existing?.id;
  if (!projectId) {
    const info = db.prepare('INSERT INTO project (name, created_at) VALUES (?, ?)').run(defaultProjectName, now);
    projectId = info.lastInsertRowid;
  }

  const upsertRepo = db.prepare(`
    INSERT INTO project_repository (project_id, repo_path, updated_at)
    VALUES (@project_id, @repo_path, @updated_at)
    ON CONFLICT(project_id) DO UPDATE SET
      repo_path = excluded.repo_path,
      updated_at = excluded.updated_at
  `);

  upsertRepo.run({ project_id: projectId, repo_path: repoPath, updated_at: now });
}

module.exports = { initSchema };
