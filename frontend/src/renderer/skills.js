export async function loadMostUsedSkills() {

  const container = document.getElementById("most-used-skills");
  if (!container) return;

  console.log("Loading most used skills...");
  const result = await window.skillsAPI.loadMostUsedSkills();
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