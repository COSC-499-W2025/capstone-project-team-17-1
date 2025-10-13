const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const Module = require('node:module');
test('openDb creates the database folder and reuses the same handle', { concurrency: false }, (t) => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'artifact-db-'));
  const originalCwd = process.cwd();
  process.chdir(tmpDir);
  const connectionModulePath = path.join(__dirname, '../src/db/connection.js');
  const originalModuleLoad = Module._load;
  t.after(() => {
    Module._load = originalModuleLoad;
    process.chdir(originalCwd);
    fs.rmSync(tmpDir, { recursive: true, force: true });
    delete require.cache[connectionModulePath];
  });
  delete require.cache[connectionModulePath];
  Module._load = function patchedLoad(request, parent, isMain) {
    if (request === 'better-sqlite3') {
      return class FakeDatabase {
        constructor(filename, options) {
          this.filename = filename;
          this.options = options;
          this.closed = false;
        }
        pragma() {}
        prepare() {
          return {
            get: () => ({ value: 1 }),
            all: () => [],
            run: () => ({}),
          };
        }
        close() { this.closed = true; }
      };
    }
    return originalModuleLoad(request, parent, isMain);
  };
  const connection = require(connectionModulePath);
  t.after(() => connection.closeDb());
  // Normalize to the real path because macOS resolves /var -> /private/var.
  const resolvedTmpDir = fs.realpathSync(tmpDir);
  const expectedDir = path.join(resolvedTmpDir, 'src', 'db');
  const expectedDbPath = path.join(expectedDir, 'app.db');
  assert.strictEqual(connection.getDbPath(), expectedDbPath);
  assert.ok(fs.existsSync(expectedDir), 'database directory should be created');
  const firstDb = connection.openDb();
  const secondDb = connection.openDb();
  assert.strictEqual(firstDb, secondDb, 'openDb should reuse the same database handle');
  const row = firstDb.prepare('SELECT 1 AS value').get();
  assert.deepStrictEqual(row, { value: 1 });
  connection.closeDb();
  assert.doesNotThrow(() => connection.closeDb(), 'closing twice should be safe');
});
