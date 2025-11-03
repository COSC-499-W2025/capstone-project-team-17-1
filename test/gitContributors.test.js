const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execSync } = require('node:child_process');

const {
  collectGitContributions,
  buildCollaborationAnalysis,
  formatAnalysisAsCSV,
  formatAnalysisAsJSON,
} = require('../src/lib/gitContributors');

// Helper to execute git commands without polluting user configs or prompting.
function runGit(repoDir, args, options = {}) {
  const result = execSync(`git ${args}`, {
    cwd: repoDir,
    stdio: 'ignore',
    env: {
      ...process.env,
      GIT_TERMINAL_PROMPT: '0',
      GIT_CONFIG_NOSYSTEM: '1',
      ...options.env,
    },
  });
  return result;
}

// Spin up an isolated git repo for each test case and clean it afterwards.
function createTempRepo(t) {
  const repoDir = fs.mkdtempSync(path.join(os.tmpdir(), 'git-project-')); 
  t.after(() => {
    fs.rmSync(repoDir, { recursive: true, force: true });
  });

  runGit(repoDir, 'init');
  runGit(repoDir, 'config user.name "Test User"');
  runGit(repoDir, 'config user.email "test@example.com"');
  return repoDir;
}

test('collectGitContributions treats single human contributor as individual even with bots', async (t) => {
  const repoDir = createTempRepo(t);

  fs.writeFileSync(path.join(repoDir, 'README.md'), '# Sample Repo\n');
  runGit(repoDir, 'add README.md');
  runGit(repoDir, 'commit -m "Initial commit"', {
    env: {
      GIT_AUTHOR_NAME: 'Alice',
      GIT_AUTHOR_EMAIL: 'alice@example.com',
      GIT_COMMITTER_NAME: 'Alice',
      GIT_COMMITTER_EMAIL: 'alice@example.com',
    },
  });

  // Add a commit attributed to a bot account and confirm it is excluded.
  fs.writeFileSync(path.join(repoDir, 'bot.txt'), 'bot change\n');
  runGit(repoDir, 'add bot.txt');
  runGit(repoDir, 'commit -m "Automated update"', {
    env: {
      GIT_AUTHOR_NAME: 'dependabot[bot]',
      GIT_AUTHOR_EMAIL: '49699333+dependabot[bot]@users.noreply.github.com',
      GIT_COMMITTER_NAME: 'dependabot[bot]',
      GIT_COMMITTER_EMAIL: '49699333+dependabot[bot]@users.noreply.github.com',
    },
  });

  const analysis = await collectGitContributions(repoDir);
  assert.strictEqual(analysis.classification, 'individual');
  assert.strictEqual(analysis.humanContributorCount, 1);
  assert.strictEqual(analysis.botContributorCount, 1);
  assert.strictEqual(analysis.mainAuthor?.name, 'Alice');
  assert.strictEqual(analysis.mainAuthor?.email, 'alice@example.com');
  assert.strictEqual(analysis.totalHumanCommits, 1);
  assert.strictEqual(analysis.totalBotCommits, 1);
});

test('collectGitContributions detects collaborative projects and honours main user hint', async (t) => {
  const repoDir = createTempRepo(t);

  function commitFile(filename, content, author) {
    fs.writeFileSync(path.join(repoDir, filename), content);
    runGit(repoDir, `add ${filename}`);
    runGit(repoDir, 'commit -m "update"', {
      env: {
        GIT_AUTHOR_NAME: author.name,
        GIT_AUTHOR_EMAIL: author.email,
        GIT_COMMITTER_NAME: author.name,
        GIT_COMMITTER_EMAIL: author.email,
      },
    });
  }

  const alice = { name: 'Alice', email: 'alice@example.com' };
  const bob = { name: 'Bob', email: 'bob@example.com' };

  commitFile('a.txt', 'Alice 1\n', alice);
  commitFile('a.txt', 'Alice 2\n', alice);
  commitFile('b.txt', 'Bob contribution\n', bob);

  const analysis = await collectGitContributions(repoDir, { mainUserEmails: [bob.email] });

  assert.strictEqual(analysis.classification, 'collaborative');
  assert.strictEqual(analysis.humanContributorCount, 2);
  assert.strictEqual(analysis.botContributorCount, 0);
  assert.strictEqual(analysis.totalHumanCommits, 3);
  assert.strictEqual(analysis.mainAuthor?.email, bob.email);
  assert.ok(analysis.mainAuthor?.share && Math.abs(analysis.mainAuthor.share - (1 / 3)) < 1e-9);
  const aliceEntry = analysis.contributors.find((c) => c.email === alice.email);
  const bobEntry = analysis.contributors.find((c) => c.email === bob.email);
  assert.ok(aliceEntry);
  assert.ok(bobEntry);
  assert.strictEqual(aliceEntry.isBot, false);
  assert.strictEqual(bobEntry.isBot, false);
});

test('buildCollaborationAnalysis captures co-authors, reviews, and export formats', async (t) => {
  const repoDir = createTempRepo(t);

  // Commit authored solely by Alice.
  fs.writeFileSync(path.join(repoDir, 'app.js'), 'console.log("v1");\n');
  runGit(repoDir, 'add app.js');
  runGit(repoDir, 'commit -m "feat: init"', {
    env: {
      GIT_AUTHOR_NAME: 'Alice',
      GIT_AUTHOR_EMAIL: 'alice@example.com',
      GIT_COMMITTER_NAME: 'Alice',
      GIT_COMMITTER_EMAIL: 'alice@example.com',
    },
  });

  // Shared commit authored by Bob but co-authored by Alice and reviewed by Carol.
  fs.writeFileSync(path.join(repoDir, 'app.js'), 'console.log("v1");\nconsole.log("feature");\n');
  runGit(repoDir, 'add app.js');
  runGit(repoDir, 'commit -m "feat: shared work" -m "Co-authored-by: Alice <alice@example.com>" -m "Reviewed-by: Carol <carol@example.com>"', {
    env: {
      GIT_AUTHOR_NAME: 'Bob',
      GIT_AUTHOR_EMAIL: 'bob@example.com',
      GIT_COMMITTER_NAME: 'Bob',
      GIT_COMMITTER_EMAIL: 'bob@example.com',
    },
  });

  // Automated dependency update to ensure bots are filtered.
  fs.writeFileSync(path.join(repoDir, 'deps.txt'), 'dependency update\n');
  runGit(repoDir, 'add deps.txt');
  runGit(repoDir, 'commit -m "chore: bump deps"', {
    env: {
      GIT_AUTHOR_NAME: 'dependabot[bot]',
      GIT_AUTHOR_EMAIL: '49699333+dependabot[bot]@users.noreply.github.com',
      GIT_COMMITTER_NAME: 'dependabot[bot]',
      GIT_COMMITTER_EMAIL: '49699333+dependabot[bot]@users.noreply.github.com',
    },
  });

  const analysis = await buildCollaborationAnalysis(repoDir, {
    mainUserEmails: ['alice@example.com'],
  });

  assert.strictEqual(analysis.totals.totalCommits, 3);
  assert.strictEqual(analysis.totals.totalBotCommits, 1);
  assert.ok(analysis.totals.totalLinesChanged > 0);

  const alice = analysis.contributorsDetailed.find((c) => c.email === 'alice@example.com');
  const bob = analysis.contributorsDetailed.find((c) => c.email === 'bob@example.com');
  const carol = analysis.contributorsDetailed.find((c) => c.email === 'carol@example.com');

  assert.ok(alice, 'Alice should appear in contributors');
  assert.ok(bob, 'Bob should appear in contributors');
  assert.ok(carol, 'Carol should be captured as reviewer');

  assert.ok(alice.metrics.commitParticipation > 0);
  assert.ok(alice.metrics.linesAdded > 0);
  assert.strictEqual(alice.isBot, false);
  assert.ok(bob.metrics.commitsAuthored >= 1);
  assert.strictEqual(bob.isBot, false);
  assert.strictEqual(carol.metrics.commitParticipation, 0);
  assert.strictEqual(carol.metrics.reviewCount, 1);

  assert.strictEqual(analysis.mainAuthor?.email, 'alice@example.com');

  const csv = formatAnalysisAsCSV(analysis, { includeBots: false });
  assert.ok(csv.includes('Alice'));
  assert.ok(!csv.includes('dependabot'));

  const jsonText = formatAnalysisAsJSON(analysis);
  const parsed = JSON.parse(jsonText);
  assert.strictEqual(parsed.contributors.length, analysis.contributorsDetailed.length);
  assert.strictEqual(parsed.mainAuthor.email, 'alice@example.com');
});

// Shared accounts and custom weighting should still produce sane scores.
test('buildCollaborationAnalysis normalizes custom weights and flags shared accounts', async (t) => {
  const repoDir = createTempRepo(t);

  // First commit authored by lead developer with sizeable diff and review trailer.
  fs.writeFileSync(path.join(repoDir, 'index.js'), 'console.log("alpha");\n');
  runGit(repoDir, 'add index.js');
  runGit(repoDir, 'commit -m "feat: initial" -m "Reviewed-by: Reviewer <reviewer@example.com>"', {
    env: {
      GIT_AUTHOR_NAME: 'Lead Dev',
      GIT_AUTHOR_EMAIL: 'lead@example.com',
      GIT_COMMITTER_NAME: 'Lead Dev',
      GIT_COMMITTER_EMAIL: 'lead@example.com',
    },
  });

  // Two commits under the same email but different author names to simulate a shared account.
  fs.writeFileSync(path.join(repoDir, 'shared.txt'), 'one\n');
  runGit(repoDir, 'add shared.txt');
  runGit(repoDir, 'commit -m "chore: shared update"', {
    env: {
      GIT_AUTHOR_NAME: 'Shared Account',
      GIT_AUTHOR_EMAIL: 'shared@example.com',
      GIT_COMMITTER_NAME: 'Shared Account',
      GIT_COMMITTER_EMAIL: 'shared@example.com',
    },
  });

  fs.writeFileSync(path.join(repoDir, 'shared.txt'), 'one\ntwo\n');
  runGit(repoDir, 'add shared.txt');
  runGit(repoDir, 'commit -m "chore: shared alias"', {
    env: {
      GIT_AUTHOR_NAME: 'Shared Alias',
      GIT_AUTHOR_EMAIL: 'shared@example.com',
      GIT_COMMITTER_NAME: 'Shared Alias',
      GIT_COMMITTER_EMAIL: 'shared@example.com',
    },
  });

  const analysis = await buildCollaborationAnalysis(repoDir, {
    weights: { commits: 2, linesChanged: 1, reviews: 1 },
  });

  assert.strictEqual(analysis.totals.totalCommits, 3);
  assert.ok(analysis.totals.totalLinesChanged > 0);
  assert.ok(analysis.totals.totalReviews >= 1);

  const weights = analysis.weights;
  assert.ok(Math.abs((weights.commits + weights.linesChanged + weights.reviews) - 1) < 1e-9);
  assert.ok(weights.commits > weights.linesChanged);

  const sharedContributor = analysis.contributorsDetailed.find((c) => c.email === 'shared@example.com');
  assert.ok(sharedContributor, 'shared contributor should be present');
  assert.strictEqual(sharedContributor.flags.isSharedAccount, true);
  assert.ok(sharedContributor.aliases.names.length >= 2);

  const humanScoreSum = analysis.contributorsDetailed
    .filter((c) => !c.isBot)
    .reduce((sum, c) => sum + c.scores.normalized, 0);
  assert.ok(Math.abs(humanScoreSum - 1) < 1e-6, 'human normalized scores should sum to ~1');

  assert.ok(analysis.sharedAccounts.length >= 1);
  const sharedEntry = analysis.sharedAccounts.find((entry) => entry.email === 'shared@example.com' || entry.name?.includes('Shared'));
  assert.ok(sharedEntry, 'shared account summary should include the shared contributor');
});

// Empty repositories should not raise errors or misreport metrics.
test('buildCollaborationAnalysis handles empty repositories without crashing', async (t) => {
  const repoDir = createTempRepo(t);

  const analysis = await buildCollaborationAnalysis(repoDir);

  assert.strictEqual(analysis.classification, 'unclassified');
  assert.strictEqual(analysis.totals.totalCommits, 0);
  assert.strictEqual(analysis.humanContributorCount, 0);
  assert.strictEqual(analysis.botContributorCount, 0);
  assert.strictEqual(analysis.mainAuthor, null);
  assert.strictEqual(analysis.timeframe.firstCommitAt, null);
  assert.strictEqual(analysis.timeframe.lastCommitAt, null);
  assert.strictEqual(analysis.timeframe.durationDays, null);
});

// CSV export toggles should control whether bots appear in the output.
test('formatAnalysisAsCSV can include bot contributors when requested', async (t) => {
  const repoDir = createTempRepo(t);

  fs.writeFileSync(path.join(repoDir, 'human.txt'), 'hi\n');
  runGit(repoDir, 'add human.txt');
  runGit(repoDir, 'commit -m "feat: human"', {
    env: {
      GIT_AUTHOR_NAME: 'Human',
      GIT_AUTHOR_EMAIL: 'human@example.com',
      GIT_COMMITTER_NAME: 'Human',
      GIT_COMMITTER_EMAIL: 'human@example.com',
    },
  });

  fs.writeFileSync(path.join(repoDir, 'bot.txt'), 'auto\n');
  runGit(repoDir, 'add bot.txt');
  runGit(repoDir, 'commit -m "deps: update"', {
    env: {
      GIT_AUTHOR_NAME: 'renovate[bot]',
      GIT_AUTHOR_EMAIL: 'bot@example.com',
      GIT_COMMITTER_NAME: 'renovate[bot]',
      GIT_COMMITTER_EMAIL: 'bot@example.com',
    },
  });

  const analysis = await buildCollaborationAnalysis(repoDir);
  const csvWithBots = formatAnalysisAsCSV(analysis, { includeBots: true });
  const csvWithoutBots = formatAnalysisAsCSV(analysis, { includeBots: false });

  assert.ok(csvWithBots.includes('renovate[bot]'));
  assert.ok(!csvWithoutBots.includes('renovate[bot]'));
  assert.ok(csvWithBots.startsWith('Name,Email,Type,'));
});
