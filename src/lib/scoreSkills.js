// scoreSkills.js
module.exports = function scoreSkills({ contributors, contributorSkills, presence }) {
  const outPerUser = {};
  const projectImpact = {};

  const sumLinesAll = (contributors || []).reduce((a, u) => a + (u.totalLines || 0), 0);

  // Determine if we have any evidence for any user
  const hasAnyEvidence = Object.values(contributorSkills || {})
    .some(arr => Array.isArray(arr) && arr.length > 0);

  for (const u of (contributors || [])) {
    const existing = (contributorSkills && contributorSkills[u.email]) || [];
    const totalFromAttr = existing.reduce((a, r) => a + (r.lines || 0), 0);

    let list = existing.map(r => ({
      skill: r.skill,
      confidence: r.confidence,
      lines: r.lines || 0,
      impact: (u.score || 0) * (totalFromAttr ? (r.lines || 0) / totalFromAttr : 0),
      sources: r.sources || []
    }));

    // Fallback only if *nobody* has evidence
    const needFallback = !hasAnyEvidence && !list.length && Array.isArray(presence) && presence.length;
    if (needFallback) {
      const share = sumLinesAll ? (u.totalLines || 0) / sumLinesAll
                                : (contributors.length ? 1 / contributors.length : 0);
      list = presence.map(p => ({
        skill: p.skill,
        confidence: p.confidence ?? 0.6,
        lines: 0,
        impact: (u.score || 0) * share,
        sources: p.sources || []
      }));
    }

    // (optional) hide tiny noise
    const userTotal = list.reduce((a, r) => a + (r.lines || 0), 0) || 1;
    list = list.filter(r => (r.lines || 0) / userTotal >= 0.01); // 1% threshold

    outPerUser[u.email] = list.sort((a, b) => b.impact - a.impact || b.confidence - a.confidence);

    for (const r of outPerUser[u.email]) {
      projectImpact[r.skill] = (projectImpact[r.skill] || 0) + (r.impact || 0);
    }
  }

  const maxImp = Math.max(0, ...Object.values(projectImpact));
  const projectSkills = Object.entries(projectImpact)
    .map(([skill, imp]) => ({ skill, impact: maxImp ? imp / maxImp : 0 }))
    .sort((a, b) => b.impact - a.impact);

  return { projectSkills, contributorSkills: outPerUser };
};
