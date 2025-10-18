const { contextBridge, ipcRenderer } = require('electron');

// Expose a safe bridge for renderer code to access the validation IPC.
contextBridge.exposeInMainWorld('archiveValidator', {
  // Call into the main process and return the validation result.
  async validatePath(filePath) {
    return ipcRenderer.invoke('zip:validate', filePath);
  }
});

// Provide limited database helpers so renderer code can manage artifacts.
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

contextBridge.exposeInMainWorld('projects', {
  async list() {
    const res = await ipcRenderer.invoke('project.list');
    if (!res || !res.ok) throw new Error(res?.error || 'project.list failed');
    return res.data;
  },
  async refresh() {
    const res = await ipcRenderer.invoke('project.refresh');
    if (!res || !res.ok) throw new Error(res?.error || 'project.refresh failed');
    return res.data;
  }
});

// Surface config helpers so the renderer can read/write user preferences.
contextBridge.exposeInMainWorld('config', {
  load: () => ipcRenderer.invoke('config:load'),
  get: (key, fallback) => ipcRenderer.invoke('config:get', key, fallback),
  set: (key, value) => ipcRenderer.invoke('config:set', key, value),
  merge: (patch) => ipcRenderer.invoke('config:merge', patch),
  reset: () => ipcRenderer.invoke('config:reset')
});
