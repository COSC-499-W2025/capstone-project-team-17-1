const { contextBridge } = require("electron")

contextBridge.exposeInMainWorld("backendAPI", {
  getUsers: async () => {
    const res = await fetch("http://127.0.0.1:8002/health")
    return await res.json()
  }
})