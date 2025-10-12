const { contextBridge, ipcRenderer } = require('electron');

// Expose a safe bridge for renderer code to access the validation IPC.
contextBridge.exposeInMainWorld('archiveValidator', {
  // Call into the main process and return the validation result.
  async validatePath(filePath) {
    return ipcRenderer.invoke('zip:validate', filePath);
  }
});

contextBridge.exposeInMainWorld("config", {
  load: () => ipcRenderer.invoke("config:load"),
  get: (k, f) => ipcRenderer.invoke("config:get", k, f),
  set: (k, v) => ipcRenderer.invoke("config:set", k, v),
  merge: (p) => ipcRenderer.invoke("config:merge", p),
  reset: () => ipcRenderer.invoke("config:reset")
});