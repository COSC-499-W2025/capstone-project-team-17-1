const { collectGitContributions } = require('../lib/gitContributors');
const { getProjectsForAnalysis, upsertProjectAnalysis } = require('../db/projectStore');

// Walk through all known projects, collect Git metrics, and store the snapshot.
async function refreshAllProjectAnalysis(options = {}) {
  const { logger = console } = options;
  const projects = getProjectsForAnalysis();
  const analyzedAt = Math.floor(Date.now() / 1000);

  for (const project of projects) {
    if (!project.repoPath) {
      // Without a repo path we cannot inspect commits, so skip gracefully.
      logger.warn?.(`[projectAnalyzer] Project "${project.name}" has no repository path, skipping analysis.`);
      continue;
    }

    try {
      const analysis = await collectGitContributions(project.repoPath, {
        mainUserEmails: project.mainUserEmail ? [project.mainUserEmail] : undefined,
        botPatterns: project.botPatterns,
      });

      upsertProjectAnalysis(project.id, {
        classification: analysis.classification,
        totalCommits: analysis.totalCommits,
        totalHumanCommits: analysis.totalHumanCommits,
        totalBotCommits: analysis.totalBotCommits,
        humanContributorCount: analysis.humanContributorCount,
        botContributorCount: analysis.botContributorCount,
        contributors: analysis.contributors,
        mainAuthor: analysis.mainAuthor,
        analyzedAt,
      });
    } catch (err) {
      logger.error?.(`[projectAnalyzer] Failed to analyze project "${project.name}" at ${project.repoPath}: ${err.message}`);
    }
  }
}

module.exports = {
  refreshAllProjectAnalysis,
};
