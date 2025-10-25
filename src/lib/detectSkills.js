// Skills we want to surface (customize freely)
const ALLOWED_SKILLS = new Set([
  'JavaScript', 'TypeScript', 'SQL/Databases', 'Electron', 'C#'
]);

// Extensions that should never count toward skills
const NOISE_EXTS = new Set([
  '.md', '.markdown', '.txt',
  '.json', '.yml', '.yaml',
  '.html', '.htm', '.css',
  '.lock', '.log',
  '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
  '__noext__'
]);

// Evidence thresholds (tune these)
const MIN_USER_LINES = 10;
const MIN_USER_SHARE = 0.02; // 2%
const MIN_PROJ_LINES = 20;
const MIN_PROJ_SHARE = 0.02; // 2%

const path = require('path');
const { synonyms, extToSkill, CONF } = require('./skillsMap');

function norm(depOrKey) {
  return (depOrKey || '').toLowerCase().replace(/\s+/g,'');
}
function mapSkill(key) {
  return synonyms[norm(key)] || null;
}
function ensure(map, key, init) { return map[key] || (map[key] = init()); }
function pushSkill(arr, skill, confidence, src) {
  const i = arr.findIndex(s => s.skill === skill);
  if (i === -1) arr.push({ skill, confidence, sources: [src] });
  else { arr[i].confidence = Math.max(arr[i].confidence, confidence); arr[i].sources.push(src); }
}

// --------- dynamic confidence helpers ----------
function combineConf(...vals) {
  let p = 0;
  for (const v of vals) {
    const x = Math.max(0, Math.min(1, v || 0));
    p = 1 - (1 - p) * (1 - x);
  }
  return p;
}
function confidenceFromShare(frac, strength = 0.6) {
  const f = Math.max(0, Math.min(1, frac || 0));
  const k = 3.2; // sensitivity
  const base = strength * (1 - Math.exp(-k * f));
  return Math.max(0.35 * strength, Math.min(0.95, base));
}

// snapshot = { manifests:[{path,deps:{..}}], files:[{path,ext,authors:{email:lines}}], contributors:[{email,score,totalLines}] }
module.exports = function detectSkills(snapshot) {
  const projectBag = [];
  const byUser = {};                // email -> [{ skill, lines, confidence, sources }]
  const presenceSet = new Set();    // project-level presence skills
  const userTotals = new Map();     // email -> total code lines (kept)
  const projectSkillLines = new Map(); // skill -> total lines across all users

  // ----- 1) Manifests → project presence (high certainty) -----
  for (const m of (snapshot.manifests || [])) {
    for (const dep of Object.keys(m.deps || {})) {
      const s = mapSkill(dep);
      if (s) {
        pushSkill(projectBag, s, CONF.manifest, `${m.path}:${dep}`);
        presenceSet.add(s);
      }
    }
  }

  // ----- 2) Files: config/tooling presence + per-user extension evidence -----
  for (const f of (snapshot.files || [])) {
    const p = f.path || '';
    const base = path.basename(p).toLowerCase();

    // project presence hints from config/tooling names
    const hints = [
      base.match(/tsconfig/) && 'TypeScript',
      base.match(/jest|vitest/) && 'Testing',
      base.match(/dockerfile|docker-compose/) && 'Docker',
      base.match(/vite\.config|webpack\.config/) && 'Tooling/Build',
      base.match(/eslint|prettier/) && 'Tooling/Build',
      base.match(/prisma/) && 'SQL/Databases',
      base.match(/main\.js|electron/) && 'Electron',
      base.match(/\.unity/) && 'Unity',
    ].filter(Boolean);

    for (const h of hints) {
      if (ALLOWED_SKILLS.has(h)) {               // only allowed skills
        pushSkill(projectBag, h, CONF.config, p);
        presenceSet.add(h);
      }
    }

    // per-user evidence from extension
    const ext = (f.ext || '').toLowerCase();
    if (NOISE_EXTS.has(ext)) continue;           // ignore noisy exts entirely

    const skill = extToSkill[ext];
    if (!skill || !ALLOWED_SKILLS.has(skill)) continue;

    // keep (weak) project presence so the header chips can show skill set
    pushSkill(projectBag, skill, CONF.file, p);

    // attribute lines to authors & accumulate totals
    let bucketTotal = 0;
    for (const [email, linesRaw] of Object.entries(f.authors || {})) {
      if (!email || email === '__project__') continue; // per-user only
      const lines = Math.max(0, linesRaw || 0);
      if (!lines) continue;

      const bag = ensure(byUser, email, () => []);
      const i = bag.findIndex(r => r.skill === skill);
      if (i === -1) bag.push({ skill, lines, confidence: 0, sources: [p] });
      else { bag[i].lines += lines; bag[i].sources.push(p); }

      userTotals.set(email, (userTotals.get(email) || 0) + lines);
      bucketTotal += lines;
    }
    projectSkillLines.set(skill, (projectSkillLines.get(skill) || 0) + bucketTotal);
  }

  // ----- 3) Dynamic confidence + per-user filtering -----
  for (const [email, list] of Object.entries(byUser)) {
    const total = userTotals.get(email) || list.reduce((a, r) => a + (r.lines || 0), 0) || 1;

    // apply thresholds (allowed skill + min lines + min share)
    const filtered = (list || []).filter(r =>
      ALLOWED_SKILLS.has(r.skill) &&
      (r.lines || 0) >= MIN_USER_LINES &&
      ((r.lines || 0) / total) >= MIN_USER_SHARE
    );

    for (const r of filtered) {
      const share = (r.lines || 0) / total;
      const extConf = confidenceFromShare(share, 0.6);
      const presenceBoost = presenceSet.has(r.skill) ? 0.0 : 0.0; // set to 0.25 if you want a small boost
      r.confidence = combineConf(extConf, presenceBoost);
      // dedupe sources
      r.sources = [...new Set(r.sources)].slice(0, 5);
    }

    byUser[email] = filtered.sort((a, b) =>
      (b.lines || 0) - (a.lines || 0) || b.confidence - a.confidence
    );
  }

  // ----- 4) Project-level filtering (min lines + min share + allowed) -----
  const projTotal = Array.from(projectSkillLines.values()).reduce((a, b) => a + b, 0) || 1;

  const projectSkills = projectBag
    .filter(s =>
      ALLOWED_SKILLS.has(s.skill) &&
      (projectSkillLines.get(s.skill) || 0) >= MIN_PROJ_LINES &&
      ((projectSkillLines.get(s.skill) || 0) / projTotal) >= MIN_PROJ_SHARE
    )
    .map(s => ({ ...s, sources: [...new Set(s.sources)].slice(0, 5) }))
    .sort((a, b) => b.confidence - a.confidence || a.skill.localeCompare(b.skill));

  // ----- 5) Return contributor skills as built above -----
  const contributorSkills = {};
  for (const [email, list] of Object.entries(byUser)) {
    contributorSkills[email] = list;
  }

  return { projectSkills, contributorSkills };
};
