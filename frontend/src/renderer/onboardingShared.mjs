export function shouldPlaceOnboardingPanelRight({ detailOpen, tabKey, sectionLabel }) {
  if (!detailOpen) return false;
  if (["projects", "settings", "customization"].includes(tabKey)) return true;
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
  ].includes(sectionLabel || "");
}

export function shouldHighlightTutorialSection({ tabKey, sectionLabel }) {
  return !["projects", "settings"].includes(tabKey) && sectionLabel !== "Resume Generation";
}
