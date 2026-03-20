import { fetchProjects } from "./projects.js";
import { authFetch, getCurrentUser } from "./auth.js";
import {
  getFeaturedProjects,
  getProjectOverride,
  loadPortfolioCustomization,
} from "./portfolioCustomizationState.js";

const API_BASE = "http://127.0.0.1:8002";

const SECTION_SELECTOR_MAP = {
  "resume-summary": ".portfolio-hero-card",
  "top-projects": ".portfolio-projects-card",
  "portfolio-stats": ".portfolio-skills-card",
  "skills-timeline": ".portfolio-timeline-card",
  "activity-heatmap": ".portfolio-heatmap-card",
};

let portfolioResumeInitialized = false;

function getStaticProfile() {
  return {
    name: "Raunak Khanna",
    title: "Computer Science Student",
    education: "UBC Okanagan — BSc Computer Science",
    awards: ["Capstone Team Contributor"],
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function dedupeStrings(values) {
  return [...new Set(asArray(values).map((v) => String(v).trim()).filter(Boolean))];
}

function buildContributionSummary(project, details, override) {
  // Prefer user-authored portfolio overrides, then fall back to detected project signals.
  const overrideRole = String(override?.keyRole || "").trim();
  const overrideEvidence = String(override?.evidence || "").trim();
  const highlights = dedupeStrings(details?.highlights);
  const technologies = dedupeStrings(details?.technologies);

  if (overrideRole && overrideEvidence) {
    return `${overrideRole} • ${overrideEvidence}`;
  }

  if (overrideRole) {
    return overrideRole;
  }

  if (highlights.length) {
    return highlights[0];
  }

  if (technologies.length) {
    return `Applied ${technologies.slice(0, 3).join(", ")} across the implementation.`;
  }

  return `Contributed to ${project.total_files || 0} analyzed file${project.total_files === 1 ? "" : "s"} in this project.`;
}

function buildImpactSummary(project, details, override) {
  const overrideEvidence = String(override?.evidence || "").trim();
  const highlights = dedupeStrings(details?.highlights);
  const impactSignals = [
    `${project.total_files || 0} file${project.total_files === 1 ? "" : "s"} analyzed`,
    `${project.total_skills || 0} skill signal${project.total_skills === 1 ? "" : "s"} detected`,
  ];

  if (overrideEvidence) {
    return `${overrideEvidence} Backed by ${impactSignals.join(" and ")}.`;
  }

  if (highlights.length > 1) {
    return `${highlights[1]} Backed by ${impactSignals.join(" and ")}.`;
  }

  return `Portfolio impact is supported by ${impactSignals.join(" and ")}.`;
}

function buildProjectEvolutionSteps(project, details, override) {
  const technologies = dedupeStrings(details?.technologies);
  const highlights = dedupeStrings(details?.highlights);
  const keyRole = String(override?.keyRole || "").trim();
  const evidence = String(override?.evidence || "").trim();

  const stageOne = {
    label: "Starting Point",
    text:
      technologies.length > 0
        ? `The project started with hands-on work in ${technologies.slice(0, 2).join(" and ")}.`
        : `The project began as ${project.is_github ? "a GitHub import" : "a ZIP upload"} ready for analysis.`,
  };

  const stageTwo = {
    label: "Key Change",
    text:
      keyRole ||
      highlights[0] ||
      `The implementation expanded across ${project.total_files || 0} analyzed file${project.total_files === 1 ? "" : "s"}.`,
  };

  const stageThree = {
    label: "Current Outcome",
    text:
      evidence ||
      highlights[1] ||
      `It now shows ${project.total_skills || 0} detected skill signal${project.total_skills === 1 ? "" : "s"} and portfolio-ready evidence of progress.`,
  };

  return [stageOne, stageTwo, stageThree];
}

function getTopProjects(projects) {
  return [...projects]
    .sort((a, b) => {
      const skillDiff = (b.total_skills || 0) - (a.total_skills || 0);
      if (skillDiff !== 0) return skillDiff;
      return (b.total_files || 0) - (a.total_files || 0);
    })
    .slice(0, 3);
}

async function fetchSkillsTimeline() {
  const res = await authFetch(`/skills/timeline`);
  if (!res.ok) {
    throw new Error(`Failed to fetch skills timeline: ${res.status}`);
  }
  const payload = await res.json();
  return Array.isArray(payload.timeline) ? payload.timeline : [];
}

async function fetchPortfolioResumeSummary() {
  const res = await authFetch(`/portfolio/latest/summary`);
  if (!res.ok) {
    throw new Error(`Failed to fetch portfolio summary: ${res.status}`);
  }
  const payload = await res.json();
  return payload?.data || null;
}

async function fetchActivityHeatmap() {
  const res = await authFetch(`/portfolio/activity-heatmap`);
  if (!res.ok) {
    throw new Error(`Failed to fetch activity heatmap: ${res.status}`);
  }
  const payload = await res.json();
  return payload?.data || { cells: [], maxCount: 0, projectCount: 0 };
}

function buildProfile(summaryData) {
  const fallback = getStaticProfile();
  const currentUser = getCurrentUser();
  // Prefer the user's editable profile name
  const editableName =
    String(currentUser?.full_name || "").trim() ||
    String(currentUser?.username || "").trim();
  return {
    name: editableName || summaryData?.owner || fallback.name,
    title: fallback.title,
    education: summaryData?.education || fallback.education,
    awards: dedupeStrings(summaryData?.awards).length
      ? dedupeStrings(summaryData.awards)
      : fallback.awards,
  };
}

function getPortfolioProjects(summaryData) {
  return asArray(summaryData?.projects).map((project) => ({
    project_id: String(project.project_id || "").trim(),
    title: String(project.title || project.project_id || "").trim(),
    summary: String(project.summary || "").trim(),
    technologies: dedupeStrings(project.technologies),
    highlights: dedupeStrings(project.highlights),
  }));
}

function getProjectDetailsMap(summaryData) {
  const map = new Map();
  getPortfolioProjects(summaryData).forEach((project) => {
    if (project.project_id) {
      map.set(project.project_id, project);
    }
  });
  return map;
}

function formatPeriodLabel(period) {
  const raw = String(period || "").trim();

  if (/^\d{4}-\d{2}$/.test(raw)) {
    const [year, month] = raw.split("-");
    const monthIndex = Number(month) - 1;
    const date = new Date(Number(year), monthIndex, 1);

    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleString("en-US", { month: "short", year: "numeric" });
    }
  }

  return raw || "Unknown";
}

function formatTimelineTimestamp(timestamp) {
  const raw = String(timestamp || "").trim();
  if (!raw) return "Unknown";

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return raw;
  }

  return date.toLocaleString("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

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

  asArray(timeline).forEach((entry) => {
    const skills = Array.isArray(entry?.skills) ? entry.skills : [];
    const seenInSnapshot = new Set();

    skills.forEach((skill) => {
      const name = getTimelineSkillName(skill);
      if (!name) return;

      const key = name.toLowerCase();
      const current = depthBySkill.get(key) || { name, totalWeight: 0, appearances: 0 };
      current.totalWeight += getTimelineSkillWeight(skill);
      if (!seenInSnapshot.has(key)) {
        current.appearances += 1;
        seenInSnapshot.add(key);
      }
      depthBySkill.set(key, current);
    });
  });

  if (!depthBySkill.size) {
    dedupeStrings(summaryData?.skills).forEach((name) => {
      depthBySkill.set(name.toLowerCase(), {
        name,
        totalWeight: 0.9,
        appearances: 1,
      });
    });
  }

  const groups = {
    Advanced: [],
    Intermediate: [],
    Foundation: [],
  };

  [...depthBySkill.values()]
    .map((skill) => {
      const depthScore = skill.totalWeight + skill.appearances * 0.35;
      return {
        ...skill,
        depthScore,
        level: getSkillExpertiseLevel(depthScore),
      };
    })
    .sort((a, b) => {
      if (b.depthScore !== a.depthScore) return b.depthScore - a.depthScore;
      return a.name.localeCompare(b.name);
    })
    .forEach((skill) => {
      groups[skill.level].push(skill.name);
    });

  return groups;
}

function getHeatmapBucket(intensity) {
  if (intensity >= 0.8) return 4;
  if (intensity >= 0.6) return 3;
  if (intensity >= 0.35) return 2;
  if (intensity > 0) return 1;
  return 0;
}

function buildContributionHeatmapModel(cells) {
  const entries = [...cells]
    .map((cell) => {
      const rawDate = String(cell.period || "").trim();
      const parsed = new Date(`${rawDate}T00:00:00`);
      return {
        dateKey: rawDate,
        date: parsed,
        count: Number(cell.count || 0),
        intensity: Number(cell.intensity || 0),
      };
    })
    .filter((cell) => !Number.isNaN(cell.date.getTime()))
    .sort((a, b) => a.date - b.date);

  if (!entries.length) {
    return { monthLabels: [], weeks: [] };
  }

  const byDate = new Map(entries.map((entry) => [entry.dateKey, entry]));
  const start = new Date(entries[0].date);
  start.setDate(start.getDate() - start.getDay());
  const end = new Date(entries[entries.length - 1].date);
  end.setDate(end.getDate() + (6 - end.getDay()));

  const weeks = [];
  const monthLabels = [];
  let cursor = new Date(start);
  let weekIndex = 0;

  while (cursor <= end) {
    const weekDays = [];
    const weekStart = new Date(cursor);
    for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
      const current = new Date(cursor);
      current.setDate(cursor.getDate() + dayIndex);
      const key = current.toISOString().slice(0, 10);
      const entry = byDate.get(key);
      weekDays.push({
        key,
        label: current.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        count: entry?.count || 0,
        bucket: getHeatmapBucket(entry?.intensity || 0),
        inRange: current >= entries[0].date && current <= entries[entries.length - 1].date,
      });
    }

    const firstOfMonth = weekDays.find((day) => day.key.endsWith("-01"));
    monthLabels.push(
      firstOfMonth ? weekStart.toLocaleDateString("en-US", { month: "short" }) : ""
    );
    weeks.push({ index: weekIndex, days: weekDays });
    cursor.setDate(cursor.getDate() + 7);
    weekIndex += 1;
  }

  return { monthLabels, weeks };
}

function applyPortfolioSectionVisibility() {
  const customization = loadPortfolioCustomization();
  const sectionVisibility = {
    "resume-summary": true,
    "top-projects": true,
    "portfolio-stats": true,
    "skills-timeline": true,
    "activity-heatmap": true,
    ...(customization?.sectionVisibility || {}),
  };

  Object.entries(SECTION_SELECTOR_MAP).forEach(([sectionKey, selector]) => {
    const element = document.querySelector(selector);
    if (!element) return;

    const isVisible = sectionVisibility[sectionKey] !== false;
    element.style.display = isVisible ? "" : "none";
  });
}

function renderResumeSummary(profile, projects, summaryData) {
  const container = document.getElementById("resume-summary-container");
  if (!container) return;

  const featuredProjects = getFeaturedProjects(projects);

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);

  const backendSkills = dedupeStrings(summaryData?.skills);
  const highlights = dedupeStrings(summaryData?.highlights).slice(0, 4);

  const summary =
    totalProjects > 0
      ? `Built a portfolio with ${totalProjects} uploaded project${totalProjects === 1 ? "" : "s"}, covering ${totalFiles} analyzed file${totalFiles === 1 ? "" : "s"} and ${totalSkills} detected skill signal${totalSkills === 1 ? "" : "s"}.`
      : "Upload projects to generate a one-page resume summary and portfolio showcase.";

  container.innerHTML = `
    <div class="resume-summary-card">
      <div class="resume-summary-top">
        <div>
          <h3>${escapeHtml(profile.name)}</h3>
          <p class="resume-role">${escapeHtml(profile.title)}</p>
        </div>
      </div>

      <p class="resume-summary-text">${escapeHtml(summary)}</p>

      <div class="resume-meta-grid">
        <div class="resume-meta-box">
          <span class="resume-meta-label">Education</span>
          <span class="resume-meta-value">${escapeHtml(profile.education)}</span>
        </div>

        <div class="resume-meta-box">
          <span class="resume-meta-label">Awards</span>
          <ul class="resume-awards-list">
            ${profile.awards.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </div>

        <div class="resume-meta-box">
          <span class="resume-meta-label">Projects Uploaded</span>
          <span class="resume-meta-value">${totalProjects}</span>
        </div>

        <div class="resume-meta-box">
          <span class="resume-meta-label">Portfolio Coverage</span>
          <span class="resume-meta-value">${totalFiles} files • ${totalSkills} skill signals</span>
        </div>
      </div>

      ${
        backendSkills.length
          ? `
            <div class="resume-meta-box">
              <span class="resume-meta-label">Core Skills</span>
              <div class="skills-pill-row">
                ${backendSkills
                  .slice(0, 10)
                  .map((skill) => `<span class="skills-pill">${escapeHtml(skill)}</span>`)
                  .join("")}
              </div>
            </div>
          `
          : ""
      }

      ${
        highlights.length
          ? `
            <div class="resume-meta-box">
              <span class="resume-meta-label">Portfolio Highlights</span>
              <ul class="resume-awards-list">
                ${highlights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
              </ul>
            </div>
          `
          : ""
      }

      ${
        featuredProjects.length
          ? `
            <div class="resume-meta-box">
              <span class="resume-meta-label">Featured Projects</span>
              <div class="skills-pill-row">
                ${featuredProjects
                  .map((project) => `<span class="skills-pill">${escapeHtml(project.project_id)}</span>`)
                  .join("")}
              </div>
            </div>
          `
          : ""
      }
    </div>
  `;
}

function renderTopProjects(projects, summaryData) {
  const container = document.getElementById("top-projects-container");
  if (!container) return;

  if (!projects.length) {
    container.innerHTML = `
      <div class="empty-state">
        Upload a project to populate your top project showcase.
      </div>
    `;
    return;
  }

  const projectDetailsMap = getProjectDetailsMap(summaryData);
  const featuredProjects = getFeaturedProjects(projects);
  const topProjects = featuredProjects.length ? featuredProjects : getTopProjects(projects);

  container.innerHTML = topProjects
    .map((project, index) => {
      const details = projectDetailsMap.get(project.project_id);
      const override = getProjectOverride(project.project_id) || {};

      const title = details?.title || project.project_id;
      const summary =
        override.portfolioBlurb ||
        details?.summary ||
        `${project.total_files} file${project.total_files === 1 ? "" : "s"} analyzed • ${project.total_skills} detected skill signal${project.total_skills === 1 ? "" : "s"}`;

      const technologies = dedupeStrings(details?.technologies).slice(0, 4);
      const keyRole = override.keyRole?.trim();
      const evidence = override.evidence?.trim();
      const contributionSummary = buildContributionSummary(project, details, override);
      const impactSummary = buildImpactSummary(project, details, override);
      const evolutionSteps = buildProjectEvolutionSteps(project, details, override);

      return `
        <div class="top-project-card">
          <div class="top-project-rank">#${index + 1}</div>
          <div class="top-project-body">
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(summary)}</p>

            ${
              contributionSummary
                ? `
                  <div class="portfolio-detail-block">
                    <span class="portfolio-detail-label">Contribution</span>
                    <p>${escapeHtml(contributionSummary)}</p>
                  </div>
                `
                : ""
            }

            ${
              impactSummary
                ? `
                  <!-- Keep success evidence behind an explicit toggle in both public and private portfolio views. -->
                  <div class="project-details">
                    <button
                      class="project-details-toggle"
                      type="button"
                      data-evidence-details="${escapeHtml(project.project_id)}"
                    >
                      View Details
                    </button>
                    <div
                      class="project-details-panel hidden"
                      data-evidence-details-panel="${escapeHtml(project.project_id)}"
                    >
                      <div class="project-story-block">
                        <span class="project-story-label">Evidence of Success</span>
                        <p class="project-evolution-text">${escapeHtml(impactSummary)}</p>
                      </div>
                      <div class="project-evolution-block">
                        <span class="portfolio-detail-label">Project Evolution</span>
                        <div class="project-evolution-steps">
                          ${evolutionSteps
                            .map(
                              (step, stepIndex) => `
                                <div class="project-evolution-step">
                                  <div class="project-evolution-marker">${stepIndex + 1}</div>
                                  <div>
                                    <div class="project-evolution-title">${escapeHtml(step.label)}</div>
                                    <p class="project-evolution-text">${escapeHtml(step.text)}</p>
                                  </div>
                                </div>
                              `
                            )
                            .join("")}
                        </div>
                      </div>
                    </div>
                  </div>
                `
                : ""
            }

            <div class="project-stack">
              <span class="stack-pill">${project.is_github ? "GitHub Import" : "ZIP Upload"}</span>
              <span class="stack-pill">${project.total_files} Files</span>
              <span class="stack-pill">${project.total_skills} Skills</span>
              ${technologies.map((tech) => `<span class="stack-pill">${escapeHtml(tech)}</span>`).join("")}
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderPortfolioStats(projects, summaryData, timeline = []) {
  const container = document.getElementById("skills-expertise-container");
  if (!container) return;

  if (!projects.length) {
    container.innerHTML = `
      <div class="skills-group-card">
        <h3>No portfolio data yet</h3>
        <p class="resume-summary-text">
          Upload projects to generate skills, highlights, and portfolio statistics.
        </p>
      </div>
    `;
    return;
  }

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);
  const githubCount = projects.filter((p) => p.is_github).length;

  const backendSkills = dedupeStrings(summaryData?.skills);
  const backendHighlights = dedupeStrings(summaryData?.highlights);
  const expertiseGroups = buildSkillExpertiseGroups(timeline, summaryData);

  container.innerHTML = `
    <div class="skills-group-card">
      <h3>Portfolio Stats</h3>
      <div class="skills-pill-row">
        <span class="skills-pill">${totalProjects} Projects</span>
        <span class="skills-pill">${totalFiles} Files</span>
        <span class="skills-pill">${totalSkills} Skill Signals</span>
        <span class="skills-pill">${githubCount} GitHub Imports</span>
        <span class="skills-pill">${backendSkills.length} Core Skills</span>
        <span class="skills-pill">${backendHighlights.length} Highlights</span>
      </div>
    </div>

    ${
      expertiseGroups.Advanced.length || expertiseGroups.Intermediate.length || expertiseGroups.Foundation.length
        ? `
          <div class="skills-group-card">
            <h3>Skills by Expertise Level</h3>
            <div class="skills-expertise-levels">
              <div class="skills-expertise-group">
                <span class="skills-expertise-label">Advanced</span>
                <div class="skills-pill-row">
                  ${
                    expertiseGroups.Advanced.length
                      ? expertiseGroups.Advanced
                          .map((skill) => `<span class="skills-pill">${escapeHtml(skill)}</span>`)
                          .join("")
                      : `<span class="timeline-empty">No advanced skills yet</span>`
                  }
                </div>
              </div>
              <div class="skills-expertise-group">
                <span class="skills-expertise-label">Intermediate</span>
                <div class="skills-pill-row">
                  ${
                    expertiseGroups.Intermediate.length
                      ? expertiseGroups.Intermediate
                          .map((skill) => `<span class="skills-pill">${escapeHtml(skill)}</span>`)
                          .join("")
                      : `<span class="timeline-empty">No intermediate skills yet</span>`
                  }
                </div>
              </div>
              <div class="skills-expertise-group">
                <span class="skills-expertise-label">Foundation</span>
                <div class="skills-pill-row">
                  ${
                    expertiseGroups.Foundation.length
                      ? expertiseGroups.Foundation
                          .map((skill) => `<span class="skills-pill">${escapeHtml(skill)}</span>`)
                          .join("")
                      : `<span class="timeline-empty">No foundation skills yet</span>`
                  }
                </div>
              </div>
            </div>
          </div>
        `
        : `
          <div class="skills-group-card">
            <h3>No skills detected yet</h3>
            <p class="resume-summary-text">
              Upload projects with detected skills to categorize portfolio skills by expertise level.
            </p>
          </div>
        `
    }
  `;
}

function renderSkillsTimeline(timeline) {
  const container = document.getElementById("skills-timeline-container");
  if (!container) return;

  if (!timeline.length) {
    container.innerHTML = `
      <div class="skills-group-card">
        <h3>No timeline data yet</h3>
        <p class="resume-summary-text">
          Upload projects with detected skills to generate a year-by-year skills timeline.
        </p>
      </div>
    `;
    return;
  }

  container.innerHTML = timeline
    .map((entry) => {
      const skills = Array.isArray(entry.skills) ? entry.skills : [];
      const timeLabel = formatTimelineTimestamp(entry.timestamp || entry.year);
      const projectLabel = String(entry.project_id || "").trim();

      return `
        <div class="timeline-year-row">
          <div class="timeline-year">
            <span class="timeline-dot" aria-hidden="true"></span>
            <div class="timeline-time-block">
              <span class="timeline-time-label">${escapeHtml(timeLabel)}</span>
              ${projectLabel ? `<span class="timeline-project-label">${escapeHtml(projectLabel)}</span>` : ""}
            </div>
          </div>
          <div class="timeline-track">
            <div class="timeline-skill-pills">
              ${
                skills.length
                  ? skills
                      .map((skill) => {
                        const name = skill.name || skill.skill || "unknown";
                        const weight =
                          skill.weight !== undefined && skill.weight !== null
                            ? `<span class="timeline-weight">${Number(skill.weight).toFixed(1)}</span>`
                            : "";

                        return `
                          <span class="timeline-skill-pill">
                            ${escapeHtml(name)} ${weight}
                          </span>
                        `;
                      })
                      .join("")
                  : `<span class="timeline-empty">No skills recorded</span>`
              }
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderActivityHeatmap(heatmapData) {
  const container = document.getElementById("activity-heatmap-container");
  if (!container) return;

  const card = container.closest(".portfolio-heatmap-card");

  const cells = Array.isArray(heatmapData?.cells) ? heatmapData.cells : [];
  const projectCount = Number(heatmapData?.projectCount || 0);

  if (!cells.length) {
    container.innerHTML = `
      <div class="skills-group-card">
        <h3>No activity data yet</h3>
        <p class="resume-summary-text">
          Upload projects with timeline or file activity data to generate a project activity heatmap.
        </p>
      </div>
    `;
    return;
  }

  // If activity data exists, keep the heatmap card visible even if an older local customization hid it.
  if (card) {
    card.style.display = "";
  }

  const totalActivity = cells.reduce((sum, cell) => sum + Number(cell.count || 0), 0);
  const averageActivity = cells.length ? Math.round(totalActivity / cells.length) : 0;
  const peakCell = [...cells].sort((a, b) => Number(b.count || 0) - Number(a.count || 0))[0];
  const heatmap = buildContributionHeatmapModel(cells);
  const legendLevels = [
    { label: "Low", bucket: 0 },
    { label: "", bucket: 1 },
    { label: "", bucket: 2 },
    { label: "", bucket: 3 },
    { label: "High", bucket: 4 },
  ];

  container.innerHTML = `
    <div class="heatmap-summary">
      <div>
        <p class="resume-summary-text">
          Aggregated activity across ${projectCount} project${projectCount === 1 ? "" : "s"}.
        </p>
        <div class="heatmap-chip-row">
          <span class="hero-stat-chip">${totalActivity} total activity events</span>
          <span class="hero-stat-chip">${averageActivity} avg / active day</span>
          <span class="hero-stat-chip">Peak: ${escapeHtml(peakCell?.period || "")}</span>
        </div>
      </div>
    </div>

    <div class="heatmap-legend">
      <span class="heatmap-legend-label">Less</span>
      <div class="heatmap-legend-scale">
        ${legendLevels
          .map(
            (item) => `
              <span class="heatmap-legend-cell bucket-${item.bucket}" aria-hidden="true"></span>
            `
          )
          .join("")}
      </div>
      <span class="heatmap-legend-label">More</span>
    </div>

    <div class="heatmap-calendar" role="img" aria-label="Project activity heatmap by day">
      <div class="heatmap-month-row">
        <div class="heatmap-month-spacer"></div>
        <div class="heatmap-month-labels">
          ${heatmap.monthLabels.map((label) => `<span class="heatmap-month-label">${escapeHtml(label)}</span>`).join("")}
        </div>
      </div>
      <div class="heatmap-body">
        <div class="heatmap-weekday-labels">
          <span>Sun</span>
          <span>Tue</span>
          <span>Thu</span>
          <span>Sat</span>
        </div>
        <div class="heatmap-weeks">
          ${heatmap.weeks
            .map(
              (week) => `
                <div class="heatmap-week-column">
                  ${week.days
                    .map(
                      (day) => `
                        <div
                          class="heatmap-square bucket-${day.bucket} ${day.inRange ? "" : "heatmap-square-empty"}"
                          title="${escapeHtml(day.label)} · ${day.count} activity event${day.count === 1 ? "" : "s"}"
                        ></div>
                      `
                    )
                    .join("")}
                </div>
              `
            )
            .join("")}
        </div>
      </div>
    </div>
  `;
}

function buildResumePreviewHtml(profile, projects, summaryData) {
  const topProjects = getFeaturedProjects(projects);
  const projectDetailsMap = getProjectDetailsMap(summaryData);

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);
  const backendSkills = dedupeStrings(summaryData?.skills);

  return `
    <div class="resume-preview-sheet">
      <div class="resume-preview-hero">
        <h1>${escapeHtml(profile.name)}</h1>
        <p class="resume-preview-role">${escapeHtml(profile.title)}</p>
      </div>

      <div class="resume-preview-section">
        <h3>Professional Summary</h3>
        <p>
          Computer Science student with hands-on experience building portfolio-focused software,
          working across frontend, backend, systems programming, and project analysis workflows.
          Current portfolio includes ${totalProjects} uploaded project${totalProjects === 1 ? "" : "s"},
          ${totalFiles} analyzed file${totalFiles === 1 ? "" : "s"}, and ${totalSkills} detected skill signal${totalSkills === 1 ? "" : "s"}.
        </p>
      </div>

      <div class="resume-preview-grid">
        <div class="resume-preview-section">
          <h3>Education</h3>
          <p>${escapeHtml(profile.education)}</p>
        </div>

        <div class="resume-preview-section">
          <h3>Awards</h3>
          <ul>
            ${profile.awards.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </div>
      </div>

      ${
        backendSkills.length
          ? `
            <div class="resume-preview-section">
              <h3>Core Skills</h3>
              <p>${escapeHtml(backendSkills.join(", "))}</p>
            </div>
          `
          : ""
      }

      <div class="resume-preview-section">
        <h3>Selected Projects</h3>
        ${
          topProjects.length
            ? topProjects
                .map((project) => {
                  const details = projectDetailsMap.get(project.project_id);
                  const override = getProjectOverride(project.project_id) || {};
                  const title = details?.title || project.project_id;
                  const summary =
                    override.portfolioBlurb ||
                    details?.summary ||
                    `${project.total_files} files analyzed • ${project.total_skills} skill signals • ${project.is_github ? "GitHub import" : "ZIP upload"}`;

                  return `
                    <div class="resume-preview-project">
                      <div class="resume-preview-project-title">${escapeHtml(title)}</div>
                      <div class="resume-preview-project-meta">${escapeHtml(summary)}</div>
                    </div>
                  `;
                })
                .join("")
            : `<p>No projects uploaded yet.</p>`
        }
      </div>

      <div class="resume-preview-section">
        <h3>Portfolio Highlights</h3>
        <ul>
          <li>${totalProjects} uploaded project${totalProjects === 1 ? "" : "s"} tracked in the desktop app</li>
          <li>${totalFiles} total analyzed file${totalFiles === 1 ? "" : "s"} across portfolio entries</li>
          <li>${totalSkills} total detected skill signal${totalSkills === 1 ? "" : "s"} from project analysis</li>
        </ul>
      </div>
    </div>
  `;
}

async function openResumePreview() {
  const modal = document.getElementById("resume-preview-modal");
  const body = document.getElementById("resume-preview-body");
  if (!modal || !body) return;

  body.innerHTML = `<p class="resume-summary-text">Loading resume preview...</p>`;
  modal.classList.remove("hidden");

  try {
    const [projects, summaryData] = await Promise.all([
      fetchProjects(),
      fetchPortfolioResumeSummary(),
    ]);

    const profile = buildProfile(summaryData);
    body.innerHTML = buildResumePreviewHtml(profile, projects, summaryData);
  } catch (err) {
    console.error("Failed to open resume preview:", err);
    body.innerHTML = `
      <div class="skills-group-card">
        <h3>Preview unavailable</h3>
        <p class="resume-summary-text">Unable to load live portfolio/resume data for the preview.</p>
      </div>
    `;
  }
}

function closeResumePreview() {
  const modal = document.getElementById("resume-preview-modal");
  modal?.classList.add("hidden");
}

export async function loadPortfolioResume() {
  const [projectsResult, timelineResult, summaryResult, heatmapResult] = await Promise.allSettled([
    fetchProjects(),
    fetchSkillsTimeline(),
    fetchPortfolioResumeSummary(),
    fetchActivityHeatmap(),
  ]);

  const projects = projectsResult.status === "fulfilled" ? projectsResult.value : [];
  const timeline = timelineResult.status === "fulfilled" ? timelineResult.value : [];
  const summaryData = summaryResult.status === "fulfilled" ? summaryResult.value : null;
  const heatmapData =
    heatmapResult.status === "fulfilled"
      ? heatmapResult.value
      : { cells: [], maxCount: 0, projectCount: 0 };

  const profile = buildProfile(summaryData);

  if (projectsResult.status === "rejected") {
    console.error("Failed to load portfolio/resume project data:", projectsResult.reason);
  }

  if (timelineResult.status === "rejected") {
    console.error("Failed to load skills timeline:", timelineResult.reason);
  }

  if (summaryResult.status === "rejected") {
    console.error("Failed to load portfolio summary data:", summaryResult.reason);
  }

  if (heatmapResult.status === "rejected") {
    console.error("Failed to load activity heatmap:", heatmapResult.reason);
  }

  renderResumeSummary(profile, projects, summaryData);
  renderTopProjects(projects, summaryData);
  renderPortfolioStats(projects, summaryData, timeline);
  renderSkillsTimeline(timeline);
  renderActivityHeatmap(heatmapData);
  applyPortfolioSectionVisibility();
}

export function initPortfolioResume() {
  loadPortfolioResume();

  if (portfolioResumeInitialized) return;
  portfolioResumeInitialized = true;

  const refreshBtn = document.getElementById("refresh-portfolio-btn");
  refreshBtn?.addEventListener("click", loadPortfolioResume);

  const previewBtn = document.getElementById("preview-resume-btn");
  previewBtn?.addEventListener("click", openResumePreview);

  const closeBtn = document.getElementById("resume-preview-close");
  closeBtn?.addEventListener("click", closeResumePreview);

  const modal = document.getElementById("resume-preview-modal");
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeResumePreview();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeResumePreview();
    }
  });

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-evidence-details]");
    if (!toggle) return;

    const projectId = toggle.dataset.evidenceDetails;
    const panel = document.querySelector(
      `[data-evidence-details-panel="${CSS.escape(projectId)}"]`
    );
    if (!panel) return;

    const isHidden = panel.classList.contains("hidden");
    panel.classList.toggle("hidden", !isHidden);
    toggle.textContent = isHidden ? "Hide Details" : "View Details";
  });

  window.addEventListener("portfolio:customization-updated", () => {
    loadPortfolioResume();
  });

  window.addEventListener("portfolio:data-updated", () => {
    loadPortfolioResume();
  });

  document.addEventListener("navigation:page-changed", (event) => {
    const { pageId } = event.detail ?? {};
    if (pageId === "resume-page" || pageId === "portfolio-page") {
      loadPortfolioResume();
    }
  });
}
