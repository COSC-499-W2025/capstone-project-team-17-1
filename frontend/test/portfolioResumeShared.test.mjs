import test from "node:test";
import assert from "node:assert/strict";

import {
  buildSkillsTimelineMarkup,
  buildTopProjectsMarkup,
  formatTimelineTimestamp,
  getTopProjects,
  sortProjectsByRankedIds,
} from "../src/renderer/portfolioShared.mjs";

test("getTopProjects returns the top 3 projects ordered by skills then files", () => {
  const projects = [
    { project_id: "delta", total_skills: 1, total_files: 40 },
    { project_id: "alpha", total_skills: 5, total_files: 10 },
    { project_id: "beta", total_skills: 5, total_files: 22 },
    { project_id: "gamma", total_skills: 3, total_files: 50 },
  ];

  assert.deepEqual(
    getTopProjects(projects).map((project) => project.project_id),
    ["beta", "alpha", "gamma"]
  );
});

test("sortProjectsByRankedIds respects backend ranked ids before local fallbacks", () => {
  const projects = [
    { project_id: "delta", total_skills: 1, total_files: 40 },
    { project_id: "alpha", total_skills: 5, total_files: 10 },
    { project_id: "beta", total_skills: 5, total_files: 22 },
    { project_id: "gamma", total_skills: 3, total_files: 50 },
  ];

  assert.deepEqual(
    sortProjectsByRankedIds(projects, ["gamma", "alpha"]).map((project) => project.project_id),
    ["gamma", "alpha", "beta", "delta"]
  );
});

test("buildTopProjectsMarkup renders private-mode details for the top 3 projects only", () => {
  const projects = [
    { project_id: "proj-a", total_skills: 4, total_files: 10, is_github: true },
    { project_id: "proj-b", total_skills: 6, total_files: 8, is_github: false },
    { project_id: "proj-c", total_skills: 5, total_files: 20, is_github: false },
    { project_id: "proj-d", total_skills: 1, total_files: 100, is_github: true },
  ];
  const summaryData = {
    projects: [
      {
        project_id: "proj-b",
        title: "Project B",
        summary: "Refined uploader",
        technologies: ["FastAPI", "SQLite"],
        highlights: ["better sync handling"],
      },
      {
        project_id: "proj-c",
        title: "Project C",
        technologies: ["Electron"],
        highlights: ["improved dashboard filters"],
      },
    ],
  };

  const markup = buildTopProjectsMarkup({
    projects,
    summaryData,
    isPrivateMode: true,
    getProjectThumbnailUrl: (projectId) => `/thumbs/${projectId}.png`,
  });

  assert.match(markup, /#1/);
  assert.match(markup, /Project B/);
  assert.match(markup, /View Details/);
  assert.match(markup, /Process/);
  assert.match(markup, /Evolution/);
  assert.match(markup, /\/thumbs\/proj-b\.png/);
  assert.match(markup, /data-project-thumbnail-trigger="proj-b"/);
  assert.match(markup, /Upload thumbnail/);
  assert.match(markup, /ZIP Upload/);
  assert.match(markup, /GitHub Import/);
  assert.ok(!markup.includes("proj-d"), "fourth-ranked project should not be rendered");
});

test("buildTopProjectsMarkup omits private details in public mode", () => {
  const markup = buildTopProjectsMarkup({
    projects: [{ project_id: "proj-a", total_skills: 2, total_files: 5, is_github: false }],
    summaryData: null,
    isPrivateMode: false,
    getProjectThumbnailUrl: () => "/thumb.png",
  });

  assert.ok(!markup.includes("Process"));
  assert.ok(!markup.includes("Evolution"));
  assert.match(markup, /Contribution/);
  assert.match(markup, /Evidence of Success/);
  assert.match(markup, /data-evidence-details=/);
  assert.match(markup, /View Details/);
});

test("buildTopProjectsMarkup highlights contribution and impact evidence", () => {
  const markup = buildTopProjectsMarkup({
    projects: [{ project_id: "proj-a", total_skills: 4, total_files: 12, is_github: true }],
    summaryData: {
      projects: [
        {
          project_id: "proj-a",
          title: "Project A",
          summary: "Portfolio-ready project",
          technologies: ["FastAPI", "SQLite"],
          highlights: ["Implemented incremental uploads", "Improved project analysis visibility"],
        },
      ],
    },
    isPrivateMode: false,
    getProjectThumbnailUrl: () => "/thumb.png",
  });

  assert.match(markup, /Contribution/);
  assert.match(markup, /Implemented Incremental Uploads/);
  assert.match(markup, /Evidence of Success/);
  assert.match(markup, /View Details/);
  assert.match(markup, /data-evidence-details-panel="proj-a"/);
  assert.match(markup, /12 files analyzed/);
  assert.match(markup, /4 skill signals detected/);
});

test("formatTimelineTimestamp returns a stable YYYY-MM-DD HH:mm:ss-like timestamp", () => {
  const formatted = formatTimelineTimestamp("2026-03-10T13:14:15Z");

  assert.match(formatted, /\d{4}-\d{2}-\d{2}/);
  assert.match(formatted, /\d{2}:\d{2}:\d{2}/);
});

test("buildSkillsTimelineMarkup renders timeline nodes with timestamps, project labels, and skills", () => {
  const markup = buildSkillsTimelineMarkup([
    {
      timestamp: "2026-03-10T13:14:15Z",
      project_id: "proj-a",
      skills: [{ name: "Python" }, { skill: "FastAPI" }],
    },
    {
      timestamp: "2026-03-09T09:00:00Z",
      project_id: "proj-b",
      skills: [{ name: "Python" }],
    },
  ]);

  assert.match(markup, /timeline-time-label/);
  assert.match(markup, /timeline-project-label/);
  assert.match(markup, /timeline-meta-pill/);
  assert.match(markup, /Python/);
  assert.match(markup, /FastAPI/);
  assert.match(markup, /proj-a/);
  assert.match(markup, /First seen/);
  assert.match(markup, /Recurring/);
  assert.match(markup, /2 snapshots/);
});

test('buildSkillsTimelineMarkup filters placeholder "0" skills from timeline output', () => {
  const markup = buildSkillsTimelineMarkup([
    {
      timestamp: "2026-03-10T13:14:15Z",
      project_id: "proj-a",
      skills: [{ skill: "0", weight: 2 }, { skill: "python", weight: 1 }],
    },
  ]);

  assert.match(markup, /Python/);
  assert.doesNotMatch(markup, />0</);
});

test("buildSkillsTimelineMarkup hides fully empty timeline rows", () => {
  const markup = buildSkillsTimelineMarkup([
    {
      timestamp: "2026-03-09T09:00:00Z",
      project_id: "proj-b",
      skills: [],
    },
  ]);

  assert.match(markup, /No timeline data yet/);
  assert.doesNotMatch(markup, /No skills recorded/);
});

test("buildSkillsTimelineMarkup renders empty state when timeline data is missing", () => {
  const markup = buildSkillsTimelineMarkup([]);

  assert.match(markup, /No timeline data yet/);
  assert.match(markup, /generate a skills timeline/);
});
