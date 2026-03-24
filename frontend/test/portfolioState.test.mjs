import test from "node:test";
import assert from "node:assert/strict";

import { getFeaturedProjectsBySavedOrder } from "../src/renderer/portfolioStateShared.mjs";

test("getFeaturedProjectsBySavedOrder preserves saved starred order", () => {
  const projects = [
    { project_id: "proj-a" },
    { project_id: "proj-b" },
    { project_id: "proj-c" },
    { project_id: "proj-d" },
  ];

  assert.deepEqual(
    getFeaturedProjectsBySavedOrder(projects, ["proj-c", "proj-a", "proj-d"]).map(
      (project) => project.project_id
    ),
    ["proj-c", "proj-a", "proj-d"]
  );
});

test("getFeaturedProjectsBySavedOrder ignores missing ids", () => {
  const projects = [
    { project_id: "proj-a" },
    { project_id: "proj-b" },
  ];

  assert.deepEqual(
    getFeaturedProjectsBySavedOrder(projects, ["proj-x", "proj-b", "proj-a"]).map(
      (project) => project.project_id
    ),
    ["proj-b", "proj-a"]
  );
});
