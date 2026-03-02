// mostUsedSkills.js

const API_BASE = "http://127.0.0.1:8002";

async function fetchAllSkills() {
  try {
    const response = await fetch(`${API_BASE}/skills`);
    if (!response.ok) {
      throw new Error("Failed to fetch skills");
    }

    const data = await response.json();
    return data;
  } catch (err) {
    console.error("Error fetching skills:", err);
    return null;
  }
}

function computeTopSkills(skillData) {
  if (!skillData || !skillData.skills || skillData.skills.length === 0) {
    return [];
  }

  // Sort descending by confidence or weight if present
  return [...skillData.skills]
    .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
    .slice(0, 5); // top 5
}

async function loadMostUsedSkills() {
  const baseURL = "http://127.0.0.1:8002";

  const projectsRes = await fetch(`${baseURL}/projects`);
  const projectsData = await projectsRes.json();

  if (!projectsData.projects || projectsData.projects.length === 0) {
    return { empty: true };
  }

  const skillProjectMap = {};
  const globalSkillTotals = {};

  for (const project of projectsData.projects) {
    const projectId = project.project_id || project.id || project.name;

    const skillsRes = await fetch(
      `${baseURL}/projects/${projectId}/skills`
    );

    if (!skillsRes.ok) continue;

    const skillsData = await skillsRes.json();

    for (const skill of skillsData.skills || []) {
    const skillName = skill.name;

    // Extract number from "1 file(s) detected"
    let weight = 0;

    if (skill.files !== undefined) {
    weight = skill.files;
    } else if (skill.evidence) {
    const match = skill.evidence.match(/\d+/);
    weight = match ? parseInt(match[0], 10) : 0;
    }

  if (!globalSkillTotals[skillName]) {
    globalSkillTotals[skillName] = 0;
  }

  globalSkillTotals[skillName] += weight;

  if (!skillProjectMap[skillName]) {
    skillProjectMap[skillName] = {
      topProject: projectId,
      maxConfidence: weight
    };
  } else {
    if (weight > skillProjectMap[skillName].maxConfidence) {
      skillProjectMap[skillName] = {
        topProject: projectId,
        maxConfidence: weight
      };
    }
  }
}
  }

const totalWeight = Object.values(globalSkillTotals)
  .reduce((a, b) => a + b, 0);

const skills = Object.keys(globalSkillTotals)
  .map(skill => ({
    skill,
    confidence: totalWeight > 0 
      ? globalSkillTotals[skill] / totalWeight 
      : 0,
    topProject: skillProjectMap[skill]?.topProject || "-"
  }))
  .sort((a, b) => b.confidence - a.confidence)
  .slice(0, 5);

  if (skills.length === 0) {
    return { empty: true };
  }

  return {
    empty: false,
    skills
  };
}

module.exports = { loadMostUsedSkills };