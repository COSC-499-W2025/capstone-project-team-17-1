const { contextBridge, ipcRenderer } = require('electron');

// 1) Validate zip path
contextBridge.exposeInMainWorld('archiveValidator', {
  async validatePath(filePath) {
    return ipcRenderer.invoke('zip:validate', filePath);
  }
});

// 2) DB helpers
contextBridge.exposeInMainWorld('db', {
  async queryArtifacts(params) {
    const res = await ipcRenderer.invoke('artifact.query', params);
    if (!res || !res.ok) throw new Error(res?.error || 'artifact.query failed');
    return res.data;
  },
  async insertArtifacts(rows) {
    const res = await ipcRenderer.invoke('artifact.insertMany', rows);
    if (!res || !res.ok) throw new Error(res?.error || 'artifact.insertMany failed');
    return res.data;
  }
});

// 3) Config helpers
contextBridge.exposeInMainWorld('config', {
  load: () => ipcRenderer.invoke('config:load'),
  get: (key, fallback) => ipcRenderer.invoke('config:get', key, fallback),
  set: (key, value) => ipcRenderer.invoke('config:set', key, value),
  merge: (patch) => ipcRenderer.invoke('config:merge', patch),
  reset: () => ipcRenderer.invoke('config:reset')
});

// 4) ZIP API
contextBridge.exposeInMainWorld('zipAPI', {
  scan: (zipPath) => ipcRenderer.invoke('zip:scan', zipPath),
  extractAndHash: (zipPath, outDir) =>
    ipcRenderer.invoke('zip:extractAndHash', zipPath, outDir),
  // NEW: native picker to return an ABSOLUTE path
  pick: () => ipcRenderer.invoke('zip:pick'),
});


console.log('[preload] bridges exposed: archiveValidator, db, config, zipAPI');
