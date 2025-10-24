const { ipcMain } = require('electron');
const { listProjectSummaries, getProjectsForAnalysis } = require('../db/projectStore');
const { refreshAllProjectAnalysis } = require('../services/projectAnalyzer');
const {
  buildCollaborationAnalysis,
  formatAnalysisAsCSV,
  formatAnalysisAsJSON,
  DEFAULT_CONTRIBUTION_WEIGHTS,
} = require('../lib/gitContributors');

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

  // Allow the renderer to export JSON/CSV snapshots without rereading the repo.
  ipcMain.handle('project.export', async (_event, params = {}) => {
    try {
      const { projectId, format = 'json', includeBots = true, pretty, refresh = false } = params;
      if (!projectId) throw new Error('projectId is required for export');

      let analysis;
      if (refresh) {
        const projects = getProjectsForAnalysis();
        const target = projects.find((project) => project.id === projectId);
        if (!target) throw new Error(`Project ${projectId} not configured for analysis`);
        analysis = await buildCollaborationAnalysis(target.repoPath, {
          mainUserEmails: target.mainUserEmail ? [target.mainUserEmail] : undefined,
          botPatterns: target.botPatterns,
        });
      } else {
        const summary = listProjectSummaries().find((row) => row.id === projectId);
        if (!summary) throw new Error(`Project ${projectId} not found`);
        if (!summary.details) throw new Error('Project has no stored analytics to export');

        const details = summary.details || {};
        const totals = { ...details.totals };
        if (typeof totals.totalCommits !== 'number') totals.totalCommits = summary.totalCommits ?? 0;
        if (typeof totals.totalHumanCommits !== 'number') totals.totalHumanCommits = summary.totalHumanCommits ?? 0;
        if (typeof totals.totalBotCommits !== 'number') totals.totalBotCommits = summary.totalBotCommits ?? 0;

        const contributorsDetailed = Array.isArray(details.contributorsDetailed)
          ? details.contributorsDetailed
          : [];
        let contributorsSummary = Array.isArray(details.contributorsSummary)
          ? details.contributorsSummary
          : null;

        if (!contributorsSummary || contributorsSummary.length === 0) {
          contributorsSummary = contributorsDetailed.map((c) => ({
            name: c.name,
            email: c.email,
            commits: Math.round(c.metrics?.commitsAuthored ?? 0),
            isBot: !!c.isBot,
            shareOfTotal: c.shares?.totalCommits ?? 0,
            shareOfHuman: c.shares?.humanCommits ?? null,
          }));
        }

        const weights = details.weights && typeof details.weights === 'object'
          ? { ...DEFAULT_CONTRIBUTION_WEIGHTS, ...details.weights }
          : { ...DEFAULT_CONTRIBUTION_WEIGHTS };

        analysis = {
          repoPath: summary.repoPath || null,
          repositoryType: 'git',
          classification: summary.classification || 'unknown',
          totals,
          humanContributorCount: summary.humanContributorCount ?? contributorsSummary.filter((c) => !c.isBot && (c.shareOfTotal ?? 0) > 0).length,
          botContributorCount: summary.botContributorCount ?? contributorsSummary.filter((c) => c.isBot && (c.shareOfTotal ?? 0) > 0).length,
          contributorsDetailed,
          contributors: contributorsSummary,
          mainAuthor: summary.mainAuthor || null,
          timeframe: details.timeframe || null,
          weights,
          sharedAccounts: details.sharedAccounts || [],
        };
      }

      let payload;
      if (String(format).toLowerCase() === 'csv') {
        payload = formatAnalysisAsCSV(analysis, { includeBots });
      } else if (String(format).toLowerCase() === 'json') {
        payload = formatAnalysisAsJSON(analysis, { pretty });
      } else {
        throw new Error(`Unsupported export format: ${format}`);
      }

      return ok({ format, projectId, payload });
    } catch (err) {
      console.error('[ipc] project.export error:', err);
      return fail(err);
    }
  });
}

module.exports = {
  registerProjectIpc,
};
