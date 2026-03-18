import test from "node:test";
import assert from "node:assert/strict";

function getTimelineSkillName(skill) {
  return String(skill?.name || skill?.skill || "").trim();
}

function getTimelineSkillWeight(skill) {
  const rawWeight = Number(skill?.weight ?? skill?.score ?? skill?.confidence ?? 0);
  if (!Number.isFinite(rawWeight)) return 0;
  return Math.max(0, rawWeight);
}

function getSkillExpertiseLevel(depthScore) {
  if (depthScore >= 2.5) return "Advanced";
  if (depthScore >= 1.0) return "Intermediate";
  return "Foundation";
}

function buildSkillExpertiseGroups(timeline, summaryData) {
  const depthBySkill = new Map();

  for (const entry of timeline) {
    const skills = Array.isArray(entry?.skills) ? entry.skills : [];
    const seenInSnapshot = new Set();

    for (const skill of skills) {
      const name = getTimelineSkillName(skill);
      if (!name) continue;
      const key = name.toLowerCase();
      const current = depthBySkill.get(key) || { name, totalWeight: 0, appearances: 0 };
      current.totalWeight += getTimelineSkillWeight(skill);
      if (!seenInSnapshot.has(key)) {
        current.appearances += 1;
        seenInSnapshot.add(key);
      }
      depthBySkill.set(key, current);
    }
  }

  if (!depthBySkill.size) {
    for (const name of summaryData?.skills || []) {
      depthBySkill.set(String(name).toLowerCase(), {
        name: String(name),
        totalWeight: 0.9,
        appearances: 1,
      });
    }
  }

  const groups = { Advanced: [], Intermediate: [], Foundation: [] };

  [...depthBySkill.values()]
    .map((skill) => {
      const depthScore = skill.totalWeight + skill.appearances * 0.35;
      return { ...skill, depthScore, level: getSkillExpertiseLevel(depthScore) };
    })
    .sort((a, b) => b.depthScore - a.depthScore)
    .forEach((skill) => {
      groups[skill.level].push(skill.name);
    });

  return groups;
}

test("buildSkillExpertiseGroups categorizes skills by inferred expertise level", () => {
  const groups = buildSkillExpertiseGroups(
    [
      {
        skills: [
          { name: "Python", weight: 1.4 },
          { name: "React", weight: 0.7 },
        ],
      },
      {
        skills: [
          { name: "Python", weight: 1.2 },
          { name: "SQL", weight: 0.4 },
        ],
      },
    ],
    null
  );

  assert.deepEqual(groups.Advanced, ["Python"]);
  assert.deepEqual(groups.Intermediate, ["React"]);
  assert.deepEqual(groups.Foundation, ["SQL"]);
});

test("buildSkillExpertiseGroups falls back to summary skills when timeline is empty", () => {
  const groups = buildSkillExpertiseGroups([], {
    skills: ["FastAPI", "Electron"],
  });

  assert.deepEqual(groups.Advanced, []);
  assert.deepEqual(groups.Intermediate, ["FastAPI", "Electron"]);
  assert.deepEqual(groups.Foundation, []);
});
