// src/db/projectStore.js
const path = require('node:path');
const { openDb } = require('./connection');

/* -------------------------------------------------------
   CREATE / UPSERT HELPERS
   -----------------------------------------------------*/

/**
 * Create a new project row and its 1:1 repository metadata.
 * Returns the new projectId (INTEGER).
 */
function createProjectWithRepo({ name, repoPath, mainUserName, mainUserEmail, botPatterns, metaJson }) {
  const db = openDb();
  const now = Math.floor(Date.now() / 1000);

  const tx = db.transaction(() => {
    const { lastInsertRowid } = db
      .prepare(`INSERT INTO project (name, created_at) VALUES (?, ?)`)
      .run(name || 'Unnamed Project', now);
    const projectId = Number(lastInsertRowid);

    db.prepare(
      `INSERT INTO project_repository
         (project_id, repo_path, main_user_name, main_user_email, bot_patterns, meta_json, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(project_id) DO UPDATE SET
         repo_path       = excluded.repo_path,
         main_user_name  = excluded.main_user_name,
         main_user_email = excluded.main_user_email,
         bot_patterns    = excluded.bot_patterns,
         meta_json       = excluded.meta_json,
         updated_at      = excluded.updated_at`
    ).run(
      projectId,
      repoPath || '',
      mainUserName ?? null,
      mainUserEmail ?? null,
      botPatterns ? JSON.stringify(botPatterns) : null,
      metaJson ? JSON.stringify(metaJson) : null,
      now,
      now
    );

    return projectId;
  });

  return tx();
}

/**
 * Save (or update) the latest Git-derived metrics for a single project.
 * Matches your schema where project_analysis PK = project_id (latest only).
 */
function upsertProjectAnalysis(projectId, analysis) {
  const db = openDb();
  const totals = analysis.totals || {
    totalCommits: analysis.totalCommits ?? 0,
    totalHumanCommits: analysis.totalHumanCommits ?? analysis.totalCommits ?? 0,
    totalBotCommits: analysis.totalBotCommits ?? 0,
  };

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

  // accept either `share` or `contributionShare`
  const share =
    (mainAuthor && (mainAuthor.share ?? mainAuthor.contributionShare)) ?? null;

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
    classification: analysis.classification || 'unknown',
    total_commits: analysis.totalCommits ?? totals.totalCommits ?? 0,
    human_contributor_count:
      analysis.humanContributorCount ??
      (Array.isArray(details.contributorsSummary)
        ? details.contributorsSummary.filter((c) => !c.isBot && (c.shareOfTotal ?? 0) > 0).length
        : 0),
    bot_contributor_count:
      analysis.botContributorCount ??
      (Array.isArray(details.contributorsSummary)
        ? details.contributorsSummary.filter((c) => c.isBot && (c.shareOfTotal ?? 0) > 0).length
        : 0),
    main_author_name: mainAuthor?.name ?? null,
    main_author_email: mainAuthor?.email ?? null,
    main_author_commits: mainAuthor?.commits ?? null,
    main_author_commit_share: share,
    analyzed_at: analyzedAt,
    details_json: JSON.stringify(details),
  });
}
// Fetch one project + its latest analysis/details by id.
function getProjectAnalysisById(projectId) {
  const db = openDb();
  const row = db.prepare(`
    SELECT
      p.id,
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
    LEFT JOIN project_analysis pa   ON pa.project_id = p.id
    WHERE p.id = ?
    LIMIT 1
  `).get(projectId);

  if (!row) return null;

  let details = null;
  if (row.details_json) {
    try { details = JSON.parse(row.details_json); }
    catch (err) {
      console.warn('[projectStore] Unable to parse details_json:', err.message);
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
    details, // <- this includes contributorsDetailed, contributorsSummary, totals, timeframe, etc.
  };
}

/**
 * One-shot convenience: create project+repo, then upsert analysis in a single transaction.
 * Returns projectId.
 */
function saveProjectAnalysisTx(n) {
  const db = openDb();
  const now = Math.floor(Date.now() / 1000);

  const tx = db.transaction(() => {
    // create project + repo
    const projectId = createProjectWithRepo({
      name: n.name,
      repoPath: n.repoPath,
      mainUserName: n.mainAuthorName,
      mainUserEmail: n.mainAuthorEmail,
      botPatterns: n.botPatterns,
      metaJson: n.metaJson,
    });

    // upsert analysis
    upsertProjectAnalysis(projectId, {
      classification: n.classification,
      totalCommits: n.totalCommits,
      humanContributorCount: n.humanContributorCount,
      botContributorCount: n.botContributorCount,
      mainAuthor: {
        name: n.mainAuthorName,
        email: n.mainAuthorEmail,
        commits: n.mainAuthorCommits,
        share: n.mainAuthorShare, // accepts either share or contributionShare in upsert
      },
      analyzedAt: n.analyzedAt,
      totals: n.totals,
      contributors: n.contributors,
      contributorsDetailed: n.contributorsDetailed,
      timeframe: n.timeframe,
      weights: n.weights,
      sharedAccounts: n.sharedAccounts,
    });

    return projectId;
  });

  return tx();
}

/* -------------------------------------------------------
   READ / LIST QUERIES
   -----------------------------------------------------*/

function getProjectsForAnalysis() {
  const db = openDb();
  const rows = db
    .prepare(
      `
    SELECT p.id AS project_id,
           p.name AS project_name,
           pr.repo_path,
           pr.main_user_name,
           pr.main_user_email,
           pr.bot_patterns
    FROM project p
    JOIN project_repository pr ON pr.project_id = p.id
  `
    )
    .all();

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

function listProjectSummaries() {
  const db = openDb();
  const rows = db
    .prepare(
      `
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
  `
    )
    .all();

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
      mainAuthor: row.main_author_name
        ? {
            name: row.main_author_name,
            email: row.main_author_email,
            commits: row.main_author_commits ?? 0,
            share: row.main_author_commit_share ?? 0,
          }
        : null,
      analyzedAt: row.analyzed_at ?? null,
      details,
    };
  });
}

/* -------------------------------------------------------
   EXPORTS
   -----------------------------------------------------*/
module.exports = {
  createProjectWithRepo,
  getProjectsForAnalysis,
  upsertProjectAnalysis,
  saveProjectAnalysisTx,
  listProjectSummaries,
  getProjectAnalysisById,
};
