const { contextBridge, ipcRenderer } = require("electron")
const skills = require("./mostUsedSkills");
contextBridge.exposeInMainWorld("api", {
  close: () => ipcRenderer.send("close"),
  minimize: () => ipcRenderer.send("minimize"),
  maximize: () => ipcRenderer.send("maximize"),
  platform: process.platform,
})

contextBridge.exposeInMainWorld("backendAPI", {
  getUsers: async () => {
    const res = await fetch("http://127.0.0.1:8002/health")
    return await res.json()
  }
})


contextBridge.exposeInMainWorld("skillsAPI", {
  loadMostUsedSkills: skills.loadMostUsedSkills
});



contextBridge.exposeInMainWorld("loomAI", {
  chat: async (messages) => ipcRenderer.invoke("ai:chat", messages),
});