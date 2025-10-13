CREATE TABLE IF NOT EXISTS project (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS artifact (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER REFERENCES project(id) ON DELETE SET NULL,
  path TEXT NOT NULL,
  name TEXT NOT NULL,
  ext  TEXT,  /*format*/
  size_bytes INTEGER,
  created_at  INTEGER,
  modified_at INTEGER,
  tag  TEXT,  /*doc, develop, image...*/
  sha256 TEXT, /*hash value to avoid duplicate file*/
  meta_json TEXT,
  UNIQUE(path, modified_at)
);

CREATE INDEX IF NOT EXISTS idx_artifact_project    ON artifact(project_id);
CREATE INDEX IF NOT EXISTS idx_artifact_modifiedat ON artifact(modified_at);
CREATE INDEX IF NOT EXISTS idx_artifact_tag        ON artifact(tag);
CREATE INDEX IF NOT EXISTS idx_artifact_sha256     ON artifact(sha256);