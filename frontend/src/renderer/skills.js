import { isPrivateMode } from "./auth.js";

export async function loadMostUsedSkills() {

  const container = document.getElementById("most-used-skills");
  if (!container) return;

  console.log("Loading most used skills...");
  let result = await window.skillsAPI.loadMostUsedSkills();

  if (isPrivateMode() && (!result || result.empty)) {
    result = await buildPrivateTimelineSkills();
  }

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

bars.forEach(bar => {
  bar.style.width = "0%";
});

void document.body.offsetHeight;

bars.forEach(bar => {
  const targetWidth = bar.dataset.width;
  bar.style.width = targetWidth;
});

}

async function buildPrivateTimelineSkills() {
  try {
    const res = await fetch("http://127.0.0.1:8002/skills/timeline");
    if (!res.ok) {
      return { empty: true };
    }

    const payload = await res.json();
    const timeline = Array.isArray(payload.timeline) ? payload.timeline : [];
    if (!timeline.length) {
      return { empty: true };
    }

    const totals = new Map();
    const topProjects = new Map();

    timeline.forEach((entry) => {
      const projectId = entry?.project_id || "-";
      const skills = Array.isArray(entry?.skills) ? entry.skills : [];

      skills.forEach((skill) => {
        const name = String(skill?.skill || skill?.name || "").trim().toLowerCase();
        if (!name) return;

        const weight = Number(skill?.weight ?? skill?.score ?? 1) || 1;
        totals.set(name, (totals.get(name) || 0) + weight);

        const currentTop = topProjects.get(name);
        if (!currentTop || weight > currentTop.weight) {
          topProjects.set(name, { projectId, weight });
        }
      });
    });

    if (!totals.size) {
      return { empty: true };
    }

    const totalWeight = [...totals.values()].reduce((sum, value) => sum + value, 0) || 1;
    const skills = [...totals.entries()]
      .map(([skill, weight]) => ({
        skill,
        confidence: weight / totalWeight,
        topProject: topProjects.get(skill)?.projectId || "-",
      }))
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 5);

    return skills.length ? { empty: false, skills } : { empty: true };
  } catch (err) {
    console.error("Failed to build private timeline skills:", err);
    return { empty: true };
  }
}
