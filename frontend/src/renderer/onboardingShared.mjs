export function shouldPlaceOnboardingPanelRight({ detailOpen, tabKey, sectionLabel }) {
  if (!detailOpen) return false;
  if (["projects", "settings", "customization", "chat", "job-match"].includes(tabKey)) return true;
  return [
    "Top Projects",
    "Skills Timeline",
    "Most Used Skills",
    "Resume Snapshot",
    "Resume Generation",
    "Recent Projects",
    "View Project",
    "Pull Repository",
    "Upload Project",
    "Evidence Editing",
    "Activity Heatmap",
    "Live Preview",
    "Project Detail Drafts",
    "My Starred Projects",
  ].includes(sectionLabel || "");
}

export function shouldHighlightTutorialSection({ tabKey, sectionLabel }) {
  return !["projects", "settings", "job-match", "chat"].includes(tabKey)
    && !["Resume Generation", "My Starred Projects", "Project Detail Drafts"].includes(sectionLabel);
}
