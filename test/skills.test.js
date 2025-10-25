// test/skills.test.js
const test = require('node:test');
const assert = require('node:assert/strict');

// Adjust this path if your repo differs
const detectSkills = require('../src/lib/detectSkills');

function skillOf(list, name) {
  return (list || []).find(s => s.skill === name);
}

test('computes dynamic confidence and includes JS + SQL with correct ordering', () => {
  // Snapshot with enough lines to pass default thresholds in detectSkills
  const snapshot = {
    manifests: [
      { path: 'package.json', deps: { electron: '^28.0.0' } }, // project presence
    ],
    files: [
      // JS bucket: strong signal
      { path: 'src/app.js',        ext: '.js',  authors: {
        'alice@example.com': 900, 'bob@example.com': 300 } },
      { path: 'src/main.js',       ext: '.js',  authors: {
        'alice@example.com': 300 } },

      // SQL bucket: weaker but still over thresholds
      { path: 'db/schema.sql',     ext: '.sql', authors: {
        'alice@example.com': 100, 'bob@example.com': 100 } },

      // Noise: should be ignored completely
      { path: 'README.md',         ext: '.md',  authors: { 'alice@example.com': 200 } },
    ],
    contributors: [] // not needed by detector
  };

  const { contributorSkills, projectSkills } = detectSkills(snapshot);

  // Project should keep JS + SQL in chips
  const projNames = new Set(projectSkills.map(s => s.skill));
  assert.ok(projNames.has('JavaScript'));
  assert.ok(projNames.has('SQL/Databases'));

  const alice = contributorSkills['alice@example.com'] || [];
  const jsA   = skillOf(alice, 'JavaScript');
  const sqlA  = skillOf(alice, 'SQL/Databases');

  assert.ok(jsA, 'Alice should have JavaScript');
  assert.ok(sqlA, 'Alice should have SQL/Databases');

  // Confidence is dynamic, but JS should be higher than SQL for Alice
  assert.ok(jsA.confidence > sqlA.confidence,
    `Expected JS confidence (${jsA.confidence}) > SQL confidence (${sqlA.confidence})`);

  // Numbers are in 0..1
  assert.ok(jsA.confidence > 0 && jsA.confidence <= 1);
  assert.ok(sqlA.confidence > 0 && sqlA.confidence <= 1);
});

test('filters noise and drops under-threshold user-skill rows', () => {
  const snapshot = {
    manifests: [],
    files: [
      { path: 'src/a.js',      ext: '.js',  authors: { 'bob@example.com': 300 } },
      { path: 'src/b.js',      ext: '.js',  authors: { 'bob@example.com': 200 } },
      // Tiny TypeScript signal: should be filtered by MIN_USER_LINES / MIN_USER_SHARE
      { path: 'src/tiny.ts',   ext: '.ts',  authors: { 'bob@example.com': 5 } },
      // Noise should be ignored entirely
      { path: 'README.md',     ext: '.md',  authors: { 'bob@example.com': 500 } },
    ],
    contributors: []
  };

  const { contributorSkills } = detectSkills(snapshot);
  const bob = contributorSkills['bob@example.com'] || [];

  // JS remains
  assert.ok(skillOf(bob, 'JavaScript'), 'Bob should have JavaScript');
  // TypeScript was tiny → below thresholds → dropped
  assert.equal(skillOf(bob, 'TypeScript'), undefined, 'Tiny TS should be filtered out');
});
