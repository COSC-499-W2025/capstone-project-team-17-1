// Works with `node --test` (npm test)
// No Jest APIs used.

const test = require('node:test');
const assert = require('node:assert/strict');
const mock = require('mock-fs');
const fs = require('fs');
const path = require('path');

// adjust path if your file lives elsewhere
const { detectTechStack, buildMarkdown } = require('../src/lib/detectTechStack');

test('detects Node/Electron project and builds markdown', async (t) => {
  // cleanup after this test
  t.after(() => mock.restore());

  // fake a tiny project
  mock({
    'package.json': JSON.stringify({
      name: 'sample-electron',
      scripts: { start: 'electron .', dev: 'vite' },
      dependencies: { electron: '^38.2.2' },
      devDependencies: { jest: '^29.7.0' } // just to see it show up as a tool/framework
    }),
    'package-lock.json': '{}'
  });

  const det = await detectTechStack(process.cwd());

  // basic assertions
  assert.ok(Array.isArray(det.languages), 'languages should be an array');
  assert.ok(det.languages.includes('JavaScript'));

  const fwNames = det.frameworks.map(f => f.name);
  assert.ok(fwNames.includes('Electron'));

  const md = buildMarkdown(det);
  assert.match(md, /## Languages/);

  // simulate write path (ensures no exceptions writing file)
  fs.writeFileSync(path.join(process.cwd(), 'TECH_STACK.md'), md);
  assert.ok(fs.existsSync('TECH_STACK.md'));
});
