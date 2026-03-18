import { openLoginFlow } from "./auth.js";
import { switchPage } from "./navigation.js";
import { shouldHighlightTutorialSection, shouldPlaceOnboardingPanelRight } from "./onboardingShared.mjs";

const ONBOARDING_KEY = "loom_onboarding_completed_v1";

const TUTORIAL_STEPS = [
  {
    tabKey: "dashboard",
    pageId: "dashboard-page",
    title: "Dashboard",
    description: "Dashboard gives you a quick view of recent projects, health signals, activity, and system status in one place.",
    sections: [
      {
        label: "Most Used Skills",
        selector: "#most-used-skills",
        description: "Most Used Skills summarizes the tools and languages that appear most often across your analyzed projects.",
      },
      {
        label: "Error Analysis",
        selector: ".error-analysis-card",
        description: "Error Analysis highlights potential issues once consent is granted for analysis features.",
      },
      {
        label: "Project Health",
        selector: "#project-health-card",
        description: "Project Health summarizes project quality and status signals so you can spot issues quickly.",
      },
      {
        label: "Recent Projects",
        selector: ".recent-projects-card",
        description: "Recent Projects gives you a quick way to jump back into the newest analyzed work.",
      },
      {
        label: "System Health",
        selector: "#system-health-card",
        description: "System Health shows device status and live resource usage while the app is running.",
      },
      {
        label: "Activity Log",
        selector: "#activity-log-card",
        description: "Activity Log shows recent events and processing activity across the app.",
      },
    ],
  },
  {
    tabKey: "projects",
    pageId: "projects-page",
    title: "Projects",
    description: "Projects is where you upload ZIP files or import repositories so Loom can analyze your work.",
    sections: [
      {
        label: "Upload Project",
        selectors: ["#upload-project-btn", ".projects-header"],
        description: "Upload Project lets you add ZIP archives so Loom can analyze files, skills, and project structure.",
      },
      {
        label: "Pull Repository",
        selector: ".pull-btn",
        description: "Pull Repository lets you bring in repository content so the app can build portfolio and dashboard insights from it.",
      },
      {
        label: "View Project",
        selector: ".view-btn",
        description: "View Project opens analyzed projects so you can inspect files, code, and project-level details.",
      },
    ],
  },
  {
    tabKey: "portfolio-resume",
    pageId: "portfolio-resume-page",
    title: "Portfolio & Resume",
    description: "Portfolio & Resume shows your one-page resume, top projects, skills timeline, and activity heatmap.",
    sections: [
      {
        label: "Resume Generation",
        selectors: [".resume-manager-card"],
        description: "Resume Generation lets you browse saved resumes and view the one-page resume snapshot built from your portfolio data.",
      },
      {
        label: "Resume Snapshot",
        selector: ".portfolio-hero-card",
        description: "Resume Snapshot condenses your education, awards, skills, and project highlights into a one-page resume view.",
      },
      {
        label: "Top Projects",
        selector: ".portfolio-projects-card",
        description: "Top Projects highlights your strongest projects with contribution evidence and success details.",
      },
      {
        label: "Portfolio Stats",
        selector: ".portfolio-skills-card",
        description: "Portfolio Stats summarizes your strongest skills and expertise signals in one place.",
      },
      {
        label: "Skills Timeline",
        selector: ".portfolio-timeline-card",
        description: "Skills Timeline shows how your tools and expertise have grown across projects over time.",
      },
      {
        label: "Activity Heatmap",
        selector: ".portfolio-heatmap-card",
        description: "Activity Heatmap shows when project work happened so you can see productivity over time.",
      },
    ],
  },
  {
    tabKey: "customization",
    pageId: "customization-page",
    title: "Customization",
    description: "Customization is only available in private mode and lets you tailor featured projects, evidence, and visible sections before sharing.",
    sections: [
      {
        label: "Job Description",
        selectors: ["#customization-job-card"],
        description: "Job Description lets you enter a target role so the app can tailor portfolio wording and matching around that position.",
      },
      {
        label: "Sections",
        selectors: ["#customization-sections-card"],
        description: "Choose which sections appear publicly and control the structure of the portfolio view.",
      },
      {
        label: "Featured Projects",
        selectors: ["#customization-featured-card"],
        description: "Reorder featured projects and control which work is emphasized first.",
      },
      {
        label: "Evidence Editing",
        selectors: ["#customization-editor-card"],
        description: "Edit contribution and evidence text before sharing. This tab is private-mode only.",
      },
      {
        label: "Live Preview",
        selectors: ["#customization-preview-card"],
        description: "Live Preview shows how your portfolio changes will look before you share them publicly.",
      },
    ],
  },
  {
    tabKey: "settings",
    pageId: "settings-page",
    title: "Settings",
    description: "Settings lets you manage your profile and control local-processing and external-AI consent.",
    sections: [
      {
        label: "Profile",
        selector: "#settings-profile",
        description: "Edit your name and profile information used throughout the app and portfolio.",
      },
      {
        label: "Consent",
        selector: "#settings-consent",
        description: "Manage local-processing and external-AI consent. If analysis features are blocked, grant consent here.",
      },
      {
        label: "Tutorial",
        selectors: ["#show-tutorial-btn", "#settings-profile"],
        description: "Use Settings to update personal information, change your password, and reopen this tutorial whenever you want a guided walkthrough again.",
      },
    ],
  },
];

let tutorialActive = false;
let currentStepIndex = 0;
let listenersBound = false;
let detailOpen = false;
let currentSectionIndex = 0;

function getPanel() {
  return document.getElementById("onboarding-panel");
}

function getStep(index) {
  return TUTORIAL_STEPS[index] || TUTORIAL_STEPS[0];
}

function markCompleted() {
  localStorage.setItem(ONBOARDING_KEY, "true");
}

function clearSectionFocus() {
  document.querySelectorAll(".tutorial-section-focus, .tutorial-section-target").forEach((element) => {
    element.classList.remove("tutorial-section-focus");
    element.classList.remove("tutorial-section-target");
  });
}

function getSectionTargets(section) {
  const selectors = section.selectors || (section.selector ? [section.selector] : []);
  return selectors
    .flatMap((selector) => {
      try {
        return Array.from(document.querySelectorAll(selector));
      } catch {
        return [];
      }
    })
    .filter((element, index, elements) => Boolean(element) && elements.indexOf(element) === index);
}

function setTutorialTabState(tabKey) {
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    const isActive = tab.dataset.tab === tabKey;
    tab.classList.toggle("active", isActive);
    tab.classList.toggle("tutorial-focus", isActive && tutorialActive);
  });
}

function renderStep() {
  const panel = getPanel();
  if (!panel) return;

  const step = getStep(currentStepIndex);
  const progress = document.getElementById("onboarding-progress");
  const title = document.getElementById("onboarding-step-title");
  const body = document.getElementById("onboarding-step-body");
  const nextBtn = document.getElementById("onboarding-next-btn");
  const signInBtn = document.getElementById("onboarding-signin-btn");
  const detailBox = document.getElementById("onboarding-detail-box");
  const detailBtn = document.getElementById("onboarding-show-details-btn");
  const leaveBtn = document.getElementById("onboarding-leave-btn");
  const hint = document.getElementById("onboarding-hint-text");
  const currentSection = step.sections[currentSectionIndex] || step.sections[0];

  switchPage(detailOpen ? step.pageId : "dashboard-page");
  setTutorialTabState(step.tabKey);
  clearSectionFocus();
  panel.classList.toggle(
    "onboarding-panel-right",
    shouldPlaceOnboardingPanelRight({
      detailOpen,
      tabKey: step.tabKey,
      sectionLabel: currentSection?.label || "",
    }),
  );

  if (progress) {
    progress.textContent = `Step ${currentStepIndex + 1} of ${TUTORIAL_STEPS.length}`;
  }
  if (title) {
    title.textContent = step.title;
  }
  if (body) {
    body.textContent = detailOpen
      ? "Click a section card to see what that part of the page is for."
      : "Click View Details to see what each section does.";
  }
  if (hint) {
    hint.textContent = detailOpen
      ? ""
      : step.description;
  }
  const hintBox = hint?.closest(".onboarding-hint");
  if (hintBox) {
    hintBox.classList.toggle("hidden", detailOpen);
  }
  if (detailBox) {
    detailBox.classList.toggle("hidden", !detailOpen);
    if (detailOpen) {
      detailBox.innerHTML = currentSection
        ? `<div class="onboarding-detail-line"><strong>${currentSection.label}:</strong> ${currentSection.description}</div>`
        : "";
      step.sections.forEach((section, index) => {
        const targets = getSectionTargets(section);
        targets.forEach((target) => {
          target.dataset.onboardingSection = String(index);
          if (shouldHighlightTutorialSection({ tabKey: step.tabKey, sectionLabel: section.label })) {
            target.classList.add("tutorial-section-target");
          }
          if (index === currentSectionIndex) {
            if (shouldHighlightTutorialSection({ tabKey: step.tabKey, sectionLabel: section.label })) {
              target.classList.add("tutorial-section-focus");
            }
          }
        });
      });
    } else {
      detailBox.innerHTML = "";
    }
  }
  if (detailBtn) {
    detailBtn.classList.toggle("hidden", detailOpen);
  }
  if (leaveBtn) {
    leaveBtn.classList.toggle("hidden", !detailOpen);
  }
  if (nextBtn) {
    nextBtn.textContent = currentStepIndex === TUTORIAL_STEPS.length - 1 ? "Finish" : "Next";
  }
  if (signInBtn) {
    signInBtn.classList.toggle("hidden", currentStepIndex !== TUTORIAL_STEPS.length - 1);
  }
}

function setTutorialActive(active) {
  tutorialActive = active;
  const panel = getPanel();
  if (!panel) return;
  panel.classList.toggle("hidden", !active);

  if (!active) {
    detailOpen = false;
    clearSectionFocus();
    panel.classList.remove("onboarding-panel-right");
    document.querySelectorAll(".nav-tab").forEach((tab) => {
      tab.classList.remove("tutorial-focus");
    });
    switchPage("dashboard-page");
    setTutorialTabState("dashboard");
    return;
  }

  renderStep();
}

function exitTutorial() {
  markCompleted();
  setTutorialActive(false);
}

export function reopenOnboarding() {
  localStorage.removeItem(ONBOARDING_KEY);
  currentStepIndex = 0;
  detailOpen = false;
  currentSectionIndex = 0;
  setTutorialActive(true);
}

function bindTutorialControls() {
  if (listenersBound) return;
  listenersBound = true;

  document.addEventListener(
    "pointerdown",
    (event) => {
      if (!tutorialActive || !detailOpen) return;
      const currentStep = getStep(currentStepIndex);
      if (currentStep.tabKey !== "projects") return;

      const pullTrigger = event.target.closest?.(".pull-btn");
      if (pullTrigger) {
        event.preventDefault();
        event.stopImmediatePropagation();
        currentSectionIndex = currentStep.sections.findIndex((section) => section.label === "Pull Repository");
        renderStep();
        return;
      }

      const viewTrigger = event.target.closest?.(".view-btn");
      if (viewTrigger) {
        event.preventDefault();
        event.stopImmediatePropagation();
        currentSectionIndex = currentStep.sections.findIndex((section) => section.label === "View Project");
        renderStep();
      }
    },
    true,
  );

  document.addEventListener(
    "click",
    async (event) => {
      const tab = event.target.closest(".nav-tab");
      if (tutorialActive && tab) {
        event.preventDefault();
        event.stopImmediatePropagation();
        const tabKey = tab.dataset.tab || "";
        const stepIndex = TUTORIAL_STEPS.findIndex((step) => step.tabKey === tabKey);
        if (stepIndex >= 0) {
          currentStepIndex = stepIndex;
          detailOpen = false;
          currentSectionIndex = 0;
          renderStep();
        }
        return;
      }

      const detailBtn = event.target.closest("#onboarding-show-details-btn");
      if (detailBtn) {
        event.preventDefault();
        detailOpen = true;
        currentSectionIndex = 0;
        renderStep();
        return;
      }

      const leaveBtn = event.target.closest("#onboarding-leave-btn");
      if (leaveBtn) {
        event.preventDefault();
        detailOpen = false;
        renderStep();
        return;
      }

      if (tutorialActive && detailOpen) {
        const currentStep = getStep(currentStepIndex);
        if (currentStep.tabKey === "projects") {
          const pullTrigger = event.target.closest(".pull-btn");
          if (pullTrigger) {
            event.preventDefault();
            event.stopImmediatePropagation();
            currentSectionIndex = currentStep.sections.findIndex((section) => section.label === "Pull Repository");
            renderStep();
            return;
          }

          const viewTrigger = event.target.closest(".view-btn");
          if (viewTrigger) {
            event.preventDefault();
            event.stopImmediatePropagation();
            currentSectionIndex = currentStep.sections.findIndex((section) => section.label === "View Project");
            renderStep();
            return;
          }

          const uploadTrigger = event.target.closest("#upload-project-btn, .projects-header");
          if (uploadTrigger) {
            event.preventDefault();
            event.stopImmediatePropagation();
            currentSectionIndex = currentStep.sections.findIndex((section) => section.label === "Upload Project");
            renderStep();
            return;
          }
        }

        const sectionHost = event.target.closest("[data-onboarding-section]");
        const sectionIndex = sectionHost ? Number(sectionHost.dataset.onboardingSection || -1) : -1;
        if (sectionIndex >= 0) {
          event.preventDefault();
          event.stopImmediatePropagation();
          currentSectionIndex = sectionIndex;
          renderStep();
          return;
        }
      }

      const nextBtn = event.target.closest("#onboarding-next-btn");
      if (nextBtn) {
        event.preventDefault();
        if (currentStepIndex >= TUTORIAL_STEPS.length - 1) {
          exitTutorial();
        } else {
          currentStepIndex += 1;
          detailOpen = false;
          currentSectionIndex = 0;
          renderStep();
        }
        return;
      }

      const skipBtn = event.target.closest("#onboarding-guest-btn");
      if (skipBtn) {
        event.preventDefault();
        exitTutorial();
        return;
      }

      const closeBtn = event.target.closest("#onboarding-close");
      if (closeBtn) {
        event.preventDefault();
        exitTutorial();
        return;
      }

      const signInBtn = event.target.closest("#onboarding-signin-btn");
      if (signInBtn) {
        event.preventDefault();
        exitTutorial();
        await openLoginFlow();
      }
    },
    true,
  );
}

export function initOnboarding() {
  bindTutorialControls();
  if (localStorage.getItem(ONBOARDING_KEY) === "true") return;
  currentStepIndex = 0;
  detailOpen = false;
  currentSectionIndex = 0;
  setTutorialActive(true);
}
