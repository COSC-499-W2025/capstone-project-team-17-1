const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execSync } = require('node:child_process');

const { collectGitContributions } = require('../src/lib/gitContributors');

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
