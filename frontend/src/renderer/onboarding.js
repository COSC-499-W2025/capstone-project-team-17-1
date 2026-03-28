import { openLoginFlow } from "./auth.js";
import { switchPage } from "./navigation.js";
import { shouldHighlightTutorialSection, shouldPlaceOnboardingPanelRight } from "./onboardingShared.mjs";

const ONBOARDING_KEY_PREFIX = "loom_onboarding_completed_v1";

const TUTORIAL_STEPS = [
  {
    tabKey: "dashboard",
    pageId: "dashboard-page",
    title: "Dashboard",
    description: "Dashboard gives you a quick view of recent projects, health signals, activity, and system status in one place.",
    sections: [
      {
        label: "Search",
        selectors: ["#dashboard-search-input", ".dashboard-toolbar"],
        description: "Search lets you quickly narrow dashboard widgets by name while staying in the same public dashboard view.",
      },
      {
        label: "Customize",
        selectors: ["#dashboard-selection-wrapper", "#dashboard-selection-panel"],
        description: "Customize is available in private mode and lets you choose which dashboard widgets appear before going live.",
      },
      {
        label: "Most Used Skills",
        selector: "#most-used-skills",
        description: "Most Used Skills summarizes the tools and languages that appear most often across your analyzed projects, and now supports switching between Bar and Pie views.",
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
    tabKey: "resume",
    pageId: "resume-page",
    title: "Resume",
    description: "Resume lets you manage your saved resumes and view the one-page resume snapshot built from your portfolio data. In Public Mode you can preview, export, and delete, while editing is only available in Private Mode.",
    sections: [
      {
        label: "My Resumes",
        selectors: [".resume-manager-card"],
        description: "Browse your saved resumes. Public Mode supports preview, export, and delete, while editing and deeper changes require Private Mode.",
      },
      {
        label: "New Resume",
        selectors: ["#new-resume-btn"],
        description: "New Resume opens the project picker so you can choose which projects to include when generating a resume.",
      },
      {
        label: "Preview",
        selectors: [".resume-preview-action"],
        description: "Preview opens a formatted resume preview for the selected resume without entering edit mode.",
      },
      {
        label: "Export",
        selectors: [".resume-export-action"],
        description: "Export downloads the selected resume in supported formats such as JSON, Markdown, or PDF.",
      },
      {
        label: "Delete",
        selectors: [".resume-delete-action"],
        description: "Delete permanently removes the selected resume from Loom after confirmation.",
      },
      {
        label: "Resume Snapshot",
        selector: ".portfolio-hero-card",
        description: "Resume Snapshot condenses your education, awards, skills, and project highlights into a one-page resume view.",
      },
    ],
  },
  {
    tabKey: "portfolio",
    pageId: "portfolio-page",
    title: "Portfolio",
    description: "Portfolio showcases your top projects, skills timeline, and activity heatmap. Public Mode is view-only here, while customization, project edits, featured selection, reordering, and live preview are only available in Private Mode.",
    sections: [
      {
        label: "Top Projects",
        selector: ".portfolio-projects-card",
        description: "Top 3 Projects highlights the strongest projects in your portfolio based on analyzed depth, contribution evidence, and success details.",
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
      {
        label: "Sections",
        selectors: ["#portfolio-selection-wrapper", ".portfolio-actions"],
        description: "Selection lets you control which portfolio sections are visible in the public-facing portfolio view, and that customization is only available in Private Mode.",
      },
      {
        label: "Evidence Editing",
        selectors: [".portfolio-editor-card"],
        description: "Edit contribution and evidence text before sharing. These edits are only available in Private Mode.",
      },
      {
        label: "Project Detail Drafts",
        // Target the drafts subsection directly so tutorial copy changes when users switch within Live Preview.
        selectors: ["#live-preview-drafts-section"],
        description: "Project Detail Drafts shows the draft text you are editing in Project Portfolio Details, including portfolio blurbs, key roles, and evidence for changed projects.",
      },
      {
        label: "My Starred Projects",
        // Keep this separate from drafts so the tutorial can explain showcase content independently.
        selectors: ["#live-preview-starred-section"],
        description: "My Starred Projects shows the projects selected for your portfolio showcase. Starring, ordering, and live preview updates are only available in Private Mode.",
      },
    ],
  },
  {
    tabKey: "chat",
    pageId: "chat-page",
    title: "Ask Sienna",
    description: "Ask Sienna provides project-aware AI support for Loom workflows, code guidance, debugging, and feature questions.",
    sections: [
      {
        label: "Project Context",
        selectors: [".sienna-toolbar", "#sienna-project-select"],
        description: "Select a project first so Sienna answers with the right project context.",
      },
      {
        label: "Conversation",
        selectors: ["#sienna-conversation-card", "#sienna-messages"],
        description: "Conversation shows your ongoing chat with Sienna, including streamed responses and project-specific guidance.",
      },
      {
        label: "Message Composer",
        selectors: ["#sienna-input", ".sienna-composer"],
        description: "Message Composer is where you ask Sienna to explain Loom features, suggest improvements, or debug project issues.",
      },
      {
        label: "Send",
        selectors: ["#sienna-send-btn"],
        description: "Send submits your prompt to Sienna and appends the AI response to the conversation.",
      },
      {
        label: "Clear Chat",
        selectors: ["#sienna-clear-btn"],
        description: "Clear Chat resets the current conversation and starts you with a fresh assistant greeting.",
      },
    ],
  },
  {
    tabKey: "job-match",
    pageId: "job-match-page",
    title: "Job Match",
    description: "Job Match is only available in private mode. Paste a job description to auto-select your best matching projects.",
    sections: [
      {
        label: "Target Job",
        selectors: ["#portfolio-job-target-container"],
        description: "Enter a target role and paste a job description so the app can rank and select your best matching projects.",
      },
      {
        label: "Featured Projects",
        selectors: ["#customization-featured-card"],
        description: "After analyzing a job, the top matching projects are auto-selected here. You can also manually reorder them.",
      },
    ],
  },
  {
    tabKey: "settings",
    pageId: "settings-page",
    title: "Settings",
    description: "Settings is organized into General, Account, Privacy & Consent, and Security so you can manage app preferences and personal controls in one place.",
    sections: [
      {
        label: "General",
        selectors: ["#settings-tab-general", "#show-tutorial-btn"],
        description: "General contains app-level preferences, including the option to replay the guided tutorial at any time.",
      },
      {
        label: "Account",
        selector: "#settings-profile",
        description: "Account is where you view and update your profile details, contact information, and public links used across Loom.",
      },
      {
        label: "Privacy & Consent",
        selector: "#settings-consent",
        description: "Privacy & Consent lets you review and manage local-processing and optional external-AI permissions for the app.",
      },
      {
        label: "Security",
        selector: "#settings-security",
        description: "Security is where signed-in users manage account protection details such as password-related settings.",
      },
    ],
  },
];

let tutorialActive = false;
let currentStepIndex = 0;
let listenersBound = false;
let detailOpen = false;
let currentSectionIndex = 0;
let currentOnboardingAudience = "guest";

function getOnboardingKey(audience = currentOnboardingAudience) {
  const suffix = String(audience || "guest").trim() || "guest";
  return `${ONBOARDING_KEY_PREFIX}:${suffix}`;
}

function getPanel() {
  return document.getElementById("onboarding-panel");
}

function getStep(index) {
  return TUTORIAL_STEPS[index] || TUTORIAL_STEPS[0];
}

function markCompleted() {
  localStorage.setItem(getOnboardingKey(), "true");
}

function hasCompletedOnboarding(audience = currentOnboardingAudience) {
  return localStorage.getItem(getOnboardingKey(audience)) === "true";
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

function syncSettingsTutorialTab(sectionLabel) {
  const tabMap = {
    General: "general",
    Account: "account",
    "Privacy & Consent": "privacy",
    Security: "security",
  };
  const activeTab = tabMap[sectionLabel] || "general";

  document.querySelectorAll(".settings-nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.settingsTab === activeTab);
  });

  document.querySelectorAll(".settings-tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `settings-tab-${activeTab}`);
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
  if (step.tabKey === "settings") {
    syncSettingsTutorialTab(currentSection?.label || "");
  }
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
  localStorage.removeItem(getOnboardingKey());
  currentStepIndex = 0;
  detailOpen = false;
  currentSectionIndex = 0;
  setTutorialActive(true);
}

export function maybeShowOnboardingForAudience(audience = "guest") {
  currentOnboardingAudience = String(audience || "guest").trim() || "guest";
  if (hasCompletedOnboarding(currentOnboardingAudience)) return false;
  currentStepIndex = 0;
  detailOpen = false;
  currentSectionIndex = 0;
  setTutorialActive(true);
  return true;
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
      const interactiveEditorTarget = event.target.closest(
        "input, textarea, select, [contenteditable='true'], [contenteditable='']",
      );
      if (interactiveEditorTarget) {
        return;
      }

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
        if (currentStep.tabKey === "settings") {
          const settingsNavTrigger = event.target.closest(".settings-nav-item");
          if (settingsNavTrigger) {
            event.preventDefault();
            event.stopImmediatePropagation();
            const settingsTab = settingsNavTrigger.dataset.settingsTab || "";
            const sectionIndex = currentStep.sections.findIndex((section) => {
              if (settingsTab === "general") return section.label === "General";
              if (settingsTab === "account") return section.label === "Account";
              if (settingsTab === "privacy") return section.label === "Privacy & Consent";
              if (settingsTab === "security") return section.label === "Security";
              return false;
            });
            if (sectionIndex >= 0) {
              currentSectionIndex = sectionIndex;
              renderStep();
            }
            return;
          }
        }

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
}
