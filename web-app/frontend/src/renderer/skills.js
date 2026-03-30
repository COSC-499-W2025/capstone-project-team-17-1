import { API_BASE } from "./config.js";

export async function loadMostUsedSkills() {
  const container = document.getElementById("most-used-skills");
  if (!container) return;

  console.log("Loading most used skills...");

  try {
    const result = await buildMostUsedSkills();
    console.log("Skills result:", result);

    if (!result || result.empty) {
      container.innerHTML = `
        <div class="empty-state">
          <h3>Hmm... 🤔</h3>
          <p>Looks like there are no projects to show yet.</p>
          <p>It's a little quiet in here... maybe upload something awesome? 😌</p>
        </div>
      `;
      return;
    }

    function capitalize(str) {
      if (!str) return "";
      return str.charAt(0).toUpperCase() + str.slice(1);
    }

    container.innerHTML = `
      <h3 class="skills-title">Most Used Skills</h3>
      <div class="skills-wrapper">
        ${result.skills
          .slice(0, 5)
          .map(
            (skill) => `
              <div class="skill-row-modern">
                <div class="skill-left-modern">
                  ${capitalize(skill.skill)}
                </div>

                <div class="skill-middle-modern">
                  <div class="skill-bar-modern">
                    <div
                      class="skill-bar-fill-modern"
                      data-width="${(skill.confidence * 100).toFixed(1)}%"
                      style="width: 0%"
                    ></div>
                  </div>
                  <span class="skill-percentage-modern">
                    ${(skill.confidence * 100).toFixed(1)}%
                  </span>
                </div>

                <div class="skill-right-modern">
                  ${capitalize(skill.topProject)}
                </div>
              </div>
            `
          )
          .join("")}
      </div>
    `;

    const bars = document.querySelectorAll(".skill-bar-fill-modern");

    bars.forEach((bar) => {
      bar.style.width = "0%";
    });

    void document.body.offsetHeight;

    bars.forEach((bar) => {
      bar.style.width = bar.dataset.width;
    });
  } catch (err) {
    console.error("Failed to load most used skills:", err);
    container.innerHTML = `<p>Failed to load skills.</p>`;
  }
}

async function buildMostUsedSkills() {
  const projectsRes = await fetch(`${API_BASE}/projects`);
  if (!projectsRes.ok) {
    throw new Error(`Failed to fetch projects: ${projectsRes.status}`);
  }

  const projectsData = await projectsRes.json();

  if (!projectsData.projects || projectsData.projects.length === 0) {
    return { empty: true };
  }

  const skillProjectMap = {};
  const globalSkillTotals = {};

  for (const project of projectsData.projects) {
    const projectId = project.project_id || project.id || project.name;
    if (!projectId) continue;

    const skillsRes = await fetch(
      `${API_BASE}/projects/${encodeURIComponent(projectId)}/skills`
    );

    if (!skillsRes.ok) {
      if ([400, 404, 409].includes(skillsRes.status)) continue;
      continue;
    }

    const skillsData = await skillsRes.json();

    for (const skill of skillsData.skills || []) {
      const skillName = skill.name;
      if (!skillName) continue;

      let weight = 0;

      if (skill.files !== undefined && skill.files !== null) {
        weight = Number(skill.files) || 0;
      } else if (skill.evidence) {
        const match = String(skill.evidence).match(/\d+/);
        weight = match ? parseInt(match[0], 10) : 0;
      }

      if (!globalSkillTotals[skillName]) {
        globalSkillTotals[skillName] = 0;
      }

      globalSkillTotals[skillName] += weight;

      if (!skillProjectMap[skillName]) {
        skillProjectMap[skillName] = {
          topProject: projectId,
          maxConfidence: weight,
        };
      } else if (weight > skillProjectMap[skillName].maxConfidence) {
        skillProjectMap[skillName] = {
          topProject: projectId,
          maxConfidence: weight,
        };
      }
    }
  }

  const totalWeight =
    Object.values(globalSkillTotals).reduce((a, b) => a + b, 0) || 1;

  const skills = Object.keys(globalSkillTotals)
    .map((skill) => ({
      skill,
      confidence: globalSkillTotals[skill] / totalWeight,
      topProject: skillProjectMap[skill]?.topProject || "-",
    }))
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 5);

  if (skills.length === 0) {
    return { empty: true };
  }

  return {
    empty: false,
    skills,
  };
}
