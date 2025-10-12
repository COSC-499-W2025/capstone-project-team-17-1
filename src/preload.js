const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('archiveValidator', {
  async validatePath(filePath) {
    return ipcRenderer.invoke('zip:validate', filePath);
  }
});
