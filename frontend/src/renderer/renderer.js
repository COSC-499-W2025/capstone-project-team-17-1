import { initThemeToggle } from "./theme.js";
import { initWindowControls } from "./windowControls.js";
import { startMetrics } from "./metrics.js";
import { loadMostUsedSkills } from "./skills.js";
import { loadRecentActivity } from "./activity.js";
import { loadRecentProjects } from "./recentProjects.js";
import { loadProjectHealth } from "./projectHealth.js";
import { loadErrorAnalysis } from "./errors.js";
import { loadProjects } from "./projects.js";
import { initAuthFlow } from "./auth.js";
import { openUploadModal } from "./uploadModal.js";
import { initNavigation } from "./navigation.js";
import { initPortfolioResume } from "./portfolioResume.js";
import { initDisplayPreferences } from "./displayPreferences.js";


// -----------------------------
// Upload button
// -----------------------------

const uploadBtn = document.getElementById("upload-project-btn");

uploadBtn?.addEventListener("click", openUploadModal);


// -----------------------------
// Initial Page Setup
// -----------------------------

document.addEventListener("DOMContentLoaded", () => {

  initThemeToggle();

  initWindowControls();

  initAuthFlow();

  // these are for portfolio/resume feature 
  initNavigation();
  
  initPortfolioResume();

  initDisplayPreferences();

  startMetrics();

  loadMostUsedSkills();

  loadRecentProjects();

  loadProjectHealth();

  loadErrorAnalysis();

  loadProjects();

  loadRecentActivity();




  setInterval(loadRecentActivity, 1000);


});
