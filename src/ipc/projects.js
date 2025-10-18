const { ipcMain } = require('electron');
const { listProjectSummaries } = require('../db/projectStore');
const { refreshAllProjectAnalysis } = require('../services/projectAnalyzer');

function ok(data) { return { ok: true, data }; }
function fail(err) { return { ok: false, error: String(err?.message || err) }; }

// Register IPC handlers so renderers can list and refresh project analytics.
function registerProjectIpc() {
  ipcMain.handle('project.list', async () => {
    try {
      const rows = listProjectSummaries();
      return ok(rows);
    } catch (err) {
      console.error('[ipc] project.list error:', err);
      return fail(err);
    }
  });

  ipcMain.handle('project.refresh', async () => {
    try {
      // Force a new analysis run before returning summarised rows.
      await refreshAllProjectAnalysis({ logger: console });
      const rows = listProjectSummaries();
      return ok(rows);
    } catch (err) {
      console.error('[ipc] project.refresh error:', err);
      return fail(err);
    }
  });
}

module.exports = {
  registerProjectIpc,
};
