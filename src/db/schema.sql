CREATE TABLE IF NOT EXISTS project (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS project_repository (
  project_id INTEGER PRIMARY KEY REFERENCES project(id) ON DELETE CASCADE,
  repo_path TEXT NOT NULL,
  main_user_name TEXT,
  main_user_email TEXT,
  bot_patterns TEXT,
  meta_json TEXT,
  created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS project_analysis (
  project_id INTEGER PRIMARY KEY REFERENCES project(id) ON DELETE CASCADE,
  classification TEXT NOT NULL,
  total_commits INTEGER NOT NULL,
  human_contributor_count INTEGER NOT NULL,
  bot_contributor_count INTEGER NOT NULL,
  main_author_name TEXT,
  main_author_email TEXT,
  main_author_commits INTEGER,
  main_author_commit_share REAL,
  analyzed_at INTEGER NOT NULL,
  details_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_project_analysis_classification ON project_analysis(classification);
CREATE INDEX IF NOT EXISTS idx_project_analysis_human_count ON project_analysis(human_contributor_count);

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
