const path = require('node:path');
const unzipper = require('unzipper');

// Normalize entry paths
function normalizeEntryPath(entryPath) {
  if (typeof entryPath !== 'string') return '';
  return entryPath.replace(/\\/g, '/').replace(/\/{2,}/g, '/').replace(/^\/+/, '');
}

function dosDateTimeToDate(dateBits, timeBits) {
  if (!Number.isInteger(dateBits) || !Number.isInteger(timeBits)) return null;
  const day = dateBits & 0x1f;
  const month = (dateBits >> 5) & 0x0f;
  const year = ((dateBits >> 9) & 0x7f) + 1980;
  const second = (timeBits & 0x1f) * 2;
  const minute = (timeBits >> 5) & 0x3f;
  const hour = (timeBits >> 11) & 0x1f;
  if (!day || !month) return null;
  return new Date(Date.UTC(year, month - 1, day, hour, minute, second));
}

function pickExtraTime(entry, field) {
  const extra = entry?.extra;
  if (!extra || typeof extra !== 'object') return null;

  const extended = extra.ExtendedTimestamp;
  if (extended && extended[field] instanceof Date) return extended[field];

  const ntfs = extra.NTFS;
  if (ntfs && ntfs[field] instanceof Date) return ntfs[field];

  const infoZip = extra.InfoZipUnix;
  if (infoZip && infoZip[field] instanceof Date) return infoZip[field];

  return null;
}

function getEntryModifiedDate(entry) {
  if (!entry) return null;

  if (entry.lastModifiedDateTime instanceof Date) {
    return entry.lastModifiedDateTime;
  }

  const fromExtra = pickExtraTime(entry, 'mtime');
  if (fromExtra) return fromExtra;

  if (Number.isInteger(entry.lastModifiedDate) && Number.isInteger(entry.lastModifiedTime)) {
    const maybe = dosDateTimeToDate(entry.lastModifiedDate, entry.lastModifiedTime);
    if (maybe) return maybe;
  }

  return null;
}

function getEntryCreationDate(entry) {
  if (!entry) return null;

  const fromExtra = pickExtraTime(entry, 'ctime');
  if (fromExtra) return fromExtra;

  if (Number.isInteger(entry.creationDate) && Number.isInteger(entry.creationTime)) {
    const maybe = dosDateTimeToDate(entry.creationDate, entry.creationTime);
    if (maybe) return maybe;
  }

  return null;
}

// Walks every entry inside a ZIP archive, including nested folders
async function* iterZipEntries(zipPath) {
  const archive = await unzipper.Open.file(zipPath);
  for (const entry of archive.files) {
    const normalizedPath = normalizeEntryPath(entry.path);
    const type = entry.type === 'Directory' ? 'directory' : 'file';
    yield {
      type,
      path: normalizedPath,
      raw: entry,
    };
  }
}

async function* iterZipMetadata(zipPath) {
  for await (const entry of iterZipEntries(zipPath)) {
    if (entry.type !== 'file') continue;
    const raw = entry.raw;
    const size = Number(raw?.uncompressedSize ?? raw?.vars?.uncompressedSize ?? 0);
    const createdAt = getEntryCreationDate(raw);
    const modifiedAt = getEntryModifiedDate(raw);
    const extname = path.extname(entry.path || '');
    const format = extname ? extname.slice(1).toLowerCase() || null : null;
    yield {
      zip_path: entry.path,
      size_bytes: Number.isFinite(size) ? size : 0,
      created_utc: createdAt ? createdAt.toISOString() : null,
      last_modified_utc: modifiedAt ? modifiedAt.toISOString() : null,
      format,
    };
  }
}

// Collect metadata from ZIP and log each entry as JSON.
// We only print to the console for now; JSONL persistence may return later
async function collectZipMetadata(zipPath, options = {}) {
  const {
    log = true,
  } = options;

  const start = process.hrtime.bigint();
  let totalBytes = 0;
  const rows = [];
  for await (const meta of iterZipMetadata(zipPath)) {
    rows.push(meta);
    const size = Number(meta.size_bytes) || 0;
    totalBytes += size;
  }
  const durationNs = process.hrtime.bigint() - start;
  const durationMs = Number(durationNs) / 1e6;

  if (log) {
    rows.forEach((row) => {
      console.log('[zipParser] metadata', JSON.stringify(row));
    });
    console.log('[zipParser] summary', JSON.stringify({
      zip: path.basename(zipPath),
      files: rows.length,
      total_bytes: totalBytes,
      duration_ms: Number(durationMs.toFixed(3)),
    }));
  }

  return {
    rows,
    count: rows.length,
    totalBytes,
    durationMs,
  };
}

module.exports = {
  iterZipEntries,
  iterZipMetadata,
  collectZipMetadata,
};
