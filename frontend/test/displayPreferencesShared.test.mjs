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

test("normalizeSelectedIds returns empty array when no known ids are selected", () => {
  assert.deepEqual(normalizeSelectedIds([]), []);
  assert.deepEqual(normalizeSelectedIds(["unknown-a", "unknown-b"]), []);
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

test("shouldShowDashboardWidget shows all widgets when all ids are selected (dashboard default state)", () => {
  const allIds = getDefaultDashboardSelection();
  for (const id of allIds) {
    assert.equal(
      shouldShowDashboardWidget({
        widgetId: id,
        label: id,
        category: "all",
        state: { search: "", category: "all" },
        isPrivateMode: true,
        selectedIds: allIds,
      }),
      true,
      `widget "${id}" should be visible when all are selected`
    );
  }
});

test("shouldShowDashboardWidget hides all widgets when selectedIds is empty", () => {
  const allIds = getDefaultDashboardSelection();
  for (const id of allIds) {
    assert.equal(
      shouldShowDashboardWidget({
        widgetId: id,
        label: id,
        category: "all",
        state: { search: "", category: "all" },
        isPrivateMode: true,
        selectedIds: [],
      }),
      false,
      `widget "${id}" should be hidden when nothing is selected`
    );
  }
});

test("shouldShowDashboardWidget applies search and selection together", () => {
  // matches search but NOT in selection → hidden
  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "most-used-skills",
      label: "Most Used Skills",
      category: "all",
      state: { search: "skills", category: "all" },
      isPrivateMode: true,
      selectedIds: ["activity-log"],
    }),
    false
  );

  // in selection but does NOT match search → hidden
  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "activity-log",
      label: "Activity Log",
      category: "all",
      state: { search: "skills", category: "all" },
      isPrivateMode: true,
      selectedIds: ["activity-log"],
    }),
    false
  );

  // matches search AND in selection → visible
  assert.equal(
    shouldShowDashboardWidget({
      widgetId: "activity-log",
      label: "Activity Log",
      category: "all",
      state: { search: "activity", category: "all" },
      isPrivateMode: true,
      selectedIds: ["activity-log"],
    }),
    true
  );
});
