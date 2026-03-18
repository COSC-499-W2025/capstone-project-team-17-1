import test from "node:test";
import assert from "node:assert/strict";

import { shouldRequireLoginForTab } from "../src/renderer/authShared.mjs";

test("shouldRequireLoginForTab gates settings and customization in public mode", () => {
  assert.equal(shouldRequireLoginForTab("settings", null), true);
  assert.equal(shouldRequireLoginForTab("customization", null), true);
});

test("shouldRequireLoginForTab allows public tabs without login", () => {
  assert.equal(shouldRequireLoginForTab("dashboard", null), false);
  assert.equal(shouldRequireLoginForTab("projects", null), false);
  assert.equal(shouldRequireLoginForTab("portfolio-resume", null), false);
});

test("shouldRequireLoginForTab allows gated tabs when a user exists", () => {
  const user = { id: 1, username: "demo" };
  assert.equal(shouldRequireLoginForTab("settings", user), false);
  assert.equal(shouldRequireLoginForTab("customization", user), false);
});
