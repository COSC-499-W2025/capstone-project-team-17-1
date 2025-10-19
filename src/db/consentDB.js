// db helpers for user consent storage
import path from 'path';
import fs from 'fs';
import sqlite3 from 'sqlite3';

// open connnection
// check if user passes in a path, if not default to env var or local file
export function connect(dbPath = null) {
    const targetDBPath = dbPath || process.env.CONSENT_DB_PATH || 'local_consent.db';

    // check if target path exists, if not create directories
    if (targetDBPath !== ':memory:') {
        const dir = path.dirname(targetDBPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    }
        // create database file
        const db = new sqlite3.Database(targetDBPath);
        db.exec('PRAGMA foreign_keys = ON;');   // enable foreign keys
        db.exec('PRAGMA synchronous = NORMAL;');   // set synchronous mode
        return db;
}

// create table
export function initSchema(db) {
    // unique id, consent status, timestamp for logs
    const schema = `
    CREATE TABLE IF NOT EXISTS user_consent (
        consent_id INTEGER PRIMARY KEY AUTOINCREMENT,  
        consent TEXT NOT NULL CHECK(consent IN ('accepted', 'rejected')),
        timestamp TEXT NOT NULL
        );`;
    db.exec(schema);
}

