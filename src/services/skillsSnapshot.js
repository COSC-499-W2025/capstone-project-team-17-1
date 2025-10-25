// src/services/skillsSnapshot.js
const fs = require('fs');
const path = require('path');

function readJSONIfExists(p) {
  try {
    if (p && fs.existsSync(p)) {
      return JSON.parse(fs.readFileSync(p, 'utf8'));
    }
  } catch (_) {}
  return null;
}

function num(v) { return Number.isFinite(v) ? v : 0; }

/**
 * Build the minimal snapshot the skills detector expects:
 * {
 *   manifests: [{ path:'package.json', deps:{...} }],
 *   files:     [{ path:'bucket.ts', ext:'.ts', authors:{ email: lines } }, ...],
 *   contributors: [{ email, score, totalLines }]
 * }
 *
 * It pulls from projectRow.details (contributorsDetailed/Summary) and repoPath.
 * If per-extension data isn't in details, it does a very light FS scan to
 * infer project-level languages (authors unknown -> no per-user attribution).
 */
function buildSkillsSnapshotFromDetails(projectRow) {
  const details = projectRow?.details || {};
  const repoPath = projectRow?.repoPath || projectRow?.repo_path || null;

  // ---------------------------
  // Contributors (for impact)
  // ---------------------------
  const detailed = Array.isArray(details.contributorsDetailed) ? details.contributorsDetailed : null;
  const summary  = Array.isArray(details.contributorsSummary)  ? details.contributorsSummary  : null;

  let contributors = [];
  if (detailed) {
    contributors = detailed
      .filter(c => c && !c.isBot)
      .map(c => ({
        email: c.email || c.name || '',
        score: num(c?.scores?.normalized),
        totalLines: num(c?.metrics?.linesChanged),
      }));
  } else if (summary) {
    contributors = summary
      .filter(c => c && !c.isBot)
      .map(c => ({
        email: c.email || c.name || '',
        score: num(c?.score ?? c?.normalizedScore),
        totalLines: num(c?.linesChanged),
      }));
  }

  // ----------------------------------------------------
  // Manifests (package.json → high-confidence skills)
  // ----------------------------------------------------
  const manifests = [];
  if (repoPath) {
    const pkg = readJSONIfExists(path.join(repoPath, 'package.json'));
    if (pkg) {
      manifests.push({
        path: 'package.json',
        deps: {
          ...(pkg.dependencies || {}),
          ...(pkg.devDependencies || {}),
          ...(pkg.peerDependencies || {}),
        },
      });
    }
  }

  // ----------------------------------------------------------------
  // Files (attribute by extension & per-author lines if available)
  // ----------------------------------------------------------------
  // Prefer per-extension lines from details.contributorsDetailed[].metrics.linesByExt
  const perExt = new Map(); // ext -> { authors:{ email: lines } }

  if (detailed) {
    for (const c of detailed) {
      const email = c?.email || c?.name || '';
      const byExt = c?.metrics?.linesByExt;
      if (byExt && typeof byExt === 'object') {
        for (const [ext, lines] of Object.entries(byExt)) {
          if (!perExt.has(ext)) perExt.set(ext, { authors: {} });
          perExt.get(ext).authors[email] = (perExt.get(ext).authors[email] || 0) + num(lines);
        }
      }
    }
  }

  // If no per-extension info, do a lightweight repo scan to infer project languages
  if (perExt.size === 0 && repoPath && fs.existsSync(repoPath)) {
    // extensions we care about
    const exts = new Set(['.ts', '.tsx', '.js', '.jsx', '.sql', '.cs', '.py', '.r']);
    // walk a few levels (cheap)
    const stack = [repoPath];
    let visited = 0;
    while (stack.length) {
      const dir = stack.pop();
      let ents = [];
      try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { continue; }
      for (const e of ents) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) {
          // skip massive dirs
          if (!/node_modules|\.git|dist|build|out/i.test(p)) stack.push(p);
          continue;
        }
        const ext = path.extname(p).toLowerCase();
        if (exts.has(ext)) {
          if (!perExt.has(ext)) perExt.set(ext, { authors: {} });
          // unknown author → put in a pseudo "project" bucket to get project-level skills
          perExt.get(ext).authors['__project__'] = (perExt.get(ext).authors['__project__'] || 0) + 1;
        }
        visited++;
        if (visited > 5000) break; // safety cap
      }
      if (visited > 5000) break;
    }
  }

  const files = [];
  for (const [ext, bucket] of perExt.entries()) {
    files.push({ path: `bucket${ext}`, ext, authors: bucket.authors });
  }

  // Debug (will print in main process)
  console.log('[skillsSnapshot] repoPath:', repoPath,
              '| manifests:', manifests.length,
              '| fileBuckets:', files.length,
              '| contributors:', contributors.length);

  return { manifests, files, contributors };
}

module.exports = { buildSkillsSnapshotFromDetails };
