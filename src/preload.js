const { contextBridge, ipcRenderer } = require('electron');

// Expose a safe bridge for renderer code to access the validation IPC.
contextBridge.exposeInMainWorld('archiveValidator', {
  // Call into the main process and return the validation result.
  async validatePath(filePath) {
    return ipcRenderer.invoke('zip:validate', filePath);
  }
});

// Provide limited database helpers so renderer can query artifact data.
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
