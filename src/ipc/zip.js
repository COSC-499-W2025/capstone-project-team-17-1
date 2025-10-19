// src/ipc/zip.js
const { dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { iterZipMetadata, extractAndHash } = require('../lib/zipParser');

async function collect(iterable) {
  const out = [];
  for await (const x of iterable) out.push(x);
  return out;
}

function registerZipIpc(ipcMain) {
  // 1) Native picker: returns an absolute .zip path
  ipcMain.handle('zip:pick', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [{ name: 'ZIP archives', extensions: ['zip'] }],
    });
    if (canceled || !filePaths?.[0]) return { ok: false, error: 'canceled' };
    return { ok: true, path: filePaths[0] };
  });

  // 2) Scan inside zip (no extraction)
  ipcMain.handle('zip:scan', async (_evt, zipPath) => {
    try {
      if (typeof zipPath !== 'string' || !zipPath.toLowerCase().endsWith('.zip')) {
        return { ok: false, error: 'InvalidInput: expected a .zip path' };
      }
      if (!fs.existsSync(zipPath)) {
        return { ok: false, error: `NotFound: ${zipPath}` };
      }
      const data = await collect(iterZipMetadata(zipPath));
      return { ok: true, data };
    } catch (e) {
      return { ok: false, error: e?.message || String(e) };
    }
  });

  // 3) Optional: extract and hash
  ipcMain.handle('zip:extractAndHash', async (_evt, zipPath, outDir) => {
    try {
      if (!fs.existsSync(zipPath)) return { ok: false, error: `NotFound: ${zipPath}` };
      const target = outDir || path.join(process.cwd(), 'unzipped');
      const data = await collect(extractAndHash(zipPath, target));
      return { ok: true, data };
    } catch (e) {
      return { ok: false, error: e?.message || String(e) };
    }
  });
}

module.exports = { registerZipIpc };
