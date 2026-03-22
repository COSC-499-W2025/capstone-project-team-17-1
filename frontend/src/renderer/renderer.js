import { initPortfolioEditor } from "./portfolioEditor.js";
import { initChat } from "./chat.js";
import { initJobMatch } from "./jobMatch.js";
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
import { initPortfolio } from "./portfolio.js";
import { initResume } from "./resume.js";
import { initDisplayPreferences } from "./displayPreferences.js";
import { initDashboard } from "./dashboardInit.js";
import { initConsentBanner } from "./consentBanner.js";
import { initOnboarding } from "./onboarding.js";


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
  initChat();
  initAuthFlow();
  
  initPortfolio();
  initPortfolioEditor();
  initResume();
  initJobMatch();

  initDisplayPreferences();
  initConsentBanner();
  initOnboarding();

  loadProjects();

  initDashboard({
    loadMostUsedSkills,
    loadRecentProjects,
    loadProjectHealth,
    loadErrorAnalysis,
    loadRecentActivity,
    startMetrics,
  }).then(() => {
    setInterval(loadRecentActivity, 1000);
  });
  startMetrics();

});
