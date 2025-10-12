const { contextBridge, ipcRenderer } = require('electron');

// Expose a safe bridge for renderer code to access the validation IPC.
contextBridge.exposeInMainWorld('archiveValidator', {
  // Call into the main process and return the validation result.
  async validatePath(filePath) {
    return ipcRenderer.invoke('zip:validate', filePath);
  }
});
