const path = require('path');
const fs = require('fs');
const Database = require('better-sqlite3');

// Open connection to consent database, ensuring directory exists when using a file-backed DB.
function connect(dbPath = null) {
  const targetDBPath = dbPath || process.env.CONSENT_DB_PATH || 'local_consent.db';

  if (targetDBPath !== ':memory:') {
    const dir = path.dirname(targetDBPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  const db = new Database(targetDBPath);
  db.pragma('foreign_keys = ON');
  db.pragma('synchronous = NORMAL');
  return db;
}

// Ensure consent table exists.
function initSchema(db) {
  const schema = `
    CREATE TABLE IF NOT EXISTS user_consent (
        consent_id INTEGER PRIMARY KEY AUTOINCREMENT,
        consent TEXT NOT NULL CHECK(consent IN ('accepted', 'rejected')),
        timestamp TEXT NOT NULL
    );`;
  db.exec(schema);
}

module.exports = { connect, initSchema };
