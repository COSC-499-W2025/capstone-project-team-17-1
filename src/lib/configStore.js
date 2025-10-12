// src/lib/configStore.js
const fs = require('fs');
const fsp = require('fs').promises;
const path = require('path');

/**
 * Minimal JSON config store with:
 * - async read/write (atomic writes)
 * - defaults on first run
 * - key-level get/set and whole-object merge
 * - pluggable validate() for basic schema checks
 */
class ConfigStore {
  /**
   * @param {Object} options
   * @param {string} options.dir          Directory to keep the config file in.
   * @param {string} [options.filename]   Defaults to 'user-config.json'.
   * @param {Object} [options.defaults]   Default config object.
   * @param {(obj:Object)=>void} [options.validate] Optional validation fn (throw on error).
   */
  constructor({ dir, filename = 'user-config.json', defaults = {}, validate } = {}) {
    if (!dir || typeof dir !== 'string') throw new Error('ConfigStore: dir is required');
    this.filePath = path.join(dir, filename);
    this.defaults = { ...defaults };
    this.validate = typeof validate === 'function' ? validate : null;
  }

  async _ensureDir() {
    await fsp.mkdir(path.dirname(this.filePath), { recursive: true });
  }

  async _atomicWrite(jsonStr) {
    const tmp = `${this.filePath}.tmp`;
    await fsp.writeFile(tmp, jsonStr, 'utf8');
    await fsp.rename(tmp, this.filePath);
  }

  async load() {
    try {
      const raw = await fsp.readFile(this.filePath, 'utf8');
      const obj = JSON.parse(raw);
      if (this.validate) this.validate(obj);
      return obj;
    } catch (err) {
      // If file does not exist or is unreadable, fall back to defaults
      return { ...this.defaults };
    }
  }

  async save(obj) {
    if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
      throw new Error('ConfigStore.save: config must be a plain object');
    }
    if (this.validate) this.validate(obj);
    await this._ensureDir();
    await this._atomicWrite(JSON.stringify(obj, null, 2));
    return obj;
  }

  async get(key, fallback = undefined) {
    const cfg = await this.load();
    return Object.prototype.hasOwnProperty.call(cfg, key) ? cfg[key] : fallback;
  }

  async set(key, value) {
    const cfg = await this.load();
    const next = { ...cfg, [key]: value };
    return this.save(next);
  }

  async merge(patch) {
    if (typeof patch !== 'object' || patch === null || Array.isArray(patch)) {
      throw new Error('ConfigStore.merge: patch must be a plain object');
    }
    const cfg = await this.load();
    const next = { ...cfg, ...patch };
    return this.save(next);
  }

  async reset() {
    return this.save({ ...this.defaults });
  }

  path() {
    return this.filePath;
  }
}

module.exports = { ConfigStore };
