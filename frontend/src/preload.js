const { contextBridge, ipcRenderer } = require("electron")

contextBridge.exposeInMainWorld("api", {
  close: () => ipcRenderer.send("close"),
  minimize: () => ipcRenderer.send("minimize"),
  maximize: () => ipcRenderer.send("maximize")
})

contextBridge.exposeInMainWorld("backendAPI", {
  getUsers: async () => {
    const res = await fetch("http://127.0.0.1:8002/health")
    return await res.json()
  }
})