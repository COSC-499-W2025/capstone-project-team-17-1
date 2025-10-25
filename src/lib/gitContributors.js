const fs = require('node:fs');
const path = require('node:path');
const { promisify } = require('node:util');
const { execFile } = require('node:child_process');

const execFileAsync = promisify(execFile);

// Default scoring weights used when extrapolating contribution impact.
const DEFAULT_CONTRIBUTION_WEIGHTS = {
  commits: 0.4,
  linesChanged: 0.4,
  reviews: 0.2,
};

// Baseline patterns used to recognise common automation accounts.
const DEFAULT_BOT_PATTERNS = [
  /\[bot\]/i,
  /\bbot\b/i,
  /dependabot/i,
  /github-actions/i,
  /semantic-release/i,
  /renovate/i,
];

// Decide whether a contributor entry represents an automation account.
function isBotContributor(name = '', email = '', extraPatterns = []) {
  const haystack = `${name} ${email}`.toLowerCase();
  const patterns = [...DEFAULT_BOT_PATTERNS, ...extraPatterns]
    .map((pattern) => (pattern instanceof RegExp ? pattern : new RegExp(String(pattern), 'i')));
  return patterns.some((pattern) => pattern.test(haystack));
}

// Normalise custom weights so they always sum to 1.0 and fall back to defaults.
function resolveContributionWeights(input = {}) {
  const weights = {
    commits: typeof input.commits === 'number' ? input.commits : DEFAULT_CONTRIBUTION_WEIGHTS.commits,
    linesChanged: typeof input.linesChanged === 'number' ? input.linesChanged : DEFAULT_CONTRIBUTION_WEIGHTS.linesChanged,
    reviews: typeof input.reviews === 'number' ? input.reviews : DEFAULT_CONTRIBUTION_WEIGHTS.reviews,
  };

  const total = weights.commits + weights.linesChanged + weights.reviews;
  if (total <= 0) return { ...DEFAULT_CONTRIBUTION_WEIGHTS };

  return {
    commits: weights.commits / total,
    linesChanged: weights.linesChanged / total,
    reviews: weights.reviews / total,
  };
}

// Convert trailer values like "Alice <alice@example.com>" into structured objects.
function parseIdentity(raw = '') {
  if (!raw) {
    return { name: null, email: null };
  }
  const trimmed = raw.trim();
  const emailMatch = trimmed.match(/<([^>]+)>/);
  const email = emailMatch ? emailMatch[1].trim() : null;
  const name = emailMatch ? trimmed.replace(emailMatch[0], '').trim() : trimmed;
  return {
    name: name || null,
    email: email || null,
  };
}

// Deduplicate identities by lower-cased email or name fallback.
function dedupeIdentities(list = []) {
  const seen = new Set();
  const result = [];
  for (const entry of list) {
    if (!entry) continue;
    const name = (entry.name || '').trim() || null;
    const email = entry.email ? entry.email.trim() : null;
    const key = email ? `email:${email.toLowerCase()}` : name ? `name:${name.toLowerCase()}` : null;
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push({ name, email });
  }
  return result;
}

// Convert `git shortlog` output into structured contributor objects.
function parseShortlogOutput(output, options = {}) {
  const lines = output.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const contributors = [];

  for (const line of lines) {
    const match = line.match(/^([0-9]+)\s+(.+?)(?:\s+<([^>]+)>)?$/);
    if (!match) continue;
    const commits = Number.parseInt(match[1], 10);
    const name = match[2].trim();
    const email = match[3] ? match[3].trim() : null;
    const contributor = {
      name,
      email,
      commits,
    };
    contributors.push(contributor);
  }

  return contributors;
}

// Ensure the provided path is a Git working tree before running expensive commands.
async function assertGitRepository(repoPath) {
  try {
    await execFileAsync('git', ['-C', repoPath, 'rev-parse', '--is-inside-work-tree']);
  } catch (err) {
    const error = new Error(`Not a git repository: ${repoPath}`);
    error.cause = err;
    throw error;
  }
}

// Inspect the working tree and return the repository type (currently Git only).
function detectRepositoryType(repoPath) {
  const resolved = path.resolve(repoPath);
  try {
    const stats = fs.statSync(path.join(resolved, '.git'));
    if (stats.isDirectory()) return 'git';
  } catch (err) {
    // ignore missing .git directory, fallthrough to null
  }
  return null;
}

// Parse git log output that includes numstat entries into structured commit data.
function parseGitLogWithNumstat(output) {
  if (!output) return [];
  const commits = [];
  const rawEntries = output.split('\x1e');

  for (const rawEntry of rawEntries) {
    if (!rawEntry) continue;
    const entry = rawEntry.trim();
    if (!entry) continue;

    const lines = entry.split('\n');
    const headerRaw = lines.shift();
    if (!headerRaw) continue;
    const parts = headerRaw.split('\x1f');
    if (parts.length < 7) continue;

    const [hash, parentsRaw, authorName, authorEmail, authorTimeRaw, subject, coAuthorRaw = '', reviewerRaw = ''] = parts;
    const parentHashes = parentsRaw ? parentsRaw.split(' ').filter(Boolean) : [];
    const authorTime = Number.parseInt(authorTimeRaw, 10);

    const coAuthors = coAuthorRaw
      ? dedupeIdentities(coAuthorRaw.split('\x1d').filter(Boolean).map(parseIdentity))
      : [];
    const reviewers = reviewerRaw
      ? dedupeIdentities(reviewerRaw.split('\x1d').filter(Boolean).map(parseIdentity))
      : [];

    let additions = 0;
    let deletions = 0;
    const files = [];

    for (const line of lines) {
      if (!line || !line.trim()) continue;
      const [addRaw, delRaw, filePath] = line.split('\t');
      if (!filePath) continue;
      const add = addRaw === '-' ? 0 : Number.parseInt(addRaw, 10);
      const del = delRaw === '-' ? 0 : Number.parseInt(delRaw, 10);
      if (!Number.isNaN(add)) additions += add;
      if (!Number.isNaN(del)) deletions += del;
      files.push({ path: filePath, added: add, deleted: del });
    }

    commits.push({
      hash,
      parents: parentHashes,
      isMerge: parentHashes.length > 1,
      author: {
        name: authorName || null,
        email: authorEmail || null,
      },
      timestamp: Number.isFinite(authorTime) ? authorTime : null,
      subject: subject || '',
      coAuthors,
      reviewers,
      additions,
      deletions,
      files,
    });
  }

  return commits;
}

// Collect per-commit statistics including line churn and collaboration trailers.
async function collectGitCommitDetails(repoPath, options = {}) {
  if (!repoPath) throw new Error('Repository path is required');
  const resolvedPath = path.resolve(repoPath);
  if (!fs.existsSync(resolvedPath)) throw new Error(`Repository path does not exist: ${resolvedPath}`);

  await assertGitRepository(resolvedPath);

  const format = '%x1e%H%x1f%P%x1f%an%x1f%ae%x1f%at%x1f%s%x1f%(trailers:key=Co-authored-by,valueonly,separator=%x1d)%x1f%(trailers:key=Reviewed-by,valueonly,separator=%x1d)';
  const args = ['-C', resolvedPath, 'log', '--numstat', '--date-order', `--pretty=format:${format}`];
  if (options.allBranches) args.push('--all');
  if (options.since) args.push(`--since=${options.since}`);
  if (options.until) args.push(`--until=${options.until}`);
  args.push('HEAD');

  let stdout = '';
  try {
    ({ stdout } = await execFileAsync('git', args, { maxBuffer: 10 * 1024 * 1024 }));
  } catch (err) {
    const stderr = err?.stderr || '';
    const stdoutErr = err?.stdout || '';
    const message = err?.message || '';
    const combined = [stderr, stdoutErr, message].join('\n');
    if (/does not have any commits yet|no commits yet|bad default revision|ambiguous argument 'head'|unknown revision or path not in the working tree/i.test(combined)) {
      return [];
    }
    const error = new Error(`Failed to read commit history for ${resolvedPath}`);
    error.cause = err;
    throw error;
  }

  return parseGitLogWithNumstat(stdout);
}

// Aggregate commit statistics into per-contributor metrics and weighted scores for collaboration insights.
async function buildCollaborationAnalysis(repoPath, options = {}) {
  const resolvedPath = path.resolve(repoPath);
  if (!fs.existsSync(resolvedPath)) throw new Error(`Repository path does not exist: ${resolvedPath}`);

  const repoType = detectRepositoryType(resolvedPath);
  if (repoType && repoType !== 'git') {
    throw new Error(`Unsupported repository type: ${repoType}`);
  }

  const commits = await collectGitCommitDetails(resolvedPath, options);
  const weights = resolveContributionWeights(options.weights);
  const extraPatterns = Array.isArray(options.botPatterns) ? options.botPatterns : [];

  const contributors = new Map();
  let anonymousCounter = 0;

  function resolveKey(identity = {}) {
    const email = identity.email ? identity.email.trim().toLowerCase() : null;
    if (email) return `email:${email}`;
    const name = identity.name ? identity.name.trim().toLowerCase() : null;
    if (name) return `name:${name}`;
    anonymousCounter += 1;
    return `anon:${anonymousCounter}`;
  }

  // Register the identity in the contributor map and keep aliases in sync.
  function ensureContributor(identity = {}) {
    const key = resolveKey(identity);
    let entry = contributors.get(key);
    if (!entry) {
      entry = {
        key,
        name: identity.name || null,
        email: identity.email || null,
        emailLower: identity.email ? identity.email.trim().toLowerCase() : null,
        names: new Set(identity.name ? [identity.name] : []),
        emails: new Set(identity.email ? [identity.email.trim().toLowerCase()] : []),
        commitsAuthored: 0,
        commitParticipation: 0,
        commitWeighted: 0,
        sharedCommitUnits: 0,
        sharedCommitEvents: 0,
        coauthoredCommits: 0,
        linesAdded: 0,
        linesDeleted: 0,
        linesByExt: {},  
        filesChanged: 0,
        reviewCount: 0,
        isBot: isBotContributor(identity.name || '', identity.email || '', extraPatterns),
      };
      contributors.set(key, entry);
    }

    if (identity.name) {
      entry.names.add(identity.name);
      if (!entry.name) entry.name = identity.name;
    }
    if (identity.email) {
      const normalized = identity.email.trim().toLowerCase();
      entry.emails.add(normalized);
      if (!entry.emailLower) entry.emailLower = normalized;
      if (!entry.email) entry.email = identity.email;
    }

    // Once an identity is flagged as bot it remains a bot; otherwise prefer human classification.
    const botGuess = isBotContributor(entry.name || identity.name || '', entry.email || identity.email || '', extraPatterns);
    entry.isBot = entry.isBot || botGuess;

    return entry;
  }

  let firstCommitTs = null;
  let lastCommitTs = null;
  let botCommitCount = 0;
  let humanCommitCount = 0;
  let totalFilesChanged = 0;

  for (const commit of commits) {
    if (commit.timestamp) {
      if (firstCommitTs === null || commit.timestamp < firstCommitTs) firstCommitTs = commit.timestamp;
      if (lastCommitTs === null || commit.timestamp > lastCommitTs) lastCommitTs = commit.timestamp;
    }

    const authorIdentity = { name: commit.author?.name || null, email: commit.author?.email || null };
    const authorIsBot = isBotContributor(authorIdentity.name || '', authorIdentity.email || '', extraPatterns);
    if (authorIsBot) botCommitCount += 1; else humanCommitCount += 1;

    const participants = dedupeIdentities([authorIdentity, ...(commit.coAuthors || [])]);
    if (participants.length === 0) continue;

    const filesChanged = new Set((commit.files || []).map(f => f.path)).size;

    totalFilesChanged += filesChanged;

    const participantShare = 1 / participants.length;
    // Only author + co-authors get line credit (we already excluded reviewers here)
const participantsForLines = participants;
const share = participantsForLines.length ? (1 / participantsForLines.length) : 1;

participants.forEach((participant, idx) => {
  const entry = ensureContributor(participant);

  // commit presence/weights
  entry.commitParticipation += 1;
  entry.commitWeighted     += participantShare;

  // line attribution — use the parsed fields
  entry.linesAdded  += (commit.additions || 0) * share;
  entry.linesDeleted+= (commit.deletions || 0) * share;

  // by-extension attribution (added + deleted), split by the same share
  for (const f of (commit.files || [])) {
    const delta = (f.added || 0) + (f.deleted || 0);
    if (!delta) continue;
    const ext = (path.extname(f.path) || '').toLowerCase() || '__noext__';
    entry.linesByExt[ext] = (entry.linesByExt[ext] || 0) + delta * share;
  }

  // files changed & shared-commit stats
  entry.filesChanged += filesChanged * participantShare;
  if (participants.length > 1) {
    entry.sharedCommitUnits  += participantShare;
    entry.sharedCommitEvents += 1;
  }

  // authorship/co-authorship counts
  if (idx === 0) entry.commitsAuthored += 1;
  else           entry.coauthoredCommits += 1;
});


    const reviewers = commit.reviewers || [];
    for (const reviewer of reviewers) {
      const entry = ensureContributor(reviewer);
      entry.reviewCount += 1;
    }
  }

  const totals = {
    totalCommits: commits.length,
    totalHumanCommits: humanCommitCount,
    totalBotCommits: botCommitCount,
    totalWeightedCommits: 0,
    totalHumanWeightedCommits: 0,
    totalBotWeightedCommits: 0,
    totalLinesAdded: 0,
    totalLinesDeleted: 0,
    totalLinesChanged: 0,
    totalHumanLinesChanged: 0,
    totalBotLinesChanged: 0,
    totalFilesChanged,
    totalReviews: 0,
    totalHumanReviews: 0,
    totalBotReviews: 0,
  };

  const contributorList = [];

  for (const entry of contributors.values()) {
    const linesChanged = entry.linesAdded + entry.linesDeleted;
    totals.totalWeightedCommits += entry.commitWeighted;
    totals.totalLinesAdded += entry.linesAdded;
    totals.totalLinesDeleted += entry.linesDeleted;
    totals.totalLinesChanged += linesChanged;
    totals.totalReviews += entry.reviewCount;

    if (entry.isBot) {
      totals.totalBotWeightedCommits += entry.commitWeighted;
      totals.totalBotLinesChanged += linesChanged;
      totals.totalBotReviews += entry.reviewCount;
    } else {
      totals.totalHumanWeightedCommits += entry.commitWeighted;
      totals.totalHumanLinesChanged += linesChanged;
      totals.totalHumanReviews += entry.reviewCount;
    }

    const aliases = {
      names: Array.from(entry.names).filter(Boolean),
      emails: Array.from(entry.emails).filter(Boolean),
    };

    contributorList.push({
      key: entry.key,
      name: entry.name || aliases.names[0] || null,
      email: entry.email || (aliases.emails[0] ? aliases.emails[0] : null),
      emailLower: entry.emailLower || (aliases.emails[0] ? aliases.emails[0].toLowerCase?.() : null),
      isBot: entry.isBot,
      aliases,
      metrics: {
        commitsAuthored: entry.commitsAuthored,
        commitParticipation: entry.commitParticipation,
        commitWeighted: entry.commitWeighted,
        sharedCommitUnits: entry.sharedCommitUnits,
        sharedCommitEvents: entry.sharedCommitEvents,
        coauthoredCommits: entry.coauthoredCommits,
        linesAdded: entry.linesAdded,
        linesDeleted: entry.linesDeleted,
        linesChanged,
        linesByExt: entry.linesByExt,     
        filesChanged: entry.filesChanged,
        reviewCount: entry.reviewCount,
      },
    });
  }

  const humanContributors = contributorList.filter((c) => !c.isBot && c.metrics.commitWeighted > 0);
  const botContributors = contributorList.filter((c) => c.isBot && c.metrics.commitWeighted > 0);

  const contributorsDetailed = contributorList.map((contrib) => {
    const { metrics } = contrib;
    const shareOfTotal = totals.totalWeightedCommits > 0 ? metrics.commitWeighted / totals.totalWeightedCommits : 0;
    const shareOfHuman = !contrib.isBot && totals.totalHumanWeightedCommits > 0
      ? metrics.commitWeighted / totals.totalHumanWeightedCommits
      : null;
    const locShare = totals.totalLinesChanged > 0 ? metrics.linesChanged / totals.totalLinesChanged : 0;
    const locShareHuman = !contrib.isBot && totals.totalHumanLinesChanged > 0
      ? metrics.linesChanged / totals.totalHumanLinesChanged
      : null;
    const reviewShare = totals.totalReviews > 0 ? metrics.reviewCount / totals.totalReviews : 0;
    const reviewShareHuman = !contrib.isBot && totals.totalHumanReviews > 0
      ? metrics.reviewCount / totals.totalHumanReviews
      : null;

    const commitShareForScore = !contrib.isBot && totals.totalHumanWeightedCommits > 0
      ? metrics.commitWeighted / totals.totalHumanWeightedCommits
      : shareOfTotal;
    const locShareForScore = !contrib.isBot && totals.totalHumanLinesChanged > 0
      ? metrics.linesChanged / totals.totalHumanLinesChanged
      : locShare;
    const reviewShareForScore = !contrib.isBot && totals.totalHumanReviews > 0
      ? metrics.reviewCount / totals.totalHumanReviews
      : reviewShare;

    const weightedScore = (weights.commits * commitShareForScore)
      + (weights.linesChanged * locShareForScore)
      + (weights.reviews * reviewShareForScore);

    const isSharedAccount = (contrib.aliases.names.length > 1 || contrib.aliases.emails.length > 1)
      || (metrics.sharedCommitEvents > 0 && metrics.commitsAuthored === 0 && metrics.commitParticipation > 0);

    return {
      ...contrib,
      shares: {
        totalCommits: shareOfTotal,
        humanCommits: shareOfHuman,
        linesChanged: locShare,
        humanLinesChanged: locShareHuman,
        reviews: reviewShare,
        humanReviews: reviewShareHuman,
      },
      scores: {
        weighted: weightedScore,
        normalized: 0,
        breakdown: {
          commits: commitShareForScore,
          linesChanged: locShareForScore,
          reviews: reviewShareForScore,
        },
      },
      flags: {
        isSharedAccount,
      },
    };
  });

  const scoreSumHuman = contributorsDetailed
    .filter((c) => !c.isBot)
    .reduce((sum, c) => sum + c.scores.weighted, 0);

  contributorsDetailed.forEach((contrib) => {
    if (!contrib.isBot && scoreSumHuman > 0) {
      contrib.scores.normalized = contrib.scores.weighted / scoreSumHuman;
    } else if (scoreSumHuman === 0 && !contrib.isBot) {
      contrib.scores.normalized = contributorsDetailed.length > 0 ? 1 / contributorsDetailed.length : 0;
    } else {
      contrib.scores.normalized = 0;
    }
  });

  const prioritizedEmails = Array.isArray(options.mainUserEmails)
    ? options.mainUserEmails.map((email) => String(email).trim().toLowerCase()).filter(Boolean)
    : [];

  let mainAuthor = null;
  if (prioritizedEmails.length > 0) {
    mainAuthor = contributorsDetailed.find((c) => c.emailLower && prioritizedEmails.includes(c.emailLower) && !c.isBot) || null;
  }
  if (!mainAuthor) {
    mainAuthor = contributorsDetailed
      .filter((c) => !c.isBot)
      .sort((a, b) => {
        if (b.scores.normalized !== a.scores.normalized) return b.scores.normalized - a.scores.normalized;
        return (b.metrics.commitWeighted || 0) - (a.metrics.commitWeighted || 0);
      })[0] || null;
  }

  const mainAuthorShare = mainAuthor && mainAuthor.shares.humanCommits != null
    ? mainAuthor.shares.humanCommits
    : (mainAuthor ? mainAuthor.shares.totalCommits : null);

  const summarizedContributors = contributorsDetailed.map((c) => ({
    name: c.name,
    email: c.email,
    commits: Math.round(c.metrics.commitsAuthored),
    isBot: c.isBot,
    shareOfTotal: c.shares.totalCommits,
    shareOfHuman: c.shares.humanCommits,
  }));

  return {
    repoPath: resolvedPath,
    repositoryType: repoType || 'git',
    classification: totals.totalHumanCommits === 0
      ? 'unclassified'
      : humanContributors.length <= 1
        ? 'individual'
        : 'collaborative',
    totals,
    humanContributorCount: humanContributors.length,
    botContributorCount: botContributors.length,
    contributorsDetailed,
    contributors: summarizedContributors,
    mainAuthor: mainAuthor ? {
      name: mainAuthor.name,
      email: mainAuthor.email,
      commits: Math.round(mainAuthor.metrics.commitsAuthored),
      share: mainAuthorShare,
    } : null,
    timeframe: {
      firstCommitAt: firstCommitTs,
      lastCommitAt: lastCommitTs,
      durationDays: firstCommitTs && lastCommitTs
        ? Math.max(1, Math.round((lastCommitTs - firstCommitTs) / 86400))
        : null,
    },
    weights,
    sharedAccounts: contributorsDetailed.filter((c) => c.flags.isSharedAccount).map((c) => ({
      name: c.name,
      email: c.email,
      commitParticipation: c.metrics.commitParticipation,
    })),
  };
}

// Render the analysis into a CSV string for reporting/export purposes.
function formatAnalysisAsCSV(analysis, options = {}) {
  if (!analysis || !Array.isArray(analysis.contributorsDetailed)) {
    throw new Error('Analysis data is required to export CSV');
  }

  const includeBots = options.includeBots !== false;
  const rows = [];
  rows.push([
    'Name',
    'Email',
    'Type',
    'Commits Authored',
    'Commit Participation',
    'Weighted Commits',
    'Shared Commit Ratio',
    'Lines Added',
    'Lines Deleted',
    'Lines Changed',
    'Files Changed (approx)',
    'Reviews',
    'Score (weighted)',
    'Score (normalized)',
  ].join(','));

  // Format numerics so exported spreadsheets stay readable.
  const formatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 });

  for (const contrib of analysis.contributorsDetailed) {
    if (!includeBots && contrib.isBot) continue;
    const sharedRatio = contrib.metrics.commitParticipation > 0
      ? contrib.metrics.sharedCommitEvents / contrib.metrics.commitParticipation
      : 0;
    rows.push([
      JSON.stringify(contrib.name ?? ''),
      JSON.stringify(contrib.email ?? ''),
      contrib.isBot ? 'bot' : 'human',
      formatter.format(contrib.metrics.commitsAuthored),
      formatter.format(contrib.metrics.commitParticipation),
      formatter.format(contrib.metrics.commitWeighted),
      formatter.format(sharedRatio),
      formatter.format(contrib.metrics.linesAdded),
      formatter.format(contrib.metrics.linesDeleted),
      formatter.format(contrib.metrics.linesChanged),
      formatter.format(contrib.metrics.filesChanged),
      formatter.format(contrib.metrics.reviewCount),
      formatter.format(contrib.scores.weighted),
      formatter.format(contrib.scores.normalized || 0),
    ].join(','));
  }

  return rows.join('\n');
}

// Convert the analysis into a JSON string suitable for file export.
function formatAnalysisAsJSON(analysis, options = {}) {
  if (!analysis) throw new Error('Analysis data is required to export JSON');
  const payload = {
    repoPath: analysis.repoPath,
    repositoryType: analysis.repositoryType,
    classification: analysis.classification,
    timeframe: analysis.timeframe,
    totals: analysis.totals,
    weights: analysis.weights,
    mainAuthor: analysis.mainAuthor,
    humanContributorCount: analysis.humanContributorCount,
    botContributorCount: analysis.botContributorCount,
    contributors: analysis.contributorsDetailed,
    sharedAccounts: analysis.sharedAccounts,
  };
  const space = options.pretty === false ? 0 : (typeof options.pretty === 'number' ? options.pretty : 2);
  return JSON.stringify(payload, null, space);
}

// Backwards-compatible summary API used by existing callers.
async function collectGitContributions(repoPath, options = {}) {
  const analysis = await buildCollaborationAnalysis(repoPath, options);
  return {
    classification: analysis.classification,
    totalCommits: analysis.totals.totalCommits,
    totalHumanCommits: analysis.totals.totalHumanCommits,
    totalBotCommits: analysis.totals.totalBotCommits,
    humanContributorCount: analysis.humanContributorCount,
    botContributorCount: analysis.botContributorCount,
    contributors: analysis.contributors,
    mainAuthor: analysis.mainAuthor,
  };
}

module.exports = {
  DEFAULT_BOT_PATTERNS,
  DEFAULT_CONTRIBUTION_WEIGHTS,
  buildCollaborationAnalysis,
  collectGitCommitDetails,
  collectGitContributions,
  detectRepositoryType,
  formatAnalysisAsCSV,
  formatAnalysisAsJSON,
  isBotContributor,
  resolveContributionWeights,
};
