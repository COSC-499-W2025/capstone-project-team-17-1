const fs = require('fs');
const path = require('path');

const DEFAULT_LOG_PATH = path.join(__dirname, '..', '..', 'log', 'validation-errors.log');

// Ensure the directory for the log file exists so append operations succeed.
function ensureLogDirectory(logPath) {
  const directory = path.dirname(logPath);
  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory, { recursive: true });
  }
}

// Append a timestamped entry describing the validation failure.
function appendErrorLog(detail, logPath = DEFAULT_LOG_PATH) {
  try {
    ensureLogDirectory(logPath);
    const entry = `[${new Date().toISOString()}] ${detail}\n`;
    fs.appendFileSync(logPath, entry, { encoding: 'utf8' });
  } catch (logError) {
    console.error('Failed to write validation error log:', logError);
  }
}

// Validate that the input points to an existing .zip archive and return
// a standardized error payload when validation fails.
function validateZipInput(filePath, { logPath = DEFAULT_LOG_PATH } = {}) {
  if (typeof filePath !== 'string' || filePath.trim().length === 0) {
    const detail = 'Expected a file path string but received an empty value.';
    appendErrorLog(detail, logPath);
    return { error: 'InvalidInput', detail };
  }

  const resolvedPath = path.resolve(filePath);
  const extension = path.extname(resolvedPath).toLowerCase();

  if (extension !== '.zip') {
    const detail = `Expected a .zip archive but received ${extension || 'a file with no extension'} (${resolvedPath}).`;
    appendErrorLog(detail, logPath);
    return { error: 'InvalidInput', detail };
  }

  if (!fs.existsSync(resolvedPath)) {
    const detail = `Input file does not exist: ${resolvedPath}.`;
    appendErrorLog(detail, logPath);
    return { error: 'InvalidInput', detail };
  }

  return null;
}

module.exports = {
  validateZipInput,
  appendErrorLog,
  DEFAULT_LOG_PATH
};
