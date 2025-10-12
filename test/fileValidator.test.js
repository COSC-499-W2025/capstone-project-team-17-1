const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { validateZipInput } = require('../src/lib/fileValidator');

// Build an isolated log directory for each test to avoid cross-test pollution.
function createTempLogPath() {
  const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), 'validator-log-'));
  const logPath = path.join(baseDir, 'log', 'validation-errors.log');
  const cleanup = () => fs.rmSync(baseDir, { recursive: true, force: true });
  return { logPath, baseDir, cleanup };
}

// Empty inputs should trigger the InvalidInput schema and produce a log entry.
test('rejects empty file path values', () => {
  const { logPath, cleanup } = createTempLogPath();
  try {
    const result = validateZipInput('', { logPath });
    assert.deepStrictEqual(result, {
      error: 'InvalidInput',
      detail: 'Expected a file path string but received an empty value.'
    });

    assert.strictEqual(fs.existsSync(logPath), true);
    const logContents = fs.readFileSync(logPath, 'utf8');
    assert.ok(
      logContents.includes('Expected a file path string but received an empty value.'),
      'log should capture the failure detail'
    );
  } finally {
    cleanup();
  }
});

// Files with a non-.zip extension are rejected with an explanatory detail.
test('rejects non-zip extensions', () => {
  const { logPath, cleanup } = createTempLogPath();
  const targetPath = path.resolve('file.pdf');

  try {
    const result = validateZipInput('file.pdf', { logPath });
    assert.deepStrictEqual(result, {
      error: 'InvalidInput',
      detail: `Expected a .zip archive but received .pdf (${targetPath}).`
    });

    const logContents = fs.readFileSync(logPath, 'utf8');
    assert.ok(logContents.includes('.pdf'), 'log should mention the invalid extension');
  } finally {
    cleanup();
  }
});

// Referencing a .zip that does not exist should return InvalidInput and log the failure.
test('rejects missing zip files', () => {
  const { logPath, cleanup, baseDir } = createTempLogPath();
  const missingPath = path.join(baseDir, 'archive.zip');

  try {
    const result = validateZipInput(missingPath, { logPath });
    assert.deepStrictEqual(result, {
      error: 'InvalidInput',
      detail: `Input file does not exist: ${missingPath}.`
    });

    const logContents = fs.readFileSync(logPath, 'utf8');
    assert.ok(logContents.includes('does not exist'), 'log should note missing input');
  } finally {
    cleanup();
  }
});

// A valid zip path should pass validation and skip log generation.
test('accepts existing zip files without logging errors', () => {
  const { logPath, cleanup, baseDir } = createTempLogPath();
  const zipPath = path.join(baseDir, 'valid.zip');
  fs.mkdirSync(path.dirname(zipPath), { recursive: true });
  fs.writeFileSync(zipPath, 'PK');

  try {
    const result = validateZipInput(zipPath, { logPath });
    assert.strictEqual(result, null);
    assert.strictEqual(fs.existsSync(logPath), false, 'no log file should be created for valid input');
  } finally {
    cleanup();
  }
});
