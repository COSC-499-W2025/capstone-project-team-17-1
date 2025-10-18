const { iterZipMetadata, extractAndHash } = require("../lib/zipParser");

async function collect(it) {
  const out = [];
  for await (const x of it) out.push(x);
  return out;
}

function registerZipIpc(ipcMain) {
  ipcMain.handle("zip:scan", async (_evt, zipPath) => {
    try {
      const data = await collect(iterZipMetadata(zipPath));
      return { ok: true, data };
    } catch (e) {
      return { ok: false, error: e?.message || String(e) };
    }
  });

  ipcMain.handle("zip:extractAndHash", async (_evt, zipPath, outDir) => {
    try {
      const data = await collect(extractAndHash(zipPath, outDir));
      return { ok: true, data };
    } catch (e) {
      return { ok: false, error: e?.message || String(e) };
    }
  });
}

module.exports = { registerZipIpc };
