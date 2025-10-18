const fs = require('node:fs');
const path = require('node:path');
const { promisify } = require('node:util');
const { execFile } = require('node:child_process');

const execFileAsync = promisify(execFile);

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

// Analyse commit history for a repository and return contributor breakdown stats.
async function collectGitContributions(repoPath, options = {}) {
  if (!repoPath) throw new Error('Repository path is required');
  const resolvedPath = path.resolve(repoPath);
  if (!fs.existsSync(resolvedPath)) throw new Error(`Repository path does not exist: ${resolvedPath}`);

  await assertGitRepository(resolvedPath);

  const args = ['-C', resolvedPath, 'shortlog', '-sne', '--no-merges'];
  if (options.allBranches) args.push('--all');
  args.push('HEAD');

  let stdout = '';
  try {
    ({ stdout } = await execFileAsync('git', args, { maxBuffer: 10 * 1024 * 1024 }));
  } catch (err) {
    const error = new Error(`Failed to read commit history for ${resolvedPath}`);
    error.cause = err;
    throw error;
  }

  const rawContributors = parseShortlogOutput(stdout, options);
  const extraPatterns = Array.isArray(options.botPatterns) ? options.botPatterns : [];

  const contributors = rawContributors.map((entry) => {
    const isBot = isBotContributor(entry.name, entry.email || '', extraPatterns);
    return {
      ...entry,
      isBot,
    };
  });

  const totalCommits = contributors.reduce((sum, c) => sum + c.commits, 0);
  const humanContributors = contributors.filter((c) => !c.isBot && c.commits > 0);
  const botContributors = contributors.filter((c) => c.isBot && c.commits > 0);
  const totalHumanCommits = humanContributors.reduce((sum, c) => sum + c.commits, 0);
  const totalBotCommits = botContributors.reduce((sum, c) => sum + c.commits, 0);

  const humanContributorCount = humanContributors.length;
  const botContributorCount = botContributors.length;

  const classification = totalHumanCommits === 0
    ? 'unclassified'
    : humanContributorCount <= 1
      ? 'individual'
      : 'collaborative';

  const normalizedContributors = contributors.map((c) => {
    const shareOfTotal = totalCommits > 0 ? c.commits / totalCommits : 0;
    const shareOfHuman = !c.isBot && totalHumanCommits > 0 ? c.commits / totalHumanCommits : null;
    return {
      name: c.name,
      email: c.email,
      commits: c.commits,
      isBot: c.isBot,
      shareOfTotal,
      shareOfHuman,
    };
  });

  const prioritizedEmails = Array.isArray(options.mainUserEmails)
    ? options.mainUserEmails.map((email) => String(email).toLowerCase())
    : [];

  let mainAuthor = null;
  if (prioritizedEmails.length > 0) {
    mainAuthor = humanContributors.find((c) => {
      const email = c.email ? c.email.toLowerCase() : '';
      return prioritizedEmails.includes(email);
    }) || null;
  }
  if (!mainAuthor) {
    mainAuthor = humanContributors[0] || null;
  }

  const mainAuthorShare = mainAuthor && totalHumanCommits > 0
    ? mainAuthor.commits / totalHumanCommits
    : null;

  return {
    classification,
    totalCommits,
    totalHumanCommits,
    totalBotCommits,
    humanContributorCount,
    botContributorCount,
    contributors: normalizedContributors,
    mainAuthor: mainAuthor
      ? {
        name: mainAuthor.name,
        email: mainAuthor.email,
        commits: mainAuthor.commits,
        share: mainAuthorShare,
      }
      : null,
  };
}

module.exports = {
  collectGitContributions,
  isBotContributor,
  DEFAULT_BOT_PATTERNS,
};
