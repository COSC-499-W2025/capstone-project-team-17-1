import test from "node:test";
import assert from "node:assert/strict";

import {
  shouldRequireLoginForTab,
  shouldRequireLoginForSettingsTab,
} from "../src/renderer/authShared.mjs";

test("shouldRequireLoginForTab gates customization in public mode", () => {
  assert.equal(shouldRequireLoginForTab("customization", null), true);
});

test("shouldRequireLoginForTab allows public tabs without login", () => {
  assert.equal(shouldRequireLoginForTab("dashboard", null), false);
  assert.equal(shouldRequireLoginForTab("projects", null), false);
  assert.equal(shouldRequireLoginForTab("portfolio-resume", null), false);
  assert.equal(shouldRequireLoginForTab("settings", null), false);
});

test("shouldRequireLoginForTab allows gated tabs when a user exists", () => {
  const user = { id: 1, username: "demo" };
  assert.equal(shouldRequireLoginForTab("settings", user), false);
  assert.equal(shouldRequireLoginForTab("customization", user), false);
});

test("shouldRequireLoginForSettingsTab only allows privacy in public mode", () => {
  assert.equal(shouldRequireLoginForSettingsTab("general", null), true);
  assert.equal(shouldRequireLoginForSettingsTab("account", null), true);
  assert.equal(shouldRequireLoginForSettingsTab("security", null), true);
  assert.equal(shouldRequireLoginForSettingsTab("privacy", null), false);
});

test("shouldRequireLoginForSettingsTab allows all settings tabs for signed-in users", () => {
  const user = { id: 1, username: "demo" };
  assert.equal(shouldRequireLoginForSettingsTab("general", user), false);
  assert.equal(shouldRequireLoginForSettingsTab("account", user), false);
  assert.equal(shouldRequireLoginForSettingsTab("security", user), false);
  assert.equal(shouldRequireLoginForSettingsTab("privacy", user), false);
});
