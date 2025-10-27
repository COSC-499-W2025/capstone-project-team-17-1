const { app, dialog, ipcMain } = require('electron');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { openDb } = require('../db/connection');
const { validateZipInput } = require('../lib/fileValidator');

function formatDateTime(value) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return formatDateTime(new Date());
  }
  const pad = (n) => String(n).padStart(2, '0');
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

async function ensureUploadsDir() {
  const baseDir = path.join(app.getPath('userData'), 'uploads');
  await fsp.mkdir(baseDir, { recursive: true });
  return baseDir;
}

async function uniqueDestination(baseDir, filename) {
  const sanitized = filename.replace(/[\\/:*?"<>|]/g, '_');
  let candidate = path.join(baseDir, sanitized);
  let counter = 1;
  const ext = path.extname(sanitized);
  const name = ext ? sanitized.slice(0, -ext.length) : sanitized;

  while (fs.existsSync(candidate)) {
    const suffix = `-${counter++}`;
    candidate = path.join(baseDir, `${name}${suffix}${ext}`);
  }
  return candidate;
}

async function copyAndHash(srcPath, destPath) {
  await fsp.copyFile(srcPath, destPath);
  const hash = crypto.createHash('sha256');
  const stream = fs.createReadStream(destPath);
  for await (const chunk of stream) {
    hash.update(chunk);
  }
  return hash.digest('hex');
}

function insertArtifact(row) {
  const db = openDb();
  const stmt = db.prepare(`
    INSERT INTO artifact
    (project_id, path, name, ext, size_bytes, created_at, modified_at, tag, sha256, meta_json)
    VALUES (@project_id, @path, @name, @ext, @size_bytes, @created_at, @modified_at, @tag, @sha256, @meta_json)
  `);
  const info = stmt.run(row);
  return info.lastInsertRowid;
}

function registerFileIpc() {
  ipcMain.handle('file:upload', async (_event, options = {}) => {
    const {
      projectId = null,
      validate: validateType = null,
    } = options;

    const { canceled, filePaths } = await dialog.showOpenDialog({
      properties: ['openFile'],
    });
    if (canceled || !filePaths?.length) return { ok: false, error: 'canceled' };

    const sourcePath = filePaths[0];

    if (validateType === 'zip') {
      const validationResult = validateZipInput(sourcePath);
      if (validationResult) {
        return {
          ok: false,
          error: validationResult.detail || 'InvalidInput',
          code: validationResult.error,
        };
      }
    }

    try {
      const uploadsDir = await ensureUploadsDir();
      const destination = await uniqueDestination(uploadsDir, path.basename(sourcePath));
      const sha256 = await copyAndHash(sourcePath, destination);
      const stats = await fsp.stat(destination);
      const createdAt = Number.isFinite(stats.birthtimeMs)
        ? formatDateTime(stats.birthtime)
        : formatDateTime(new Date());
      const modifiedAt = Number.isFinite(stats.mtimeMs)
        ? formatDateTime(stats.mtime)
        : createdAt;

      const artifactRow = {
        project_id: projectId,
        path: destination,
        name: path.basename(destination),
        ext: path.extname(destination) || null,
        size_bytes: stats.size,
        created_at: createdAt,
        modified_at: modifiedAt,
        tag: 'upload',
        sha256,
        meta_json: JSON.stringify({
          originalPath: sourcePath,
          storedAt: destination,
        }),
      };

      const artifactId = insertArtifact(artifactRow);
      return {
        ok: true,
        data: { id: artifactId, ...artifactRow, storedPath: destination },
      };
    } catch (err) {
      console.error('[ipc] file:upload error:', err);
      return { ok: false, error: err?.message || String(err) };
    }
  });
}

module.exports = { registerFileIpc };
