const unzipper = require('unzipper');

// Normalize entry paths
function normalizeEntryPath(entryPath) {
  if (typeof entryPath !== 'string') return '';
  return entryPath.replace(/\\/g, '/').replace(/\/{2,}/g, '/').replace(/^\/+/, '');
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

module.exports = {
  iterZipEntries,
};
