const path = require('node:path');
const { openDb } = require('./connection');

// Fetch the set of projects that have repository metadata so Git analysis can run.
function getProjectsForAnalysis() {
  const db = openDb();
  const rows = db.prepare(`
    SELECT p.id AS project_id,
           p.name AS project_name,
           pr.repo_path,
           pr.main_user_name,
           pr.main_user_email,
           pr.bot_patterns
    FROM project p
    JOIN project_repository pr ON pr.project_id = p.id
  `).all();

  return rows.map((row) => {
    let botPatterns;
    if (row.bot_patterns) {
      try {
        const parsed = JSON.parse(row.bot_patterns);
        if (Array.isArray(parsed)) botPatterns = parsed;
      } catch (e) {
        console.warn('[projectStore] Failed to parse bot_patterns JSON, ignoring:', e.message);
      }
    }

    return {
      id: row.project_id,
      name: row.project_name,
      repoPath: row.repo_path ? path.resolve(row.repo_path) : undefined,
      mainUserName: row.main_user_name || undefined,
      mainUserEmail: row.main_user_email || undefined,
      botPatterns,
    };
  });
}

// Persist the latest Git-derived metrics for a single project.
function upsertProjectAnalysis(projectId, analysis) {
  const db = openDb();
  const totals = analysis.totals || {
    totalCommits: analysis.totalCommits ?? 0,
    totalHumanCommits: analysis.totalHumanCommits ?? analysis.totalCommits ?? 0,
    totalBotCommits: analysis.totalBotCommits ?? 0,
  };

  // Store richer analytics so the renderer can surface advanced metrics/export data.
  const details = {
    totals,
    contributorsDetailed: analysis.contributorsDetailed || [],
    contributorsSummary: analysis.contributors || [],
    timeframe: analysis.timeframe || null,
    weights: analysis.weights || null,
    sharedAccounts: analysis.sharedAccounts || [],
  };

  const mainAuthor = analysis.mainAuthor || null;
  const analyzedAt = analysis.analyzedAt ?? Math.floor(Date.now() / 1000);

  const stmt = db.prepare(`
    INSERT INTO project_analysis (
      project_id,
      classification,
      total_commits,
      human_contributor_count,
      bot_contributor_count,
      main_author_name,
      main_author_email,
      main_author_commits,
      main_author_commit_share,
      analyzed_at,
      details_json
    ) VALUES (@project_id, @classification, @total_commits, @human_contributor_count, @bot_contributor_count,
              @main_author_name, @main_author_email, @main_author_commits, @main_author_commit_share,
              @analyzed_at, @details_json)
    ON CONFLICT(project_id) DO UPDATE SET
      classification = excluded.classification,
      total_commits = excluded.total_commits,
      human_contributor_count = excluded.human_contributor_count,
      bot_contributor_count = excluded.bot_contributor_count,
      main_author_name = excluded.main_author_name,
      main_author_email = excluded.main_author_email,
      main_author_commits = excluded.main_author_commits,
      main_author_commit_share = excluded.main_author_commit_share,
      analyzed_at = excluded.analyzed_at,
      details_json = excluded.details_json
  `);

  stmt.run({
    project_id: projectId,
    classification: analysis.classification,
    total_commits: analysis.totalCommits ?? 0,
    human_contributor_count: analysis.humanContributorCount ?? 0,
    bot_contributor_count: analysis.botContributorCount ?? 0,
    main_author_name: mainAuthor?.name ?? null,
    main_author_email: mainAuthor?.email ?? null,
    main_author_commits: mainAuthor?.commits ?? null,
    main_author_commit_share: mainAuthor?.share ?? null,
    analyzed_at: analyzedAt,
    details_json: JSON.stringify(details),
  });
}

// Provide a combined view that joins projects, repository metadata, and analysis output.
function listProjectSummaries() {
  const db = openDb();
  const rows = db.prepare(`
    SELECT p.id,
           p.name,
           p.created_at,
           pr.repo_path,
           pr.main_user_name,
           pr.main_user_email,
           pa.classification,
           pa.total_commits,
           pa.human_contributor_count,
           pa.bot_contributor_count,
           pa.main_author_name,
           pa.main_author_email,
           pa.main_author_commits,
           pa.main_author_commit_share,
           pa.analyzed_at,
           pa.details_json
    FROM project p
    LEFT JOIN project_repository pr ON pr.project_id = p.id
    LEFT JOIN project_analysis pa ON pa.project_id = p.id
    ORDER BY p.created_at DESC, p.id DESC
  `).all();

  return rows.map((row) => {
    let details = null;
    if (row.details_json) {
      try {
        details = JSON.parse(row.details_json);
      } catch (err) {
        console.warn('[projectStore] Unable to parse project analysis details JSON:', err.message);
      }
    }

    return {
      id: row.id,
      name: row.name,
      createdAt: row.created_at,
      repoPath: row.repo_path || null,
      mainUserName: row.main_user_name || null,
      mainUserEmail: row.main_user_email || null,
      classification: row.classification || 'unknown',
      totalCommits: row.total_commits ?? (details?.totals?.totalCommits ?? 0),
      totalHumanCommits: details?.totals?.totalHumanCommits ?? null,
      totalBotCommits: details?.totals?.totalBotCommits ?? null,
      humanContributorCount: row.human_contributor_count ?? 0,
      botContributorCount: row.bot_contributor_count ?? 0,
      mainAuthor: row.main_author_name ? {
        name: row.main_author_name,
        email: row.main_author_email,
        commits: row.main_author_commits ?? 0,
        share: row.main_author_commit_share ?? 0,
      } : null,
      analyzedAt: row.analyzed_at ?? null,
      details,
    };
  });
}

module.exports = {
  getProjectsForAnalysis,
  upsertProjectAnalysis,
  listProjectSummaries,
};
