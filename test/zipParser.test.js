const assert = require('assert');
const path = require('node:path');
const { describe, it, beforeEach, afterEach } = require('node:test');

const zipParserPath = require.resolve('../src/lib/zipParser.js');
const unzipperPath = require.resolve('unzipper');
const originalUnzipperEntry = require.cache[unzipperPath];

function makeDosDate(year, month, day) {
  return ((year - 1980) << 9) | (month << 5) | day;
}

function makeDosTime(hour, minute, second) {
  return (hour << 11) | (minute << 5) | Math.floor(second / 2);
}

function restoreModules() {
  delete require.cache[zipParserPath];
  if (originalUnzipperEntry) {
    require.cache[unzipperPath] = originalUnzipperEntry;
  } else {
    delete require.cache[unzipperPath];
  }
}

function loadZipParserWithStub(stubbedUnzipper) {
  delete require.cache[zipParserPath];
  require.cache[unzipperPath] = {
    id: unzipperPath,
    filename: unzipperPath,
    loaded: true,
    exports: stubbedUnzipper,
  };
  return require(zipParserPath);
}

describe('zipParser', { concurrency: false }, () => {
  beforeEach(() => {
    restoreModules();
  });

  afterEach(() => {
    restoreModules();
  });

  it('iterZipEntries normalizes paths and reports entry types', async () => {
    let requestedPath = null;
    const stub = {
      Open: {
        file: async (zipPath) => {
          requestedPath = zipPath;
          return {
            files: [
              { path: '\\root\\folder\\\\file.md', type: 'File' },
              { path: '//nested//subdir\\', type: 'Directory' },
            ],
          };
        },
      },
    };
    const { iterZipEntries } = loadZipParserWithStub(stub);
    const seen = [];
    for await (const entry of iterZipEntries('sample.zip')) {
      seen.push(entry);
    }
    assert.strictEqual(requestedPath, 'sample.zip');
    assert.strictEqual(seen.length, 2);
    assert.deepStrictEqual(seen.map((item) => item.type), ['file', 'directory']);
    assert.deepStrictEqual(seen.map((item) => item.path), ['root/folder/file.md', 'nested/subdir/']);
    assert.strictEqual(seen[0].raw.path, '\\root\\folder\\\\file.md');
    assert.strictEqual(seen[1].raw.path, '//nested//subdir\\');
  });

  it('iterZipMetadata derives size, timestamps, and format', async () => {
    const modified = new Date('2024-02-17T12:34:56Z');
    const created = new Date('2024-02-01T08:00:00Z');
    const fallbackModified = new Date(Date.UTC(2021, 6, 15, 10, 20, 30));
    const fallbackCreated = new Date(Date.UTC(2020, 0, 2, 9, 10, 0));
    const stub = {
      Open: {
        file: async () => ({
          files: [
            { path: 'ignored/', type: 'Directory' },
            {
              path: 'Folder\\FILE.ONE',
              type: 'File',
              uncompressedSize: 2048,
              extra: {
                ExtendedTimestamp: {
                  mtime: modified,
                  ctime: created,
                },
              },
            },
            {
              path: '\\Second.TXT',
              type: 'File',
              vars: { uncompressedSize: 512 },
              lastModifiedDate: makeDosDate(2021, 7, 15),
              lastModifiedTime: makeDosTime(10, 20, 30),
              creationDate: makeDosDate(2020, 1, 2),
              creationTime: makeDosTime(9, 10, 0),
            },
          ],
        }),
      },
    };
    const { iterZipMetadata } = loadZipParserWithStub(stub);
    const rows = [];
    for await (const meta of iterZipMetadata('bundle.zip')) {
      rows.push(meta);
    }
    assert.strictEqual(rows.length, 2);
    assert.deepStrictEqual(rows[0], {
      zip_path: 'Folder/FILE.ONE',
      size_bytes: 2048,
      created_utc: created.toISOString(),
      last_modified_utc: modified.toISOString(),
      format: 'one',
    });
    assert.strictEqual(rows[1].zip_path, 'Second.TXT');
    assert.strictEqual(rows[1].size_bytes, 512);
    assert.strictEqual(rows[1].created_utc, fallbackCreated.toISOString());
    assert.strictEqual(rows[1].last_modified_utc, fallbackModified.toISOString());
    assert.strictEqual(rows[1].format, 'txt');
  });

  it('collectZipMetadata aggregates rows and emits summary logs', async () => {
    const firstDate = new Date('2023-06-01T05:00:00Z');
    const secondDate = new Date('2023-06-02T06:00:00Z');
    const stub = {
      Open: {
        file: async () => ({
          files: [
            {
              path: 'alpha.txt',
              type: 'File',
              uncompressedSize: 123,
              lastModifiedDateTime: firstDate,
            },
            {
              path: 'beta.json',
              type: 'File',
              uncompressedSize: 456,
              lastModifiedDateTime: secondDate,
            },
          ],
        }),
      },
    };
    const { collectZipMetadata } = loadZipParserWithStub(stub);
    const originalLog = console.log;
    const logs = [];
    console.log = (...args) => {
      logs.push(args);
    };
    try {
      const result = await collectZipMetadata('demo.zip');
      assert.strictEqual(result.count, 2);
      assert.strictEqual(result.totalBytes, 579);
      assert.ok(Number.isFinite(result.durationMs));
      assert.strictEqual(logs.length, result.count + 1);
      logs.slice(0, result.count).forEach((args, index) => {
        assert.strictEqual(args[0], '[zipParser] metadata');
        const parsed = JSON.parse(args[1]);
        assert.deepStrictEqual(parsed, result.rows[index]);
      });
      const summaryArgs = logs.at(-1);
      assert.strictEqual(summaryArgs[0], '[zipParser] summary');
      const summary = JSON.parse(summaryArgs[1]);
      assert.strictEqual(summary.zip, path.basename('demo.zip'));
      assert.strictEqual(summary.files, result.count);
      assert.strictEqual(summary.total_bytes, result.totalBytes);
      assert.ok(Number.isFinite(summary.duration_ms));
    } finally {
      console.log = originalLog;
    }
  });
});

