import { fetchProjects } from "./projects.js";
import { authFetch, getCurrentUser } from "./auth.js";
import {
  getProjectOverride,
  loadPortfolioCustomization,
} from "./portfolioState.js";
import { sortProjectsByRankedIds } from "./portfolioShared.mjs";

const API_BASE = "http://127.0.0.1:8002";

const SECTION_SELECTOR_MAP = {
  "top-projects": ".portfolio-projects-card",
  "portfolio-stats": ".portfolio-skills-card",
  "skills-timeline": ".portfolio-timeline-card",
  "activity-heatmap": ".portfolio-heatmap-card",
};

let portfolioInitialized = false;
const heatmapState = {
  granularity: "day",
  projectId: "",
  projects: [],
};
let projectEvolutionCache = new Map();

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

function toTitleCase(value) {
  return String(value || "")
    .split(/[\s-/]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function normalizeSkillName(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";

  const lower = raw.toLowerCase();
  const canonicalMap = {
    js: "JavaScript",
    javascript: "JavaScript",
    ts: "TypeScript",
    typescript: "TypeScript",
    json: "JSON",
    html: "HTML",
    css: "CSS",
    sql: "SQL",
    nosql: "NoSQL",
    api: "API",
    rest: "REST",
    graphql: "GraphQL",
    yaml: "YAML",
    xml: "XML",
    csv: "CSV",
    aws: "AWS",
    gcp: "GCP",
    fastapi: "FastAPI",
    sqlite: "SQLite",
    postgresql: "PostgreSQL",
    mongodb: "MongoDB",
    redis: "Redis",
    nodejs: "Node.js",
    expressjs: "Express.js",
    ui: "UI",
    ux: "UX",
    ci: "CI",
    cd: "CD",
  };

  return canonicalMap[lower] || toTitleCase(raw);
}

function dedupeStrings(values) {
  const seen = new Set();
  const result = [];
  asArray(values)
    .map((v) => normalizeSkillName(v))
    .filter(Boolean)
    .forEach((value) => {
      const key = value.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      result.push(value);
    });
  return result;
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

async function fetchRankedTopProjectIds(limit = 3) {
  const currentUser = getCurrentUser();
  const username =
    String(currentUser?.username || "").trim() ||
    String(currentUser?.full_name || "").trim();

  if (!username) {
    return [];
  }

  const res = await authFetch(
    `/showcase/portfolio/summary?user=${encodeURIComponent(username)}&limit=${encodeURIComponent(limit)}`
  );
  if (!res.ok) {
    throw new Error(`Failed to fetch ranked top projects: ${res.status}`);
  }

  const payload = await res.json();
  return Array.isArray(payload?.data)
    ? payload.data
        .map((item) => String(item?.project_id || "").trim())
        .filter(Boolean)
        .slice(0, limit)
    : [];
}

function getRankedTopProjects(projects, rankedIds = [], limit = 3) {
  if (Array.isArray(rankedIds) && rankedIds.length) {
    return sortProjectsByRankedIds(projects, rankedIds).slice(0, limit);
  }
  return getTopProjects(projects).slice(0, limit);
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

async function fetchActivityHeatmap(options = {}) {
  const params = new URLSearchParams();
  const granularity = String(options?.granularity || "day").trim().toLowerCase();
  const projectId = String(options?.projectId || "").trim();

  if (granularity) {
    params.set("granularity", granularity);
  }
  if (projectId) {
    params.set("project_id", projectId);
  }

  const query = params.toString();
  const res = await authFetch(`/portfolio/activity-heatmap${query ? `?${query}` : ""}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch activity heatmap: ${res.status}`);
  }
  const payload = await res.json();
  return payload?.data || { cells: [], maxCount: 0, projectCount: 0, projects: [], granularity };
}

async function fetchProjectEvolution(projectIds = []) {
  const cleaned = [...new Set(asArray(projectIds).map((value) => String(value || "").trim()).filter(Boolean))];
  if (!cleaned.length) {
    return {};
  }

  const params = new URLSearchParams();
  params.set("project_ids", cleaned.join(","));
  const res = await authFetch(`/portfolio/project-evolution?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch project evolution: ${res.status}`);
  }
  const payload = await res.json();
  return payload?.data || {};
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

function formatCompactDelta(value, suffix) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) return null;
  if (numeric > 0) return `+${numeric} ${suffix}`;
  if (numeric < 0) return `${numeric} ${suffix}`;
  return `0 ${suffix}`;
}

function renderEvolutionTimeline(project, details, override) {
  const projectId = String(project?.project_id || "").trim();
  const evolution = projectEvolutionCache.get(projectId);
  const steps = Array.isArray(evolution?.steps) ? evolution.steps : [];

  if (!steps.length) {
    const fallbackSteps = buildProjectEvolutionSteps(project, details, override);
    return `
      <div class="project-evolution-block">
        <span class="portfolio-detail-label">Project Evolution</span>
        <div class="project-evolution-steps">
          ${fallbackSteps
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
    `;
  }

  return `
    <div class="project-evolution-block">
      <span class="portfolio-detail-label">Project Evolution</span>
      <div class="project-evolution-steps project-evolution-steps-history">
        ${steps
          .map((step, stepIndex) => {
            const metricPills = [
              formatCompactDelta(step?.delta?.files, "files"),
              formatCompactDelta(step?.delta?.skills, "skills"),
              formatCompactDelta(step?.delta?.active_days, "active days"),
            ].filter(Boolean);
            const newSkills = Array.isArray(step?.new_skills) ? step.new_skills : [];
            const highlights = Array.isArray(step?.highlights) ? step.highlights : [];

            return `
              <div class="project-evolution-step project-evolution-step-history">
                <div class="project-evolution-marker">${stepIndex + 1}</div>
                <div class="project-evolution-content">
                  <div class="project-evolution-headline">
                    <div>
                      <div class="project-evolution-title">${escapeHtml(step?.label || `Iteration ${stepIndex + 1}`)}</div>
                      <div class="project-evolution-time">${escapeHtml(formatTimelineTimestamp(step?.timestamp || ""))}</div>
                    </div>
                    <div class="project-evolution-metrics">
                      <span class="stack-pill">${Number(step?.metrics?.files || 0)} Files</span>
                      <span class="stack-pill">${Number(step?.metrics?.skills || 0)} Skills</span>
                      <span class="stack-pill">${Number(step?.metrics?.active_days || 0)} Active Days</span>
                    </div>
                  </div>
                  ${
                    step?.changeSummary
                      ? `<p class="project-evolution-change-summary">${escapeHtml(step.changeSummary)}</p>`
                      : ""
                  }
                  ${
                    step?.summary
                      ? `<p class="project-evolution-text">${escapeHtml(step.summary)}</p>`
                      : ""
                  }
                  ${
                    metricPills.length
                      ? `<div class="project-evolution-delta-row">${metricPills.map((item) => `<span class="hero-stat-chip">${escapeHtml(item)}</span>`).join("")}</div>`
                      : ""
                  }
                  ${
                    newSkills.length
                      ? `<div class="project-evolution-detail-row"><span class="project-story-label">New Skills</span><div class="skills-pill-row">${newSkills.map((skill) => `<span class="skills-pill">${escapeHtml(skill)}</span>`).join("")}</div></div>`
                      : ""
                  }
                  ${
                    highlights.length
                      ? `<div class="project-evolution-detail-row"><span class="project-story-label">Signals From This Snapshot</span><ul class="resume-awards-list">${highlights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>`
                      : ""
                  }
                </div>
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function getTimelineSkillName(skill) {
  return normalizeSkillName(skill?.name || skill?.skill || "");
}

function getTimelineSkillWeight(skill) {
  const rawWeight = Number(skill?.weight ?? skill?.score ?? skill?.confidence ?? 0);
  if (!Number.isFinite(rawWeight)) return 0;
  return Math.max(0, rawWeight);
}

function getSharedSkillDepthLevel(depthScore) {
  if (depthScore >= 2.5) return "Advanced";
  if (depthScore >= 1.75) return "Proficient";
  if (depthScore >= 1.1) return "Developing";
  return "Foundation";
}

function getExpertiseLevelOrder() {
  return ["Advanced", "Proficient", "Developing", "Foundation"];
}

function getSkillGrowthLabel({
  previousWeight,
  currentWeight,
  appearanceCount,
  projectCount,
  previousComplexity,
  currentComplexity,
}) {
  if (appearanceCount <= 1) return "Baseline established";

  const weightDelta = currentWeight - previousWeight;
  const complexityDelta = currentComplexity - previousComplexity;

  if (weightDelta >= 0.08 && (projectCount >= 2 || complexityDelta >= 0.75)) {
    return "Depth increasing";
  }
  if (complexityDelta >= 1.2 || projectCount >= 3) {
    return "Expanding across projects";
  }
  if (weightDelta <= -0.08 && complexityDelta <= -0.75) {
    return "Applying in lighter scope";
  }
  return "Depth sustained";
}

function buildTimelineEntries(timeline) {
  const seenCounts = new Map();
  const previousWeights = new Map();
  const cumulativeWeights = new Map();
  const projectSets = new Map();
  const previousComplexities = new Map();

  return asArray(timeline).map((entry) => {
    const rawSkills = Array.isArray(entry?.skills) ? entry.skills : [];
    const aggregatedSkills = new Map();
    const projectId = String(entry?.project_id || "").trim();
    const projectMetrics =
      entry?.project_metrics && typeof entry.project_metrics === "object" ? entry.project_metrics : {};
    const currentComplexity = Number(projectMetrics?.complexity_score || 0);

    rawSkills.forEach((skill) => {
      const name = getTimelineSkillName(skill);
      const weight = getTimelineSkillWeight(skill);
      const current = aggregatedSkills.get(name) || { name, weight: 0 };
      current.weight += weight;
      aggregatedSkills.set(name, current);
    });

    const normalizedSkills = [...aggregatedSkills.values()].sort((a, b) => {
      if (b.weight !== a.weight) return b.weight - a.weight;
      return a.name.localeCompare(b.name);
    });

    let recurringCount = 0;
    let newCount = 0;
    let growthCount = 0;

    const decoratedSkills = normalizedSkills.map(({ name, weight }) => {
      const previousCount = seenCounts.get(name) || 0;
      const nextCount = previousCount + 1;
      const previousWeight = previousWeights.get(name) || 0;
      const cumulativeWeight = (cumulativeWeights.get(name) || 0) + weight;
      const projectSet = new Set(projectSets.get(name) || []);
      if (projectId) {
        projectSet.add(projectId);
      }
      const projectCount = projectSet.size;
      const previousComplexity = Number(previousComplexities.get(name) || 0);
      const depthScore = cumulativeWeight + nextCount * 0.35;
      const growthLabel = getSkillGrowthLabel({
        previousWeight,
        currentWeight: weight,
        appearanceCount: nextCount,
        projectCount,
        previousComplexity,
        currentComplexity,
      });

      seenCounts.set(name, nextCount);
      previousWeights.set(name, weight);
      cumulativeWeights.set(name, cumulativeWeight);
      projectSets.set(name, projectSet);
      previousComplexities.set(name, currentComplexity);

      if (previousCount > 0) recurringCount += 1;
      else newCount += 1;
      if (
        previousCount > 0 &&
        (
          weight > previousWeight + 0.08 ||
          projectCount >= 2 ||
          currentComplexity > previousComplexity + 0.75
        )
      ) {
        growthCount += 1;
      }

      return {
        name,
        appearanceCount: nextCount,
        projectCount,
        weight,
        depthScore,
        level: getSharedSkillDepthLevel(depthScore),
        growthLabel,
        status: previousCount > 0 ? "Recurring" : "First seen",
      };
    });

    return {
      ...entry,
      skills: decoratedSkills,
      meta: {
        totalSkills: normalizedSkills.length,
        recurringCount,
        newCount,
        growthCount,
      },
    };
  });
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
    Proficient: [],
    Developing: [],
    Foundation: [],
  };

  [...depthBySkill.values()]
    .map((skill) => {
      const depthScore = skill.totalWeight + skill.appearances * 0.35;
      return {
        ...skill,
        depthScore,
        level: getSharedSkillDepthLevel(depthScore),
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

function buildExpertiseSections(expertiseGroups) {
  return getExpertiseLevelOrder().map((level) => ({
    key: level,
    title: level,
    skills: Array.isArray(expertiseGroups?.[level]) ? expertiseGroups[level] : [],
  }));
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

function buildAggregatedHeatmapCalendar(cells, granularity) {
  const entries = [...cells]
    .map((cell) => ({
      key: String(cell.period || "").trim(),
      count: Number(cell.count || 0),
      bucket: getHeatmapBucket(Number(cell.intensity || 0)),
      label: formatHeatmapPeriod(cell.period, granularity),
    }))
    .filter((cell) => cell.key)
    .sort((a, b) => a.key.localeCompare(b.key));

  if (!entries.length) {
    return { columnLabels: [], rows: [] };
  }

  if (granularity === "month") {
    const byKey = new Map(entries.map((entry) => [entry.key, entry]));
    const years = [...new Set(entries.map((entry) => entry.key.slice(0, 4)))].sort();
    const columnLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const rows = years.map((year) => ({
      label: year,
      cells: columnLabels.map((monthLabel, index) => {
        const key = `${year}-${String(index + 1).padStart(2, "0")}`;
        const entry = byKey.get(key);
        return {
          key,
          label: entry?.label || `${monthLabel} ${year}`,
          count: entry?.count || 0,
          bucket: entry?.bucket || 0,
          inRange: Boolean(entry),
        };
      }),
    }));
    return { columnLabels, rows };
  }

  const byKey = new Map(entries.map((entry) => [entry.key, entry]));
  const years = entries.map((entry) => Number(entry.key)).filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  const startYear = years[0];
  const endYear = years[years.length - 1];
  const columnLabels = Array.from(
    { length: Math.min(12, endYear - startYear + 1) },
    (_, index) => String(startYear + index)
  );
  const rows = [];

  for (let cursor = startYear; cursor <= endYear; cursor += 12) {
    const rowYears = Array.from({ length: 12 }, (_, index) => cursor + index).filter((year) => year <= endYear);
    rows.push({
      label: `${cursor}${rowYears.length > 1 ? `-${rowYears[rowYears.length - 1]}` : ""}`,
      cells: rowYears.map((year) => {
        const key = String(year);
        const entry = byKey.get(key);
        return {
          key,
          label: entry?.label || key,
          count: entry?.count || 0,
          bucket: entry?.bucket || 0,
          inRange: Boolean(entry),
        };
      }),
    });
  }

  return { columnLabels, rows };
}

function formatHeatmapPeriod(period, granularity) {
  const raw = String(period || "").trim();
  if (!raw) return "Unknown";

  if (granularity === "year" && /^\d{4}$/.test(raw)) {
    return raw;
  }

  if (granularity === "month" && /^\d{4}-\d{2}$/.test(raw)) {
    const [year, month] = raw.split("-");
    const date = new Date(Number(year), Number(month) - 1, 1);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
    }
  }

  if (granularity === "day" && /^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const date = new Date(`${raw}T00:00:00`);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    }
  }

  return raw;
}

function renderHeatmapFilters(heatmapData) {
  const projects = Array.isArray(heatmapData?.projects) ? heatmapData.projects : [];
  heatmapState.projects = projects;

  return `
    <div class="heatmap-toolbar">
      <label class="heatmap-filter">
        <span>Time Filter</span>
        <select id="heatmap-granularity-select" class="heatmap-select">
          <option value="year" ${heatmapState.granularity === "year" ? "selected" : ""}>Year</option>
          <option value="month" ${heatmapState.granularity === "month" ? "selected" : ""}>Month</option>
          <option value="day" ${heatmapState.granularity === "day" ? "selected" : ""}>Day</option>
        </select>
      </label>
      <label class="heatmap-filter">
        <span>Project Map</span>
        <select id="heatmap-project-select" class="heatmap-select">
          <option value="" ${!heatmapState.projectId ? "selected" : ""}>All Projects</option>
          ${projects
            .map(
              (projectId) => `
                <option value="${escapeHtml(projectId)}" ${heatmapState.projectId === projectId ? "selected" : ""}>
                  ${escapeHtml(projectId)}
                </option>
              `
            )
            .join("")}
        </select>
      </label>
    </div>
  `;
}

async function refreshActivityHeatmap() {
  try {
    const heatmapData = await fetchActivityHeatmap({
      granularity: heatmapState.granularity,
      projectId: heatmapState.projectId,
    });
    renderActivityHeatmap(heatmapData);
  } catch (error) {
    console.error("Failed to refresh activity heatmap:", error);
  }
}

function bindHeatmapFilterEvents() {
  const granularitySelect = document.getElementById("heatmap-granularity-select");
  const projectSelect = document.getElementById("heatmap-project-select");

  granularitySelect?.addEventListener("change", async (event) => {
    heatmapState.granularity = String(event.target.value || "day").trim().toLowerCase() || "day";
    await refreshActivityHeatmap();
  });

  projectSelect?.addEventListener("change", async (event) => {
    heatmapState.projectId = String(event.target.value || "").trim();
    await refreshActivityHeatmap();
  });
}

function applyPortfolioSectionVisibility() {
  const customization = loadPortfolioCustomization();
  const sectionVisibility = {
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

function renderResumeSummary(profile, projects, summaryData, rankedTopProjectIds = []) {
  const container = document.getElementById("resume-summary-container");
  if (!container) return;

  const topProjects = getRankedTopProjects(projects, rankedTopProjectIds);

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

      <p class="muted-text">${escapeHtml(summary)}</p>

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
        topProjects.length
          ? `
            <div class="resume-meta-box">
              <span class="resume-meta-label">Top 3 Projects</span>
              <div class="skills-pill-row">
                ${topProjects
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

function renderTopProjects(projects, summaryData, rankedTopProjectIds = []) {
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
  const topProjects = getRankedTopProjects(projects, rankedTopProjectIds);

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
                      ${renderEvolutionTimeline(project, details, override)}
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
        <p class="muted-text">
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
  const expertiseSections = buildExpertiseSections(expertiseGroups);

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
      expertiseSections.some((section) => section.skills.length)
        ? `
          <div class="skills-group-card">
            <h3>Skills by Expertise Level</h3>
            <div class="skills-expertise-levels">
              ${expertiseSections
                .map(
                  (section) => `
                    <div class="skills-expertise-group">
                      <span class="skills-expertise-label">${escapeHtml(section.title)}</span>
                      <div class="skills-pill-row">
                        ${
                          section.skills.length
                            ? section.skills
                                .map((skill) => `<span class="skills-pill">${escapeHtml(skill)}</span>`)
                                .join("")
                            : `<span class="timeline-empty">No ${escapeHtml(section.title.toLowerCase())} skills yet</span>`
                        }
                      </div>
                    </div>
                  `
                )
                .join("")}
            </div>
          </div>
        `
        : `
          <div class="skills-group-card">
            <h3>No skills detected yet</h3>
            <p class="muted-text">
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
        <p class="muted-text">
          Upload projects with detected skills to generate a year-by-year skills timeline.
        </p>
      </div>
    `;
    return;
  }

  container.innerHTML = buildTimelineEntries(timeline)
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
            <div class="timeline-meta-row">
              <span class="timeline-meta-pill">${entry.meta.totalSkills} skill${entry.meta.totalSkills === 1 ? "" : "s"}</span>
              ${
                entry.meta.newCount
                  ? `<span class="timeline-meta-pill">${entry.meta.newCount} first seen</span>`
                  : ""
              }
              ${
                entry.meta.recurringCount
                  ? `<span class="timeline-meta-pill">${entry.meta.recurringCount} recurring</span>`
                  : ""
              }
              ${
                entry.meta.growthCount
                  ? `<span class="timeline-meta-pill">${entry.meta.growthCount} growing in depth</span>`
                  : ""
              }
            </div>
            <div class="timeline-skill-pills">
              ${
                skills.length
                  ? skills
                      .map((skill) => {
                        const metaParts = [
                          `${skill.status} · ${skill.appearanceCount} snapshot${skill.appearanceCount === 1 ? "" : "s"}`,
                          `${skill.projectCount} project${skill.projectCount === 1 ? "" : "s"}`,
                        ];
                        return `
                          <span class="timeline-skill-pill">
                            <span class="timeline-skill-name">${escapeHtml(skill.name)}</span>
                            <span class="timeline-skill-meta">${escapeHtml(skill.level)} · ${escapeHtml(skill.growthLabel)}</span>
                            <span class="timeline-skill-meta">${escapeHtml(metaParts.join(" · "))}</span>
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
  const granularity = String(heatmapData?.granularity || heatmapState.granularity || "day").trim().toLowerCase();
  const selectedProjectId = String(heatmapData?.selectedProjectId || heatmapState.projectId || "").trim();
  heatmapState.granularity = granularity;
  heatmapState.projectId = selectedProjectId;

  if (!cells.length) {
    container.innerHTML = `
      ${renderHeatmapFilters(heatmapData)}
      <div class="skills-group-card">
        <h3>No activity data yet</h3>
        <p class="muted-text">
          Upload projects with timeline or file activity data to generate a project activity heatmap.
        </p>
      </div>
    `;
    bindHeatmapFilterEvents();
    return;
  }

  // If activity data exists, keep the heatmap card visible even if an older local customization hid it.
  if (card) {
    card.style.display = "";
  }

  const totalActivity = cells.reduce((sum, cell) => sum + Number(cell.count || 0), 0);
  const averageActivity = cells.length ? Math.round(totalActivity / cells.length) : 0;
  const peakCell = [...cells].sort((a, b) => Number(b.count || 0) - Number(a.count || 0))[0];
  const heatmap = granularity === "day" ? buildContributionHeatmapModel(cells) : null;
  const aggregatedCalendar = granularity === "day" ? null : buildAggregatedHeatmapCalendar(cells, granularity);
  const legendLevels = [
    { label: "Low", bucket: 0 },
    { label: "", bucket: 1 },
    { label: "", bucket: 2 },
    { label: "", bucket: 3 },
    { label: "High", bucket: 4 },
  ];

  container.innerHTML = `
    ${renderHeatmapFilters(heatmapData)}
    <div class="heatmap-summary">
      <div>
        <p class="muted-text">
          ${selectedProjectId ? `Showing ${escapeHtml(selectedProjectId)}.` : `Aggregated activity across ${projectCount} project${projectCount === 1 ? "" : "s"}.`}
        </p>
        <div class="heatmap-chip-row">
          <span class="hero-stat-chip">${totalActivity} total activity events</span>
          <span class="hero-stat-chip">${averageActivity} avg / active ${escapeHtml(granularity)}</span>
          <span class="hero-stat-chip">Peak: ${escapeHtml(formatHeatmapPeriod(peakCell?.period || "", granularity))}</span>
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

    ${
      granularity === "day"
        ? `
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
        `
        : `
          <div
            class="heatmap-calendar heatmap-calendar-aggregated ${granularity === "year" ? "heatmap-calendar-aggregated-year" : ""}"
            role="img"
            aria-label="Project activity heatmap by ${escapeHtml(granularity)}"
          >
            <div class="heatmap-aggregated-calendar">
              <div class="heatmap-aggregated-topbar">
                <div class="heatmap-aggregated-corner"></div>
                <div class="heatmap-aggregated-columns">
                  ${aggregatedCalendar.columnLabels
                    .map(
                      (label) => `
                        <span class="heatmap-aggregated-column-label">${escapeHtml(label)}</span>
                      `
                    )
                    .join("")}
                </div>
              </div>
              <div class="heatmap-aggregated-rows">
                ${aggregatedCalendar.rows
                  .map(
                    (row) => `
                      <div class="heatmap-aggregated-row">
                        <span class="heatmap-aggregated-row-label">${escapeHtml(row.label)}</span>
                        <div class="heatmap-aggregated-grid">
                          ${row.cells
                            .map(
                              (entry) => `
                                <div
                                  class="heatmap-square bucket-${entry.bucket} ${entry.inRange ? "" : "heatmap-square-empty"}"
                                  title="${escapeHtml(entry.label)} · ${entry.count} activity event${entry.count === 1 ? "" : "s"}"
                                ></div>
                              `
                            )
                            .join("")}
                        </div>
                      </div>
                    `
                  )
                  .join("")}
              </div>
            </div>
          </div>
        `
    }
  `;
  bindHeatmapFilterEvents();
}

function buildResumePreviewHtml(profile, projects, summaryData, rankedTopProjectIds = [], timeline = []) {
  const topProjects = getRankedTopProjects(projects, rankedTopProjectIds);
  const projectDetailsMap = getProjectDetailsMap(summaryData);
  const expertiseGroups = buildSkillExpertiseGroups(timeline, summaryData);
  const expertiseSections = buildExpertiseSections(expertiseGroups);

  const totalProjects = projects.length;
  const totalFiles = projects.reduce((sum, p) => sum + (p.total_files || 0), 0);
  const totalSkills = projects.reduce((sum, p) => sum + (p.total_skills || 0), 0);

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

      <div class="resume-preview-section">
        <h3>Skills by Expertise Level</h3>
        <div class="resume-preview-grid">
          ${expertiseSections
            .map(
              (section) => `
                <div>
                  <strong>${escapeHtml(section.title)}</strong>
                  <p>${section.skills.length ? escapeHtml(section.skills.join(", ")) : `No ${escapeHtml(section.title.toLowerCase())} skills yet.`}</p>
                </div>
              `
            )
            .join("")}
        </div>
      </div>

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

function buildOnePageResumeSnapshot(profile, projects, summaryData, rankedTopProjectIds = [], timeline = []) {
  const topProjects = getRankedTopProjects(projects, rankedTopProjectIds);
  const projectDetailsMap = getProjectDetailsMap(summaryData);
  const expertiseGroups = buildSkillExpertiseGroups(timeline, summaryData);

  return {
    title: "One-Page Resume",
    owner: profile.name,
    target_role: profile.title,
    education: profile.education,
    awards: [...profile.awards],
    skills_by_expertise: Object.fromEntries(
      buildExpertiseSections(expertiseGroups).map((section) => [section.title, [...section.skills]])
    ),
    projects: topProjects.map((project) => {
      const details = projectDetailsMap.get(project.project_id);
      const override = getProjectOverride(project.project_id) || {};
      const title = details?.title || project.project_id;
      const summary =
        override.portfolioBlurb ||
        details?.summary ||
        `${project.total_files} files analyzed • ${project.total_skills} skill signals • ${project.is_github ? "GitHub import" : "ZIP upload"}`;
      const contribution = buildContributionSummary(project, details, override);
      const impact = buildImpactSummary(project, details, override);

      return {
        project_id: project.project_id,
        title,
        summary,
        contribution,
        impact,
      };
    }),
  };
}

function buildOnePageResumeMarkdown(snapshot) {
  const expertiseSections = getExpertiseLevelOrder().map((level) => ({
    title: level,
    skills: Array.isArray(snapshot.skills_by_expertise?.[level]) ? snapshot.skills_by_expertise[level] : [],
  }));
  const sections = [
    `# ${snapshot.title}`,
    "",
    `**Name:** ${snapshot.owner}`,
    `**Target Role:** ${snapshot.target_role}`,
    "",
    "## Education",
    snapshot.education,
    "",
    "## Awards",
    ...(snapshot.awards.length ? snapshot.awards.map((item) => `- ${item}`) : ["- None listed"]),
    "",
    "## Skills by Expertise Level",
    ...expertiseSections.map((section) => `**${section.title}:** ${section.skills.length ? section.skills.join(", ") : "None yet"}`),
    "",
    "## Projects",
    ...(
      snapshot.projects.length
        ? snapshot.projects.flatMap((project) => [
            `### ${project.title}`,
            project.summary,
            `- Contribution: ${project.contribution}`,
            `- Evidence of Success: ${project.impact}`,
            "",
          ])
        : ["No projects uploaded yet.", ""]
    ),
  ];

  return sections.join("\n").trim();
}

function buildOnePageResumePdfPayload(snapshot) {
  const expertiseSections = getExpertiseLevelOrder().map((level) => ({
    title: level,
    skills: Array.isArray(snapshot.skills_by_expertise?.[level]) ? snapshot.skills_by_expertise[level] : [],
  }));
  return {
    title: snapshot.title,
    target_role: snapshot.target_role,
    fullName: snapshot.owner,
    sections: [
      {
        name: "education",
        items: [
          {
            title: snapshot.education,
            content: snapshot.education,
          },
        ],
      },
      {
        name: "awards",
        items: snapshot.awards.map((award) => ({
          title: award,
          content: award,
        })),
      },
      {
        name: "core_skill",
        items: expertiseSections.map((section) => ({
          title: section.title,
          content: section.skills.length ? section.skills.join(", ") : "None yet",
        })),
      },
      {
        name: "projects",
        items: snapshot.projects.map((project) => ({
          title: project.title,
          content: project.summary,
          bullets: [
            `Contribution: ${project.contribution}`,
            `Evidence of Success: ${project.impact}`,
          ],
        })),
      },
    ],
  };
}

export async function buildOnePageResumeExportBundle() {
  const [projects, summaryData, rankedTopProjectIds, timeline] = await Promise.all([
    fetchProjects(),
    fetchPortfolioResumeSummary(),
    fetchRankedTopProjectIds().catch(() => []),
    fetchSkillsTimeline().catch(() => []),
  ]);

  const profile = buildProfile(summaryData);
  const snapshot = buildOnePageResumeSnapshot(
    profile,
    projects,
    summaryData,
    rankedTopProjectIds,
    timeline
  );

  return {
    snapshot,
    markdown: buildOnePageResumeMarkdown(snapshot),
    pdfPayload: buildOnePageResumePdfPayload(snapshot),
  };
}


export async function openResumePreview() {
  const modal = document.getElementById("resume-preview-modal");
  const body = document.getElementById("resume-preview-body");
  if (!modal || !body) return;

  body.innerHTML = `<p class="muted-text">Loading resume preview...</p>`;
  modal.classList.remove("hidden");

  try {
    const [projects, summaryData, rankedTopProjectIds, timeline] = await Promise.all([
      fetchProjects(),
      fetchPortfolioResumeSummary(),
      fetchRankedTopProjectIds().catch(() => []),
      fetchSkillsTimeline().catch(() => []),
    ]);
    const profile = buildProfile(summaryData);
    body.innerHTML = buildResumePreviewHtml(profile, projects, summaryData, rankedTopProjectIds, timeline);
  } catch (err) {
    console.error("Failed to open resume preview:", err);
    body.innerHTML = `<p class="muted-text">Unable to load resume preview.</p>`;
  }
}

function closeResumePreview() {
  const modal = document.getElementById("resume-preview-modal");
  modal?.classList.add("hidden");
}

export async function loadPortfolio() {
  heatmapState.granularity = "day";
  heatmapState.projectId = "";
  const [projectsResult, timelineResult, summaryResult, heatmapResult, rankedTopProjectsResult] = await Promise.allSettled([
    fetchProjects(),
    fetchSkillsTimeline(),
    fetchPortfolioResumeSummary(),
    fetchActivityHeatmap(),
    fetchRankedTopProjectIds(),
  ]);

  const projects = projectsResult.status === "fulfilled" ? projectsResult.value : [];
  const timeline = timelineResult.status === "fulfilled" ? timelineResult.value : [];
  const summaryData = summaryResult.status === "fulfilled" ? summaryResult.value : null;
  const heatmapData =
    heatmapResult.status === "fulfilled"
      ? heatmapResult.value
      : { cells: [], maxCount: 0, projectCount: 0 };
  const rankedTopProjectIds =
    rankedTopProjectsResult.status === "fulfilled" ? rankedTopProjectsResult.value : [];
  const topProjectsForEvolution = getRankedTopProjects(projects, rankedTopProjectIds);

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
  if (rankedTopProjectsResult.status === "rejected") {
    console.error("Failed to load ranked top projects:", rankedTopProjectsResult.reason);
  }

  try {
    const evolutionMap = await fetchProjectEvolution(topProjectsForEvolution.map((project) => project.project_id));
    projectEvolutionCache = new Map(Object.entries(evolutionMap || {}));
  } catch (error) {
    projectEvolutionCache = new Map();
    console.error("Failed to load project evolution:", error);
  }

  renderResumeSummary(profile, projects, summaryData, rankedTopProjectIds);
  renderTopProjects(projects, summaryData, rankedTopProjectIds);
  renderPortfolioStats(projects, summaryData, timeline);
  renderSkillsTimeline(timeline);
  renderActivityHeatmap(heatmapData);
  applyPortfolioSectionVisibility();
}

export function initPortfolio() {
  loadPortfolio();

  if (portfolioInitialized) return;
  portfolioInitialized = true;

  const refreshBtn = document.getElementById("refresh-portfolio-btn");
  refreshBtn?.addEventListener("click", loadPortfolio);

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
    loadPortfolio();
  });

  window.addEventListener("portfolio:data-updated", () => {
    loadPortfolio();
  });

  document.addEventListener("navigation:page-changed", (event) => {
    const { pageId } = event.detail ?? {};
    if (pageId === "resume-page" || pageId === "portfolio-page") {
      loadPortfolio();
    }
  });
}
