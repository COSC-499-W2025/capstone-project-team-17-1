const Database = require('better-sqlite3');
const { app } = require('electron');
const fs = require('node:fs');
const path = require('node:path');

function getDbPath() {
  const dir = path.join(process.cwd(), 'src/db');
  // Ensure the database folder exists before creating or opening the file.
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, 'app.db');
}

let db = null;

function openDb() {
  // Reuse the same handle so WAL mode and caches stay consistent.
  if (db) return db;
  db = new Database(getDbPath(), { fileMustExist: false });
  // Set pragmatic flags to provide safer concurrent writes for SQLite.
  db.pragma('journal_mode = WAL');
  db.pragma('synchronous = NORMAL');
  db.pragma('foreign_keys = ON');
  return db;
}

function closeDb() {
  if (db) { db.close(); db = null; }
}

module.exports = { openDb, closeDb, getDbPath };