import test from "node:test";
import assert from "node:assert/strict";

import {
  getDefaultDashboardSelection,
  normalizeSelectedIds,
  shouldShowDashboardWidget,
} from "../src/renderer/displayPreferencesShared.mjs";

test("getDefaultDashboardSelection returns all known dashboard widget ids", () => {
  assert.deepEqual(getDefaultDashboardSelection(), [
    "most-used-skills",
    "error-analysis",
    "project-health",
    "recent-projects",
    "system-health",
    "activity-log",
  ]);
});

test("normalizeSelectedIds drops unknown ids and preserves known order", () => {
  assert.deepEqual(normalizeSelectedIds(["recent-projects", "unknown", "activity-log"]), [
    "recent-projects",
    "activity-log",
  ]);
});

test("shouldShowDashboardWidget matches by search text", () => {
  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "recent-projects",
      label: "Recent Projects",
      category: "projects",
      state: { search: "recent", category: "all" },
      isPrivateMode: false,
      selectedIds: [],
    }),
    true
  );

  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "recent-projects",
      label: "Recent Projects",
      category: "projects",
      state: { search: "errors", category: "all" },
      isPrivateMode: false,
      selectedIds: [],
    }),
    false
  );
});

test("shouldShowDashboardWidget matches by category", () => {
  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "system-health",
      label: "System Health",
      category: "system",
      state: { search: "", category: "system" },
      isPrivateMode: false,
      selectedIds: [],
    }),
    true
  );

  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "system-health",
      label: "System Health",
      category: "system",
      state: { search: "", category: "projects" },
      isPrivateMode: false,
      selectedIds: [],
    }),
    false
  );
});

test("shouldShowDashboardWidget respects private mode selections", () => {
  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "activity-log",
      label: "Activity Log",
      category: "activity",
      state: { search: "", category: "all" },
      isPrivateMode: true,
      selectedIds: ["activity-log"],
    }),
    true
  );

  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "activity-log",
      label: "Activity Log",
      category: "activity",
      state: { search: "", category: "all" },
      isPrivateMode: true,
      selectedIds: ["recent-projects"],
    }),
    false
  );
});
