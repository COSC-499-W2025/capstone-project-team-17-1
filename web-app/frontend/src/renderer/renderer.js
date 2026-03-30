import { initThemeToggle } from "./theme.js";
import { loadMostUsedSkills } from "./skills.js";
import { loadRecentActivity } from "./activity.js";
import { loadRecentProjects } from "./recentProjects.js";
import { loadProjectHealth } from "./projectHealth.js";
import { loadErrorAnalysis } from "./errors.js";
import { loadProjects } from "./projects.js";
import { initAuthFlow, isAuthenticated } from "./auth.js";
import { openUploadModal } from "./uploadModal.js";
import { initNavigation } from "./navigation.js";
import { initPortfolioResume } from "./portfolioResume.js";
import { initDisplayPreferences } from "./displayPreferences.js";

document.addEventListener("DOMContentLoaded", async () => {
  const uploadBtn = document.getElementById("upload-project-btn");
  uploadBtn?.addEventListener("click", openUploadModal);

  initThemeToggle();

  await initAuthFlow();

  if (isAuthenticated()) {
    initNavigation();
    initDisplayPreferences();
    initPortfolioResume();

    await loadMostUsedSkills();
    await loadRecentProjects();
    await loadProjectHealth();
    await loadErrorAnalysis();
    await loadProjects();
  }

});
