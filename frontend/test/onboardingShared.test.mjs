import test from "node:test";
import assert from "node:assert/strict";

import {
  shouldHighlightTutorialSection,
  shouldPlaceOnboardingPanelRight,
} from "../src/renderer/onboardingShared.mjs";

test("shouldPlaceOnboardingPanelRight keeps collapsed tutorial on the left", () => {
  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: false,
      tabKey: "portfolio-resume",
      sectionLabel: "Top Projects",
    }),
    false
  );
});

test("shouldPlaceOnboardingPanelRight moves projects, settings, customization, chat, and job match detail panels to the right", () => {
  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "projects",
      sectionLabel: "Upload Project",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "settings",
      sectionLabel: "Consent",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "customization",
      sectionLabel: "Featured Projects",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "chat",
      sectionLabel: "Conversation",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "job-match",
      sectionLabel: "Featured Projects",
    }),
    true
  );
});

test("shouldPlaceOnboardingPanelRight moves selected dashboard and portfolio details to the right", () => {
  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "dashboard",
      sectionLabel: "Recent Projects",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "portfolio-resume",
      sectionLabel: "Resume Snapshot",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "portfolio-resume",
      sectionLabel: "Portfolio Stats",
    }),
    false
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "portfolio",
      sectionLabel: "Evidence Editing",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "portfolio",
      sectionLabel: "Activity Heatmap",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "portfolio",
      sectionLabel: "Live Preview",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "portfolio",
      sectionLabel: "Project Detail Drafts",
    }),
    true
  );

  assert.equal(
    shouldPlaceOnboardingPanelRight({
      detailOpen: true,
      tabKey: "portfolio",
      sectionLabel: "My Starred Projects",
    }),
    true
  );
});

test("shouldHighlightTutorialSection disables white frames for projects, settings, job match, chat, and resume generation", () => {
  assert.equal(
    shouldHighlightTutorialSection({ tabKey: "projects", sectionLabel: "Upload Project" }),
    false
  );

  assert.equal(
    shouldHighlightTutorialSection({ tabKey: "settings", sectionLabel: "Consent" }),
    false
  );

  assert.equal(
    shouldHighlightTutorialSection({ tabKey: "job-match", sectionLabel: "Featured Projects" }),
    false
  );

  assert.equal(
    shouldHighlightTutorialSection({ tabKey: "chat", sectionLabel: "Conversation" }),
    false
  );

  assert.equal(
    shouldHighlightTutorialSection({ tabKey: "portfolio-resume", sectionLabel: "Resume Generation" }),
    false
  );

  assert.equal(
    shouldHighlightTutorialSection({ tabKey: "portfolio", sectionLabel: "Project Detail Drafts" }),
    false
  );

  assert.equal(
    shouldHighlightTutorialSection({ tabKey: "portfolio", sectionLabel: "My Starred Projects" }),
    false
  );

  assert.equal(
    shouldHighlightTutorialSection({ tabKey: "customization", sectionLabel: "Live Preview" }),
    true
  );
});
