// test/configStore.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const fsp = require('fs').promises;
const os = require('os');
const path = require('path');

const { ConfigStore } = require('../src/lib/configStore');

function makeTempDir(prefix = 'cfg-') {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  const cleanup = () => fs.rmSync(dir, { recursive: true, force: true });
  return { dir, cleanup };
}

test('returns defaults on first load and writes atomically on save', async () => {
  const { dir, cleanup } = makeTempDir();
  try {
    const store = new ConfigStore({
      dir,
      defaults: { theme: 'dark', recentFiles: [] },
    });

    const first = await store.load();
    assert.deepStrictEqual(first, { theme: 'dark', recentFiles: [] });

    await store.set('theme', 'light');
    const saved = JSON.parse(await fsp.readFile(store.path(), 'utf8'));
    assert.strictEqual(saved.theme, 'light');
    assert.ok(fs.existsSync(store.path()));
    // .tmp file should not remain
    assert.ok(!fs.existsSync(`${store.path()}.tmp`));
  } finally {
    cleanup();
  }
});

test('get() fallback and set()/merge() behavior', async () => {
  const { dir, cleanup } = makeTempDir();
  try {
    const store = new ConfigStore({ dir, defaults: { a: 1 } });
    assert.strictEqual(await store.get('missing', 'x'), 'x');

    await store.set('a', 10);
    assert.strictEqual(await store.get('a'), 10);

    await store.merge({ b: 2, c: 3 });
    const cfg = await store.load();
    assert.deepStrictEqual(cfg, { a: 10, b: 2, c: 3 });
  } finally {
    cleanup();
  }
});

test('reset() restores defaults', async () => {
  const { dir, cleanup } = makeTempDir();
  try {
    const store = new ConfigStore({ dir, defaults: { lang: 'en' } });
    await store.set('lang', 'fr');
    await store.reset();
    const cfg = await store.load();
    assert.deepStrictEqual(cfg, { lang: 'en' });
  } finally {
    cleanup();
  }
});

test('validate() rejects bad shapes', async () => {
  const { dir, cleanup } = makeTempDir();
  try {
    const store = new ConfigStore({
      dir,
      defaults: { allowTelemetry: false },
      validate(obj) {
        // Only allow known keys and boolean for allowTelemetry
        const allowed = new Set(['allowTelemetry', 'theme']);
        for (const k of Object.keys(obj)) {
          if (!allowed.has(k)) throw new Error(`Unknown key: ${k}`);
        }
        if (typeof obj.allowTelemetry !== 'boolean') {
          throw new Error('allowTelemetry must be a boolean');
        }
      },
    });

    await store.save({ allowTelemetry: true }); // ok

    await assert.rejects(
      () => store.save({ allowTelemetry: 'yes' }),
      /allowTelemetry must be a boolean/
    );

    await assert.rejects(
      () => store.merge({ notAllowed: 1 }),
      /Unknown key: notAllowed/
    );
  } finally {
    cleanup();
  }
});
