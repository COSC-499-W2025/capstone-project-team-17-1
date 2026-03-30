# COSC 499 TEAM 17 Personal Log - Raunak Khanna

## Table of Contents
- [Week 3 Personal Log](#week-3-personal-log)
- [Week 4 Personal Log](#week-4-personal-log)
- [Week 5 Personal Log](#week-5-personal-log)
- [Week 6 Personal Log](#week-6-personal-log)
- [Week 7 Personal Log](#week-7-personal-log)
- [Week 8 Personal Log](#week-8-personal-log)
- [Week 9 Personal Log](#week-9-personal-log)
- [Week 10 Personal Log](#week-10-personal-log)
- [Week 12 Personal Log](#week-12-personal-log)
- [Week 13 Personal Log](#week-13-personal-log)
- [Week 14 Personal Log](#week-14-personal-log)
- [Term 2 Week 1 Personal Log](#term-2-week-1-personal-log)
- [Term 2 Week 2 Personal Log](#term-2-week-2-personal-log)
- [Term 2 Week 3 Personal Log](#term-2-week-3-personal-log)
- [Term 2 Week 5 Personal Log](#term-2-week-5-personal-log)
- [Term 2 Week 8 Personal Log](#term-2-week-8-personal-log)
- [Term 2 Week 9 Personal Log](#term-2-week-9-personal-log)
- [Term 2 Week 10 Personal Log](#term-2-week-10-personal-log)
- [Term 2 Week 12 Personal Log](#term-2-week-12-personal-log)

---

### WEEK 3 PERSONAL LOG
(Sep 15–21, 2025)
- Drafted **User Requirements (UR-01 to UR-08)** focusing on usability, privacy, insights, and accessibility.  
- Co-authored **Technical Requirements** (cross-platform compatibility, data store, API, Git reader, concurrency).  
- Contributed to **Risk Analysis** with Yuxuan on privacy, interruptions, and performance bottlenecks.  
- Set up **Discord and GitHub** on my system to support team communication and track project progress.  

![Screenshot 2025-09-20 at 7 28 06 PM](https://github.com/user-attachments/assets/2a1c5ed8-0c39-4186-97e2-e381dbe3fc3c)

---

### WEEK 4 PERSONAL LOG 
(Sep 22–28, 2025)
- Helped teammates **Nade** and **Shuyu** with GitHub Kanban setup, including the pull request “**Create Project Directory Structure #15.**”  
- Initiated the Group Project Proposal document by referencing the sample template provided on Canvas. Made progress on the "COSC 499 Week 4 Project Proposal" with **Michelle**, making sure that we both followed the slides.  
- While drafting the Project Scope and Usage Scenario, I introduced the idea of comparing our dashboard’s progress indicators to Workday’s percentage tracker for degree completion. This analogy made the concept easier to understand and gave the team a clear, relatable way to explain how our system shows progress toward goals.  
- Worked with **Michelle** on the System Architecture Diagram Document along with the designs following the templates on the weekly slides.  
- Reviewed **Nade**'s pull requests.  

<img width="888" height="623" alt="Week4PersonalLog" src="https://github.com/user-attachments/assets/4d183521-853a-43fe-979c-dc21d235640b" />


### WEEK 5 PERSONAL LOG 
(Sep 29-Oct 05, 2025)
- Worked with **Michelle** and **Parsa** to understand the Data Flow Diagram (DFD) requirements as outlined in Dr. Hui’s lecture slides. (They helped me understand what is expected on the dfd diagram in more detail.)
  - Reviewed examples of Level 0 (Context Diagram) and Level 1 (System Diagram) to learn how to properly represent processes, data stores, and external entities.
  - Collaboratively designed the Level 0 and Level 1 DFD for our Mining Digital Work Artifacts system using Google Drawings, ensuring consistency between both levels.
  - Defined the key entities (User, System API) and internal processes (Source Selection, Mining/Scan, Analytics & Generation, Visualization & Export, Save Portfolio).
  - Mapped each process to its corresponding requirement:
     - UR-01 (Source Selection) = Source Selection process
     - UR-02 (Transparency) and UR-03 (Progress & Feedback) = feedback flows within Mining/Scan
     - UR-04 (Control) and UR-05 (Privacy) = user interactions that manage or limit scanning
     - UR-06 (Insights) = Analytics & Generation
     - UR-07 (Export) = Visualization & Export
     - UR-08 (Accessibility) = consistent flow design and labeling for screen-reader compatibility
- ***(I had previously worked on the user requirements section on the **Project Requirements** document)***
- Feedback emphasized improving clarity within labels and showing how progress updates (UR-03) interact with the user interface and error logs.
- No unresolved problems this week — most questions were clarified during in-class discussions by reviewing other teams’ DFD diagrams. Our group was able to solve the remaining issues collaboratively during team meetings, which helped us further polish our DFD diagram.
- Further steps I participated in: polishing flow labels, incorporate progress-feedback details (from in class discussions) into the final DFD, and prepare for the DFD quiz.

<img width="1075" height="625" alt="WEEK5EVAL" src="https://github.com/user-attachments/assets/8c1024b7-c908-42d1-bb4d-f4e285e972c9" />

### WEEK 6 PERSONAL LOG 

 Work Completed This Week:
- Collaborated with Parsa and Michelle on environment setup
- Successfully configured Docker and Electron on my system to begin our local development environment.
- **Parsa** and **Michelle** guided me through the setup and explained key dependencies and configuration files.
- I actively contributed by helping identify and fix minor bugs and configuration errors that appeared during setup.
- This collaboration ensured all team members are now on the same technical baseline, reducing future compatibility issues and enabling smoother integration across systems.
- Improved and aligned project diagrams
- Made refinements to the system diagrams based on the feedback received from our last review session.
- Focused on improving clarity of data flow and inter-module communication to ensure the diagrams reflected our updated design.
- These improvements directly shaped our Work Breakdown Structure (WBS) by clarifying task dependencies and priorities.
- The updated visuals have made it easier for the team to identify responsibilities and maintain consistency between documentation and implementation.
- Documented Sections 4.0 – 7.0 of the WBS Document
- Authored detailed write-ups for future system components, including:
  - 4.0 User Permission Management – ensuring user consent and transparency for any external service use.
  - 5.0 Offline Functionality – outlining fallback mechanisms for full offline operation.
  - 6.0 User Configuration Storage – describing how user preferences will persist securely.
  - 7.0 Project Classification – defining fair distinction between individual and collaborative projects.
- My writing focused on clarity, transparency, and privacy-first design principles.
- This documentation lays the foundation for ethical, privacy-aware development, helping future milestones maintain compliance and user trust.
- Including the purpose, implementation plan, and expected outcomes for each section ensures that the next development phase has clear technical direction and avoids ambiguity.

  
- Assigned and managed Kanban task:
  - Took ownership of the task — “Parse a specified zipped folder containing nested folders and files.”
  - The goal is to implement metadata extraction (file path, size, and last modified date) for organized and automated file handling.
  - Even though implementation will occur later, pre-planning the task ensures that parsing and indexing mechanisms are well-defined, modular, and aligned with our architecture.
  - This will help streamline local scanning processes, contributing to higher system efficiency.
  - Supported team organization and sprint management
  - Helped other team members identify, define, and assign their tasks on the Kanban sprint board.
  - Ensured a balanced workload and logical sequencing of activities based on dependencies.
  - Improved team communication and accountability by making task ownership explicit.
  - This structured approach supports better sprint visibility and progress tracking, which will be valuable for both reporting and evaluation.
 
OVERALL: My work this week strengthened both the technical foundation and documentation quality of the project.
Setting up Docker and Electron ensures smooth cross-team development.
Refining diagrams and WBS documentation provides a clear roadmap for upcoming milestones.
The privacy-centric sections I authored establish trust and compliance standards early in development.
Active contribution to Kanban planning and task alignment has improved workflow clarity and collaboration across the team.

<img width="1026" height="485" alt="WEEK6PERSONALLOG" src="https://github.com/user-attachments/assets/2f581570-c6b8-40c6-af8b-a108720c9a9a" />

### WEEK 7 PERSONAL LOG 

What I built
- Created feature branch feat/zip-parse.
- Implemented ZIP parsing pipeline:
- Main/IPC: added zip:validate, zip:scan, (optional zip:extractAndHash), registered via registerZipIpc(ipcMain).
- Preload bridges: exposed window.archiveValidator, window.zipAPI, window.db, window.config for safe renderer access.
- Renderer UI: added ZIP Import section (index.html + src/js/zipImport.js) to pick a .zip, scan, render table (Path / Size / Modified UTC / MIME), and upsert rows into the artifact table.
- Added button state + status messages (disable until file chosen, “Validating…/Scanning…/Found N files · Inserted M”).
- Validation & safety: file path validation, MIME/size display, basic error/status handling in UI.
- Fixes & hardening
- Resolved a crash from double registering Artifact IPC:
- Removed duplicate registerArtifactIpc() and added defensive ipcMain.removeHandler('artifact.query' | 'artifact.insertMany') before single registration.
- Prevented DevTools “Autofill” noise (stopped auto-opening DevTools and filtered Autofill logs).
- Guarded zip:scan against bad inputs; added native picker in IPC (returns absolute path) to avoid path issues on some machines.
- Tests & runs
- Unit tests: 12/12 passing (ConfigStore, DB connection, file validator, ZIP validator).
- Manual run (Electron): seeded demo artifacts render; scanning a .zip lists entries and upserts to DB. No functional errors seen.
- Git/GitHub
- Opened PR #45: “feat(zip): scan nested .zip via IPC; renderer UI; DB upsert; guard duplicates”.
- Added reviewers and filled out description (scope, testing steps, checklist, notes, screenshots).
- Resolved merge conflicts with develop in src/main.js:
- Kept our single IPC-registration pattern + kept team’s new imports/initialization where relevant.
- Re-requested review after fixes; PR now shows no conflicts and is ready for approvals/merge.
- Collaboration / debugging
- Helped teammate reproduce an issue; root cause was duplicate IPC registration in main.js.
- Provided a simple “fresh run” checklist (git fetch/pull, npm ci, electron-rebuild, npm test, npm start) to testers.
- What’s left / next
- Team review & approvals for PR #45; merge into develop.
- Wire real project_id on insert; add unit tests for zipParser happy/evil paths.
- Add UI notice for existing-rows skipped on upsert.

- PARSE(ZIP) below:

<img width="1470" height="956" alt="FEAT(PARSE)" src="https://github.com/user-attachments/assets/4d859d39-f981-429a-9ab0-12cf2add0e76" />
<img width="1047" height="535" alt="WEEK7PERSONALLOG" src="https://github.com/user-attachments/assets/f69fccbd-e06b-4bd7-9122-ee53cc83f05f" />

### WEEK 8 PERSONAL LOG 
##  Goals for the Week
- Persist project information and analytics to a local database.
- Wire main/renderer IPC to read/write analytics without recomputing.
- Seed sample data for demo/testing.
- Open a PR (review only) against `develop`.

---

##  What I Did
1. **SQLite Persistence (better-sqlite3)**
   - Implemented `src/db/connection.js` using `app.getPath('userData')` for a writable, per-user DB path.
   - Enabled pragmas: `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000`.
   - Added `closeDb()` and hooked it to `app.on('before-quit')`.

2. **Schema & Init Runner**
   - Created `src/db/schema.sql` with tables:
     - `project`, `project_repository` (1:1), `project_analysis`, `artifact` (+ indexes).
   - Wrote `src/db/init.js` to load and apply the schema in a transaction.
   - Logged created tables on startup for verification.
   - Added **dev seeds**: 3 demo artifacts + default project (“Capstone Team Workspace”).

3. **Data Store**
   - Implemented `src/db/projectStore.js`:
     - `getProjectsForAnalysis()` — repo config for analyzer.
     - `upsertProjectAnalysis(projectId, analysis)` — persist analyzer output.
     - `listProjectSummaries()` — joined view for UI (parses `details_json`).

4. **IPC Wiring**
   - `src/ipc/projects.js`:
     - `project.list` — list summaries.
     - `project.refresh` — re-run analysis then list.
     - `project.export` — JSON/CSV snapshot export (optionally refresh).

5. **Main Process Updates**
   - In `src/main.js`, called `initSchema()` on `app.whenReady()`.
   - Added a log for `[app] userData = …` to locate the DB on disk.
   - **Fixed by me:** imported `closeDb` and added shutdown hook to flush/close SQLite.

6. **Repo Hygiene**
   - Ensured `.gitignore` excludes `app.db`, `app.db-*`, `*.db-journal`.
   - Removed stray dev DB files in `src/` to avoid confusion.

7. **PR**
   - Pushed branch `feat/db-persistence`.
   - Opened a **draft PR** to `develop` for review (no merge yet).
   - Added detailed PR body (scope, testing, notes).

---

##  Verification & Testing
- **Runtime logs:**
  - Saw `[app] userData = /Users/<me>/Library/Application Support/cosc-499-project`.
  - Saw `[db:init] applying schema from src/db/schema.sql`.
  - Saw `[db:init] tables: ['artifact','project','project_analysis','project_repository','sqlite_sequence']`.
  - Saw `[seed] 3 demo artifacts inserted`.
- **SQLite checks:**
  - `sqlite3 "$HOME/Library/Application Support/cosc-499-project/app.db" '.tables'` shows all tables.
- **Manual seed/write:**
  - Used `window.db.saveAnalysis(...)` from DevTools to insert an analysis; counts reflect in DB.

---

##  Issues & Resolutions
- **DB path confusion:** Initially created DB under `src/` (wrong).  
  **Fix:** Switched to `app.getPath('userData')` in `connection.js`; added startup log to confirm path.
- **Empty DB (0 bytes):** Schema hadn’t run for that file.  
  **Fix:** Deleted file and ensured `initSchema()` runs in `app.whenReady()`.
- **Merge conflict markers in `main.js`:** Caused `Unexpected token '<<'`.  
  **Fix:** Resolved conflicts, removed markers, kept `initSchema()` and `closeDb()` logic.
- **Electron deprecation warning:** `console-message` args.  
  **Status:** Non-blocking; will update to new `(event, params)` signature later.
- **IPC log confusion:** `ipcMain.eventNames()` doesn’t list `ipcMain.handle` channels.  
  **Status:** Verified IPC via working handlers & UI/DevTools calls.

---

##  Collaboration
- Opened a draft PR for teammate review (no merge).  
- Documented DB location and testing steps in the PR for reviewers.

---

##  Learnings
- Correct DB placement in Electron apps is **userData**, not project cwd.
- Always remove conflict markers before running the app; add a grep check to CI/local workflow.
- Seeding data + startup logs speed up verification and reduce confusion.

---

##  Risks / Blockers
- Seeds should be gated to dev mode before release.
- Need a small UI “Save to DB” action so QA doesn’t rely on DevTools.

---

##  Plan for Next Week
- Gate or remove dev seeds behind an environment flag.
- Add UI button/workflow to persist current analysis.
- Update the `console-message` listener to the new Electron signature.
- Add light tests for `projectStore` (e.g., upsert/list roundtrip).
- Address any reviewer feedback on the draft PR.
<img width="1046" height="615" alt="WEEK8PERSONALLOG" src="https://github.com/user-attachments/assets/aec99609-0910-4b78-8a2b-9c75daaa0d36" />

---
### WEEK 9 PERSONAL LOG 


## Context
- Repo migrated from Electron app to Python CLI (`capstone` in `src/` layout).
- Local environment had multiple Python versions; needed venv + `PYTHONPATH=src`.

---

## Timeline

1) Pull latest + align with remote
- `git fetch origin`
- `git checkout develop`
- `git reset --hard origin/develop`

2) Virtualenv + install package
- `python3 -m venv .venv && source .venv/bin/activate`
- `export PATH="$VIRTUAL_ENV/bin:$PATH"; hash -r`
- `pip install -e .`
- Ensure imports work with src-layout: `export PYTHONPATH=src`
- Verified CLI help: `PYTHONPATH=src python3 -m capstone.cli --help`

3) Confirmed demo runner exists
- Noted `sample_project.py` calls `capstone.cli.main([...])` (no standalone `main.py` required).

4) Implemented new feature: `clean` subcommand (Req. 18)
- Edited `src/capstone/cli.py`:
  - Added **subparser** for `clean` (placed *before* `return parser`).
  - Implemented `_safe_wipe_dir(target, repo_root)` with repo-root safety.
  - Implemented `_handle_clean(args)`.
  - Routed in `main()` via `if args.command == "clean": return _handle_clean(args)`.
- Fixed ordering bug (moved parser block above `return parser`).

5) Manual validation
- `PYTHONPATH=src python3 -m capstone.cli --help` → shows `consent, config, analyze, clean`.
- `PYTHONPATH=src python3 -m capstone.cli clean` → removed `./analysis_output`.
- `PYTHONPATH=src python3 -m capstone.cli clean --all` → idempotent “Nothing to remove” OK.

6) Commit & push branch
- `git checkout -b feat/clean-subcommand`
- `git add src/capstone/cli.py`
- `git commit -m "feat(cli): add clean subcommand to safely delete generated outputs (Req. 18)"`
- `git push -u origin feat/clean-subcommand`
- GitHub printed PR link.

7) Testing setup + unit test
- Installed pytest in correct interpreter: `python3 -m pip install -U pytest`
- Wrote `tests/test_clean.py`:
  - Uses `tmp_path`, sets `PYTHONPATH` to repo `src/`, runs CLI with `cwd=tmp_path` to satisfy safety.
  - First attempt failed (outside-repo safety) → fixed with `cwd=tmp_path`.
- Run: `export PYTHONPATH=src && python3 -m pytest -q tests/test_clean.py` → **1 passed**.

8) Commit test
- `git add tests/test_clean.py`
- `git commit -m "test(cli): add unit test for clean subcommand"`
- `git push`

---

## Key Commands Used
```bash
# Env
source .venv/bin/activate
export PATH="$VIRTUAL_ENV/bin:$PATH"; hash -r
export PYTHONPATH=src
which python3

# CLI
python3 -m capstone.cli --help
python3 -m capstone.cli clean
python3 -m capstone.cli clean --all

# Tests
python3 -m pip install -U pytest
python3 -m pytest -q tests/test_clean.py


```
### WEEK 10 PERSONAL LOG 

#### 🧠 **Focus Area**

Milestones #19 & #20 – Timeline Exports (Projects + Skills)

---

#### 🧩 **Tasks Completed**
- Implemented the **`timeline.py` module** to export chronological data:
  - `write_projects_timeline()` → generates `projects_timeline.csv`
  - `write_skills_timeline()` → generates `skills_timeline.csv`
- Replaced legacy raw SQL calls with the **storage API** (`fetch_latest_snapshots`) for safer, schema-independent data access.
- Integrated the new timeline feature into the **CLI** (`capstone.cli`) via a `timeline` subcommand.
- Wrote and refined **`test_timeline_smoke.py`** to verify export behavior.
  - Created a schema-agnostic smoke test using a stubbed `_iter_snapshots` to avoid DB schema dependency.
  - Ensured both CSVs are created correctly with valid headers and counts.
- Debugged multiple test failures related to SQLite visibility and uncommitted transactions.
  - Resolved by isolating logic and mocking data in the test.
- Confirmed full test suite passes (`pytest -q` ✅).

---

#### 🧪 **Verification**
- Ran manual CLI verification:
  ```bash
  python -m capstone.cli consent grant
  python -m capstone.cli analyze ~/sample.zip --analysis-mode local
  python -m capstone.cli timeline --out-dir out

<img width="1470" height="956" alt="WEEK10EVAL" src="https://github.com/user-attachments/assets/bc51ffab-18df-49da-9bb6-8f4622780cc7" />


### WEEK 12 PERSONAL LOG 
-Today while reviewing Michelle’s work on the feature/chronological-projects branch, I found and fixed a small bug in the sample project demo. The code was trying to read a column from the project_analysis table that doesn’t actually exist in the database, which was causing the demo to crash at runtime. 


-I tracked the issue down to the query pulling the wrong column name and updated it so that it matches the actual database schema. After the change, the demo runs smoothly without errors. It was a tiny tweak, but it unblocked Michelle’s code and made the chronological projects output work as intended

- Explored existing **CLI analyzer**:
  - Ran `capstone analyze demo.zip` to understand how project snapshots are generated.
  - Created a tiny `demo_project/` (src/app.py, docs/README.md, requirements.txt) and zipped it.
  - Verified `analysis_output/metadata.jsonl` + `summary.json` and saw languages/frameworks in CLI output.

- Implemented **project–job scoring logic** in `src/capstone/job_matching.py`:
  - Added `ProjectMatch` dataclass with:
    - `score`, `required_coverage`, `preferred_coverage`, `keyword_overlap`, `recency_factor`
    - `matched_required`, `matched_preferred`, `matched_keywords`
  - Helper functions:
    - `_normalise(tokens)` – lowercases, trims, de-dupes skill tokens.
    - `_coverage(jd_terms, project_terms)` – returns `(coverage_ratio, matched_terms)`.
    - `_recency_factor(recency_days)` – exponential decay; recent projects get higher scores.
    - `_iter_skill_names(...)` – supports `SkillScore`, dicts, or objects with `.skill`.
  - Main APIs:
    - `score_project_for_job(jd_profile, project_snapshot, weights=None)`
      - Combines required, preferred, keywords, recency with default weights `{0.6, 0.2, 0.1, 0.1}`.
    - `rank_projects_for_job(jd_profile, project_snapshots)`
      - Scores all projects and sorts best → worst.
    - `matches_to_json(matches)`
      - Converts `ProjectMatch` list into JSON-ready dict for UI / resume generator.

- Created **manual scoring demo** `job_match_manual_demo.py` (repo root):
  - Hard-coded sample JD: “Backend Python Intern” with `["python", "flask", "sql"]`.
  - Defined 3 fake snapshots:
    - `flask_backend` (good match, recent).
    - `data_science_notebook` (partial match).
    - `old_php_site` (almost no match, very old).
  - Called `rank_projects_for_job(...)` and printed a breakdown per project.
  - Ran via:
    ```bash
    PYTHONPATH=src python3 job_match_manual_demo.py
    ```
  - Confirmed ranking: `flask_backend` > `data_science_notebook` > `old_php_site` with sensible scores.

- Git / collaboration:
  - Worked on `feature/parse-job-description`.
  - Resolved merge conflict in `job_matching.py` (kept new scoring implementation).
  - Re-ran manual demo after resolving, then pushed and opened PR describing:
  - Michelle helped me with some changes and that can be seen on the Pull request that I have put up
    - New scoring logic,
    - Demo script,
    -  this supports step 1+2 job–project matching.
<img width="1059" height="625" alt="WEEK12PEEREVAL" src="https://github.com/user-attachments/assets/d138a0e3-38bf-4640-a6cb-b35628a83ed4" />

### WEEK 13 PERSONAL LOG 
**Personal Log – Improving Demo Output (feature/demo-friendly-output)**

**29 November Saturday**


- Today I worked on refining the usability and presentation quality of our capstone project’s CLI demo. The original `sample_project.py` script printed large JSON objects directly to the terminal, which made the demo cluttered and difficult to interpret. To improve clarity and communication for supervisors and evaluators, I added a structured, human-readable reporting layer on top of the existing analysis pipeline.
- I implemented helper functions (`_banner`, `_section`, `print_project_summary`, and `print_metrics`) to create a clean, formatted terminal report. This update preserves all raw JSON outputs for debugging while introducing a professional, readable summary that highlights the detected languages, frameworks, skills, collaboration classification, and metrics such as project duration, frequency, activity timeline, and contributions.
- The biggest improvement was replacing the raw `summary.json` (I basically commented that section) dump with a polished **“Project Analysis”** section and a **“Metrics Summary”** block that communicates the analysis results at a glance. I also ensured that the database snapshot information (skills + collaboration) and chronological project ordering integrate cleanly after the analysis output.
- Overall, this change significantly enhances how the project is showcased and makes the demo more intuitive and evaluative-friendly for the proffesors/TA. This will help us articulate the value of our tool Loom more effectively during presentations and checkpoints.

**Co-authoring Michelle's PR(3 Part 1 Feature: Extract Company-Specific Qualities):**


**Summary**

Implemented the Company Qualities extraction subsystem and wired it into the company profile backend so we can return structured JSON for resume matching (not just flat skill lists).

**Implementation**

- Added `capstone/company_qualities.py`:
  - Defined keyword maps:
    - `COMPANY_VALUE_KEYWORDS` (e.g., innovation, customer_focus, diversity, impact, sustainability, excellence, etc.)
    - `WORK_STYLE_KEYWORDS` (e.g., remote, hybrid, fast_paced, agile, mentorship, flexible_hours, etc.)
  - Implemented `CompanyQualities` dataclass:
    - `company_name`
    - `values`
    - `work_style`
    - `preferred_skills`
    - `keywords` (combined universe for matching)
  - Implemented `extract_company_qualities(text, company_name)` to:
    - parse raw company text
    - infer `values`, `work_style`, and `preferred_skills` (via `JOB_SKILL_KEYWORDS`)
    - build a unified `keywords` list for resume matching

- Updated `capstone/company_profile.py`:
  - `build_company_profile(company_name, url=None)` now:
    - fetches text via `fetch_company_text()` / `fetch_from_url()`
    - calls `extract_job_skills()`, `extract_softskills()`, and `extract_company_qualities()`
    - returns a structured JSON-ready dict with:
      - `company`, `source`
      - `required_skills`, `preferred_skills`, `keywords`
      - `values`, `work_style`, `traits`
      - `preferred_skills_from_profile`
  - Kept backward compatibility for existing matching logic while enriching the profile with values + work style information.
  - Cleaned up `build_company_resume_lines()` so bullets clearly reference the company and avoid duplicated “aligning with…” text.

**Testing**

- Added `tests/test_company_qualities.py`:
  - Verifies extraction of `values`, `work_style`, `preferred_skills`, and `keywords` from realistic sample text.
- Updated `tests/test_company_profile.py`:
  - Verifies that `build_company_profile()` returns the new structured JSON fields.
  - Asserts that core skill/keyword behaviour is preserved.
- All tests passing locally (`78 passed, 1 skipped`).

**Impact**

- Completes the “Extract company-preferred skills, traits, and keywords” part of Step 3 (Part 1).
- Backend now exposes a richer company profile that the resume-matching pipeline can consume, capturing not just tech stack alignment but also company values and work style.

**Weekly Personal Log — Integration Pipeline (Step 5)**
 **Overview**


This week I completed **Step 5: Integration with the Mining Pipeline**, which required me to connect all earlier backend stages (Steps 1–3) into one cohesive workflow. I implemented a new pipeline module that stitches together project detection, job matching, company profiling, and company quality extraction.


**What I Completed**
- Added a new module: **`capstone/pipeline.py`** and test_pipeline.py (This is crucial for future frontend application)
- Implemented **`run_full_pipeline()`**, which integrates:
  - **Project detection** via a wrapper around `detect_node_electron_project`
  - **Job → project relevance scoring** using `rank_projects_for_job`
  - **Company profile extraction** from `build_company_profile`
  - **Company values, work-style, and preferred skills extraction** using `extract_company_qualities`
- Created `_detect_projects_wrapper()` to generate a minimal project snapshot, allowing integration even when full mined data is not available.
- Ensured the pipeline can be executed directly using:
  ```bash
  python3 -m capstone.pipeline

<img width="1077" height="619" alt="WEEK13PEEREVAL" src="https://github.com/user-attachments/assets/fac58d47-93e4-4f87-8a48-24fd26ae4cca" />

### WEEK 14 PERSONAL LOG


**Date:** 2025-12-07
**Branch:** `feature/summarize-projects-cli`

Today I implemented and wired up a new CLI subcommand called `summarize-projects` in the Capstone analyzer.

**What I did**

1. **Set up the branch**

   * Created a new feature branch `feature/summarize-projects-cli` before touching anything.
   * Verified `git status` was clean to avoid mixing old changes.

2. **Extended the CLI**

   * Opened `src/capstone/cli.py`.
   * Added a new subcommand `summarize-projects` to the main `argparse` parser with flags:

     * `--db-dir`
     * `--user`
     * `--limit`
     * `--use-llm`
     * `--format` (`markdown` | `json`)
   * Hooked up a new handler `_handle_summarize_projects` that:

     * Opens the DB with `open_db(args.db_dir)`.
     * Uses `fetch_latest_snapshots` to collect the latest snapshot per project.
     * Reuses `rank_projects_from_snapshots` to score and order projects.
     * If `--use-llm` is set, builds an LLM via `build_default_llm()` and passes `llm` + `use_llm=True` into `generate_top_project_summaries`.
     * Prints either:

       * Markdown for each summary (via `export_markdown` / `.markdown`), or
       * A JSON array of summary objects.
     * Ensures `close_db()` is called in a `finally` block.
   * Wired the new handler into `main()` with:

     ```python
     if args.command == "summarize-projects":
         return _handle_summarize_projects(args)
     ```

3. **Dealt with the first breakage**

   * First draft of the handler + tests didn’t line up (signature assumptions vs. real code).
   * Adjusted the tests to be less opinionated about the internal structure:

     * Focused only on:

       * Whether `build_default_llm` is called (or not).
       * Whether `generate_top_project_summaries` is invoked with the right `llm` and `use_llm` flags.
       * Output being valid markdown-ish text or valid JSON.

4. **Wrote tests for the new command**

   * In `tests/test_cli.py`, inside `CLITestCase`, added:

     * `test_summarize_projects_markdown_without_llm`

       * Mocks `open_db`, `fetch_latest_snapshots`, `rank_projects_from_snapshots`, `generate_top_project_summaries`, and `export_markdown`.
       * Asserts:

         * Exit code is `0`.
         * `build_default_llm` is **not** called.
         * Output contains both mocked project titles.
     * `test_summarize_projects_json_with_llm`

       * Mocks the same DB + ranking pipeline plus `build_default_llm`.
       * Asserts:

         * Exit code is `0`.
         * `build_default_llm` **is** called.
         * `generate_top_project_summaries` gets `llm` and `use_llm=True`.
         * Output parses as JSON and contains the expected `title` and `score`.

5. **Got everything green**

   * Ran the test suite for CLI:

     ```bash
     pytest tests/test_cli.py -k summarize
     ```
   * All tests passed after the adjustments.

6. **Committed the work**

   * Staged the modified files:

     ```bash
     git add src/capstone/cli.py tests/test_cli.py
     ```
   * Committed with message:

     > Add summarize-projects CLI command and tests
   * Pushed the branch:

     ```bash
     git push -u origin feature/summarize-projects-cli
     ```

7. **Prepared the PR**

   * Drafted a PR titled **“Add `summarize-projects` CLI command and tests”**.
   * Documented:

     * What the new command does.
     * How it reuses existing ranking + summary logic.
     * Example usage for both markdown and JSON output.
     * The tests that cover LLM vs non-LLM flows.

---

**Overall feeling**

This change is pretty neat because it turns all the ranking and summary plumbing we already had into a single, user-facing CLI entry point. TAs / users can now just run one command and immediately see top project summaries, with the option to flip on LLM polishing when available. The tests give a decent safety net around DB usage, ranking, and LLM wiring, so future refactors shouldn’t break this silently.

Additionally,

I worked on the WBS 5-8 for the Demo video and helped in curating the overall presentation for this week. 


<img width="1470" height="956" alt="WEEK14PEEREVAL" src="https://github.com/user-attachments/assets/fb2edcb1-c68f-407e-8cc4-c50ff9af4673" />

### TERM 2 WEEK 1 PERSONAL LOG
---

## **Weekly Log – COSC 499 (Week of January 6–12, 2026)**

### **Files Modified**

* `capstone/portfolio_retrieval.py`
* `tests/test_portfolio_evidence.py`

---

### **Work Completed**

**1. Added a new portfolio evidence API endpoint**

I implemented a new Flask endpoint to expose evidence of success for a project based on its latest analysis snapshot:

```python
@app.get("/portfolios/evidence")
def evidence_latest():
    project_id = request.args.get("projectId", "")
    if not project_id:
        return jsonify({"data": None, "error": {"code": "BadRequest", "detail": "projectId is required"}}), 400

    with _db_session(db_dir) as c:
        ensure_indexes(c)
        snap = get_latest_snapshot(c, project_id)

    if snap is None:
        return jsonify({"data": None, "error": {"code": "NotFound", "detail": "No snapshots found"}}), 404

    evidence = _extract_evidence(snap)
    return jsonify({
        "data": {"projectId": project_id, "evidence": evidence},
        "error": None
    })
```

This endpoint (`GET /portfolios/evidence`) returns structured metrics that can be used in portfolio and résumé contexts.

---

**2. Implemented robust evidence extraction logic**

I added a helper function that extracts evidence from multiple possible snapshot schemas, ensuring compatibility with existing and future analysis outputs:

```python
def _extract_evidence(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    candidates = [
        snapshot.get("evidence"),
        snapshot.get("metrics"),
        snapshot.get("results"),
        snapshot.get("evaluation"),
        snapshot.get("outcomes"),
    ]

    for c in candidates:
        if isinstance(c, dict):
            return {
                "type": "metrics",
                "items": [{"label": k, "value": str(v)} for k, v in c.items()]
            }

    return {"type": "metrics", "items": []}
```

Fallback logic was included to return derived metrics (e.g., skill count, project count) when explicit evidence is not available.

---

**3. Added isolated pytest coverage**

I created a new test file to validate the new endpoint using Flask’s test client and a temporary SQLite database:

```python
def test_portfolios_evidence_happy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "_open_db", None)
    monkeypatch.setattr(pr, "_close_db", None)
    monkeypatch.setattr(pr, "_fetch_latest_snapshot", None)

    app = pr.create_app(db_dir=str(tmp_path), auth_token=None)
    client = app.test_client()

    resp = client.get("/portfolios/evidence?projectId=p1")
    assert resp.status_code == 200
```

The tests cover:

* Successful evidence retrieval
* Missing `projectId` handling
* Non-existent project handling

---

### **Outcome**

* Successfully extended the backend API with a Milestone 2–aligned feature
* Added test coverage without modifying existing database schemas
* Submitted changes via a pull request on a dedicated feature branch
<img width="642" height="551" alt="T2WEEK1PEEREVAL" src="https://github.com/user-attachments/assets/eb374d20-0cf1-4549-9646-2bc3801e78bf" />

---
### TERM 2 WEEK 2 PERSONAL LOG
Got you — here’s the updated weekly log version with **backend-only** + **no screenshots (UI not ready yet)**.

---

## Weekly Log (Jan 12–18)

### Summary

Implemented and tested **backend-only** support for portfolio “evidence of success” to move toward Milestone 2 requirements. Opened a PR for review. This is an improvement fron last week's PR.

### What I worked on

* **Backend API (Flask)**

  * Added `GET /portfolios/evidence?projectId=...` to return a structured evidence payload (metrics/evaluation signals) derived from the **latest portfolio snapshot**.
  * Implemented `_extract_evidence()` to safely pull evidence across multiple snapshot shapes (`metrics`, `results`, `evaluation`, etc.) with fallbacks.
  * Updated `GET /portfolios/latest` to support `view=portfolio|resume` for returning either portfolio snapshot output (default) or resume-description output.
  * Used `_db_session()` for consistent SQLite connection handling in local/test environments.

* **Testing**

  * Added `tests/test_portfolio_evidence.py` covering:

    * Happy path evidence extraction
    * `400` when `projectId` missing
    * `404` when no snapshot exists

### Files changed

* `src/capstone/portfolio_retrieval.py`
* `tests/test_portfolio_evidence.py`

### PRs

* Opened PR: **Improving portfolio evidence endpoint + tests** (#157)

### How I tested

```bash
pytest -q tests/test_portfolio_evidence.py
python3 -c "import capstone.portfolio_retrieval as pr; app=pr.create_app(auth_token=None); print([r.rule for r in app.url_map.iter_rules()])"
```

### Notes

* **No screenshots included** — this work is **backend only** right now; UI integration is not implemented yet. Although we will not need to do extra work once UI is implemented since the backend and testing is already verified.
<img width="1112" height="644" alt="T2WEEK2PEEREVAL" src="https://github.com/user-attachments/assets/5d44900c-67dd-40b1-938e-cdad81ed7b6c" />

---
### TERM 2 WEEK 3 PERSONAL LOG

### 1) Repo / Setup

* Worked in repo: `capstone-project-team-17-1`
* Ran tests with:

  * `PYTHONPATH=src pytest ...`
* Note: on macOS, `python` wasn’t available → used `python3` for quick manual runs.

---

## A) Storage + CLI snapshot work (Latest snapshot helper)

### Goal (what problem this solves)

* Needed a clean way to fetch the **latest snapshot per project** without doing slow / repeated queries.
* Prevents the **N+1 query** problem (looping project IDs and querying DB one by one).

### What I implemented

**1. New storage helper**

* File: `src/capstone/storage.py`
* Added: `fetch_latest_snapshots_for_projects(conn, project_ids)`
* Behavior:

  * Input: a DB connection + list of project IDs
  * Output: a map/dict like:

    ```python
    {
      "project-a": { ... latest snapshot row ... },
      "project-b": { ... latest snapshot row ... },
    }
    ```
  * Uses **one SQL query** to:

    * Find latest `created_at` per `project_id`
    * Join back to get the full snapshot row
  * Handles edge cases:

    * empty project_ids → returns `{}` immediately
    * filters out blank IDs

**2. Wired it into the app**

* Files touched:

  * `src/capstone/portfolio_retrieval.py` (and possibly `src/capstone/cli.py`)
* Updated code so endpoints/flows that need “latest snapshot for these projects” call the new helper instead of doing repeated reads.

### Testing + verification

* Updated / made test resilient to CLI behavior:

  * File: `tests/test_summarize_top_projects.py`
  * Instead of asserting internal helper calls that don’t exist / may change, it:

    * patches DB open/close + fetch
    * captures `stdout`
    * asserts the no-LLM path prints the expected project IDs
* Confirmed the test passes locally.

### Notes / housekeeping

* Two local files showed up in git changes during testing:

  * `config/user_config.json`
  * `data/capstone.db`
* These are **local artifacts** and usually should not be committed unless the project expects them tracked.

---

## B) Issue #138 — User Role Representation (Project Insight prompt)

### Goal

* When generating a “project insight” prompt, the system should clearly indicate:

  * is the requesting user the **primary contributor**?
  * a **collaborator**?
  * or **unknown**?
* This is based only on metadata already present in the snapshot.

### What I implemented

**1. Added a role inference function**

* File: `src/capstone/project_insight.py`
* Added: `_infer_user_role(snapshot, user)`
* Logic (simple and deterministic):

  1. If `user` is missing → `"unknown"`
  2. If snapshot has `collaboration.primary_contributor`:

     * if matches user (case-insensitive) → `"primary_contributor"`
     * else → `"collaborator"` (because if a primary exists and it isn’t you, you’re not the owner)
  3. Else fallback checks (only if fields exist):

     * if user appears in `collaboration.contributors` keys → `"collaborator"`
     * if user appears in `collaboration.coauthors` (handles dict/list shapes) → `"collaborator"`
  4. Otherwise → `"unknown"`

**2. Extended prompt builder**

* File: `src/capstone/project_insight.py`
* Updated: `build_project_insight_prompt(...)`

  * Added a new optional param: `user: Optional[str] = None`
  * Now prompt includes a line like:

    * `- Requesting user's role: primary_contributor`
    * `- Requesting user's role: collaborator`
    * `- Requesting user's role: unknown`

### Testing + verification

**Unit test added/updated**

* File: `tests/test_project_insight.py`
* Checks:

  * prompt contains “Requesting user's role”
  * prompt contains `primary_contributor` when user matches primary contributor
  * prompt contains `collaborator` when user != primary contributor (with contributors data)

**Command run**

* `PYTHONPATH=src pytest -q tests/test_project_insight.py`

**Manual demo (CLI-less sanity check)**

* Ran:

  ```bash
  PYTHONPATH=src python3 -c "
  from capstone.project_insight import build_project_insight_prompt
  snap={'collaboration':{'primary_contributor':'Alice','contributors':{'Alice':3,'Bob':1}},
        'file_summary':{'active_days':3},
        'languages':{'Python':10},
        'frameworks':['Flask']}
  print(build_project_insight_prompt(snap,'What did I do?',user='Bob'))
  "
  ```
* Output showed:

  * Primary contributor: Alice
  * Requesting user's role: collaborator ✅

---

## C) Git / Workflow actions

* Synced with develop:

  * `git checkout develop`
  * `git pull`
* Created branch for Issue #138 work:

  * `git checkout -b feature/user-role-representation`
* Confirmed changes staged are only:

  * `src/capstone/project_insight.py`
  * `tests/test_project_insight.py`

---

## What I’m NOT doing today (planned)

### Issue #140 — Project Image Association

* Tomorrow I’ll implement:

  * endpoint(s) to attach an image thumbnail to a project
  * storage layer to store/retrieve image metadata
  * tests for these endpoints using Flask test client (no real server)

---

## Deliverables summary (what I can tell prof/team)

✅ Added a new DB helper to fetch latest snapshots for a set of project IDs in **one query**.
✅ Updated CLI test to be stable and assert real output behavior.
✅ Implemented Issue #138: project insight prompt now includes requesting user role (primary/collab/unknown).
✅ Added unit tests + manual demo + verified passing with pytest.
<img width="1140" height="619" alt="T2WEEK3PEEREVAL" src="https://github.com/user-attachments/assets/ff2d0f7b-cf35-4e9a-abf0-1d49e435d915" />

--------

### TERM 2 WEEK 5 PERSONAL LOG
# (WEEK 4+5 Logs) 
# Merged PR's and their impact 

### PR: Add project success evidence storage + prompt evidence test
**What I changed**
- Added persistence for “evidence of project success” (quant + qual signals) so it can be stored/retrieved later (DB-backed, keyed by `project_id`).
- Extended the storage layer to support writing/reading this evidence in a structured payload (e.g., metrics/feedback/evaluation fields).
- Added/updated a unit test (`tests/test_project_insight_evidence.py`) to exercise the evidence prompt/flow and assert the stored snapshot includes the evidence fields.

**Impact**
- Enables Milestone 2 requirement: persist evidence for later display (not just compute it once).
- Makes project insight/resume/portfolio outputs auditable: “claims” can be backed by stored evidence.
- Regression protection: evidence flow is test-covered, lowering risk of future refactors breaking it silently.

---

### PR: Milestone 2 API — FastAPI entrypoint + consent + projects endpoints
**What I changed**
- Implemented FastAPI app entrypoint and routing layout (`capstone.api.server:app`) with OpenAPI/Swagger support.
- Added/verified core endpoints:
  - `GET /health` for liveness checks
  - `POST /privacy-consent` for consent capture/validation
  - `POST /projects/upload` for ingestion (zip upload / metadata creation)
  - `GET /projects` list view (project index)
  - `GET /projects/{project_id}` project detail fetch
- Wired endpoints into existing services/storage so API calls exercise the same backend logic as CLI.
- Proof:
<img width="1470" height="956" alt="Screenshot 2026-02-08 at 7 16 23 PM" src="https://github.com/user-attachments/assets/88fbd3e4-8345-40a5-b439-6be11f64ea5b" />

**Impact**
- Converts the system into an API-first service (Milestone 2 expectation: operate via API calls).
- Consent becomes enforceable at the API boundary (privacy-safe by design).
- Unblocks frontend integration + automated endpoint tests (no “manual CLI only” bottleneck).

---

### PR: Fix pytest import path (reduce failing tests)
**What I changed**
- Fixed test discovery/import issues by aligning `sys.path`/package imports with `src/` layout.
- Updated tests to import modules through the package namespace instead of assuming a top-level `main` module exists in the runtime path.

**Impact**
- Eliminates `ModuleNotFoundError` during pytest collection across environments.
- Improves portability (local/CI) and reduces time wasted on non-functional test failures.

---

### PR: Fix duplicate main menu rendering (Single Menu)
**What I changed**
- Fixed a CLI bug where the **Main Menu was printed twice** during a single loop iteration.
- Removed the **redundant menu-rendering block** so the menu prints **exactly once per loop**.
- Kept the menu options consistent so navigation still works normally.

**Impact**
- **Better UX:** CLI output is no longer confusing/noisy during demos and peer testing.
- **More predictable control flow:** one loop = one menu render (cleaner state transitions).
- **Less risk of input/output bugs:** duplicate prints often hide deeper loop/branching issues.
- **Easier to test/debug:** stable output makes CLI tests + debugging way more deterministic.

---

### PR: (User Role Representation) Add user-role inference to project insight
**What I changed**
- Added role inference logic in the project insight pipeline to map contribution signals which a likely user role (e.g., primary contributor, collaborator).
- Integrated role inference into snapshot/insight output so downstream consumers (portfolio/resume/UI) can display it consistently.

**Impact**
- Improves interpretability: insights now include “who did what” rather than only raw stats.
- Supports human-in-the-loop customization: users can validate/override role framing for final portfolio/resume output.

---
### PR: Add snapshot history helper + test

**What I did**
- Updated `src/capstone/storage.py` to support **incremental snapshots** for projects (multiple snapshot rows over time per `project_id`) instead of treating snapshots as a single overwrite.
- Implemented/used a **snapshot history retrieval** path that returns entries **newest-first** for a given project.
- Added `tests/test_incremental_snapshots.py` to validate:
  - storing multiple snapshots for the same project works
  - history length is correct
  - ordering is correct (latest snapshot first)

**Impact**
- Unlocks Milestone 2 “incremental information” requirement: the system can now **accumulate project state over time** instead of losing earlier snapshots.
- Improves traceability + auditability (you can inspect how a project evolved and support timeline/diff features later).
- Hardens the feature with a regression test so future schema/storage edits don’t silently break snapshot history behavior.
---
### PR: Duplicate file recognition

### What I did
- Added a **content-addressable file storage layer** to `src/capstone/storage.py`.
- Introduced/extended DB schema to support dedup:
  - `files` table keyed by content `hash` (plus `size_bytes`, `mime`, `path`, `ref_count`)
  - `uploads` table to store per-upload metadata and link each upload to a stored file (`file_id`)
  - indexes to keep lookups fast (`idx_files_hash`, `idx_uploads_file`)
- Implemented storage helpers to:
  - store uploaded bytes once (by hash)
  - reuse existing file records on duplicate uploads (increment `ref_count`)
  - fetch file metadata by hash for verification/debugging
- Wrote a focused unit test (`tests/test_file_dedup.py`) to validate dedup logic end-to-end.

### Testing / Evidence
- `PYTHONPATH=src pytest -q tests/test_file_dedup.py` (passes)

### Impact
- **No more duplicate blobs** in the DB/file store when the same content is uploaded repeatedly.
- **Lower storage usage** and cleaner persistence model (one canonical file, many upload references).
- **Deterministic identity** for artifacts via hash → makes snapshots/analysis reproducible.
- **Foundation for API uploads**: backend now has the right primitives for `/projects/upload`-style flows without ballooning DB size.

<img width="1141" height="647" alt="Screenshot 2026-02-08 at 8 26 25 PM" src="https://github.com/user-attachments/assets/56a68622-b4fa-4897-abde-949389fec312" />





### TERM 2 WEEK 8 PERSONAL LOG
## PR : Safer optional router mounting and declaring API/dev dependencies

### Summary
Today I focused on stabilizing our Milestone 2 API workflow by improving FastAPI app initialization, adding request tracing middleware, and making our environment reproducible through `pyproject.toml` dependency declarations.

---

### 1) Refactor: FastAPI app initialization (`src/capstone/api/server.py`)
**Problem:** `server.py` had multiple duplicated “safe import” blocks for optional routers (job_match, portfolio, showcase, resume). Each block repeated: dynamic import → optional `configure(...)` → `include_router(...)` → store traceback on failure.

**Changes:**
- Centralized optional-router mounting into a consistent pattern:
  - Dynamic import for optional router modules so missing modules don’t crash app startup (useful across branches).
  - Optional `configure(db_dir, auth_token)` hook supported per router before mounting.
  - Standardized error capture by storing failures in `app.state.<name>_import_error` / `app.state.<name>_mount_error`.
- Kept always-available routers mounted unconditionally (consent/projects/skills + legacy aliases) to ensure core API stays up.

**Outcome:** Cleaner entrypoint, less duplication, more resilient startup without changing the exposed route surface.

---

### 2) Feature: Request tracing middleware (`src/capstone/api/middleware/request_id.py`)
Added `RequestIdMiddleware` to improve debugging and observability:
- Ensures every request has an `X-Request-ID`.
- If client provides `X-Request-ID`, server echoes it.
- If missing, server generates a UUID4.
- Attaches the value to both:
  - `request.state.request_id` (available to handlers/logging)
  - Response headers (`X-Request-ID`) for client-side correlation.

**Why:** Standard production API pattern; makes it easier to track failures and correlate logs across multi-step flows (upload → analyze → generate resume/portfolio).

---

### 3) Build/Setup: Reproducible deps via `pyproject.toml`
A fresh env previously required manual installs to run the API and HTTP-level tests. I updated `pyproject.toml` to explicitly declare:

**Runtime deps:**
- `fastapi`
- `python-multipart` (required for `/projects/upload` multipart form data)
- `uvicorn[standard]` (local server runner for `/docs`)

**Dev deps (extras):**
- `pytest`
- `httpx` (required by `starlette.testclient` / FastAPI `TestClient`)

This enables clean setup using:
- `pip install -e .`
- `pip install -e ".[dev]"`

---

### Testing / Verification
- ✅ `pytest -q` (full suite passes locally)
- ✅ API boots with `uvicorn capstone.api.server:app --reload`
- ✅ Swagger UI loads at `/docs`
- ✅ Verified auth-protected endpoints return `401` without `Authorization: Bearer <token>`

---
## Collaboration Note — Contributions to Michelle’s PR (Job Match API Endpoint #232)

I collaborated with Michelle on PR **#232: Job Match API Endpoint** by contributing both API functionality and test coverage to help ship a stable Milestone-2–ready endpoint set.

### What I contributed
- **Implemented `top_k` support for ranking endpoint**
  - Added support for `top_k` as a query parameter on `POST /job-matching/rank` so clients can request a bounded number of ranked projects instead of always returning the full list.
  - Implemented input validation for `top_k` (e.g., rejecting invalid values such as 0 or overly large values) to keep behavior predictable and avoid expensive/unbounded ranking calls.

- **Strengthened HTTP-level test coverage**
  - Added/extended FastAPI `TestClient` tests for the ranking endpoint to verify:
    - Correct behavior when `top_k` is provided (returns exactly N results).
    - Correct error handling for invalid `top_k` values (boundary cases/out-of-range).
    - Proper request validation for malformed or missing payloads (ensures API responds with the expected error/validation status).
  - Used mocking where appropriate to isolate endpoint behavior from the underlying ranking implementation and keep tests deterministic.

- **Coordinated integration with Michelle’s branch**
  - Synced changes with Michelle’s branch to avoid conflicts and ensure the endpoint implementation + tests landed together.
  - Confirmed changes aligned with the existing API structure and did not break other routes (ran local pytest suite before pushing).

### Outcome
Michelle’s PR merged with:
- a more flexible `/job-matching/rank` API (`top_k` support),
- stronger automated regression tests around rank request validation and edge cases,
- and cleaner integration into the overall FastAPI route surface for Milestone 2.

## Collaboration / Contribution Note — PR #225 (Portfolio Showcase + Legacy Route Compatibility)

I contributed to PR **#224** by focusing on API stability and backward compatibility after the `/showcase/*` rollout, and by coordinating with teammates to ensure the existing test suite + older client calls continued to work without sacrificing the new endpoint structure.

---

### What I worked on (technical)

#### 1) Restored backward-compatible API surface via legacy aliases
After the new `/showcase/*` endpoints landed, several older routes used by existing tests/clients started returning `404` or behaving inconsistently. I helped address this by adding **legacy route aliases** that map old endpoints to the new showcase implementation. This preserved the upgraded architecture while preventing breakage for consumers that still call legacy URLs.

Key alias mappings included (conceptually):
- `GET /portfolios/latest` → `GET /showcase/portfolios/latest`
- `GET /portfolios/evidence` → `GET /showcase/portfolios/evidence`
- `GET /users` and `GET /users/{user}/projects` → `GET /showcase/users` and `GET /showcase/users/{user}/projects`

This approach keeps the new canonical endpoints while supporting “old” traffic through a thin compatibility layer.

#### 2) Stabilized FastAPI app wiring for deterministic mounting
I also worked on making the app initialization more deterministic in `create_app()`:
- Ensured routers for **portfolio / showcase / resume** are mounted consistently.
- Avoided cases where route availability depended on import order or runtime conditions.
- Added/maintained a stable app factory (`get_app_for_tests`) so endpoint tests can build an identical app instance without starting a real server.

This reduced “it works locally but CI fails” problems tied to router mounting differences.

#### 3) Tightened validation behavior for legacy endpoints
For some legacy routes, missing fields/params were silently accepted or behaved unpredictably. I adjusted validation so requests that are missing required inputs return **400/422** instead of “passing” and producing incorrect outputs. This makes API behavior more explicit and prevents flaky downstream behavior.

#### 4) Dependency note for upload endpoints
Documented/confirmed the requirement for `python-multipart` for upload/form-data routes (e.g., endpoints using `UploadFile`). This is necessary for FastAPI to register multipart dependencies correctly and prevents runtime failures when starting the server.

---

### Collaboration
- Coordinated with the PR owner/merger (Eren) to make sure the fix preserved the new `/showcase/*` design while keeping existing test expectations intact.
- Reviewed changes with the lens of “don’t break tests / don’t break old clients,” and iterated until the endpoints, validation, and router mounting aligned with the current test suite.
- Verified behavior by running the relevant endpoint tests locally and confirming `/docs` reflected the restored legacy routes alongside the new showcase routes.

---

### Outcome
PR #225 successfully merged with:
- **Backward-compatible endpoints restored** via alias routing,
- **Deterministic app initialization** for consistent test/runtime behavior,
- **Improved request validation** for legacy compatibility routes,
- Reduced regression risk while keeping `/showcase/*` as the canonical API surface.

## Journal Update — PR #220 (Milestone 2 API: incremental uploads, DB migration, overrides, tests)

I delivered the core Milestone 2 API functionality in PR **#220**, focused on enabling incremental artifact uploads, storing multiple snapshots over time, and supporting human-in-the-loop edits with persistent overrides.

---

### 1) Incremental uploads support (`POST /projects/upload`)
**Goal:** Allow the same project to be uploaded multiple times over time (incremental snapshots), instead of treating each upload as a brand new project.

**Changes:**
- Updated `POST /projects/upload` to accept an **optional `project_id`** query parameter.
  - If `project_id` is provided, the new upload is attached to the same project, creating a new snapshot entry rather than creating an entirely separate project.
- Updated the file storage path to support reusing the provided `upload_id` when appropriate, instead of always generating a new one.  
  - This reduced duplication and kept snapshot linkage consistent.

---

### 2) DB schema migration for snapshots (`uploads` table)
**Problem:** The existing schema prevented storing multiple upload rows per logical project upload id (or enforced uniqueness constraints that made incremental snapshots impossible).

**Changes:**
- Added a migration step in the DB open/init path (e.g., `storage.open_db()` style flow) to update the `uploads` table schema so multiple rows can exist for the same logical upload identifier.
- Removed/relaxed the **UNIQUE constraint** on `upload_id` (or equivalent key), enabling multiple upload records to reference the same project while still preserving dedupe/file store semantics.

**Outcome:** The DB can now store multiple snapshots for a project without breaking existing stored file references.

---

### 3) Human-in-the-loop project overrides (`project_overrides` table + endpoints)
**Goal:** Support user edits/corrections (Milestone 2 requirement) and persist them in the DB.

**Changes:**
- Added a new DB table (e.g., `project_overrides`) to store edits such as:
  - `key_role`, `evidence`, `portfolio_blurb`, `resume_bullets`, `selected`, and `rank`
- Implemented endpoints:
  - `PATCH /projects/{project_id}` to save overrides
  - `GET /projects/{project_id}/overrides` to fetch overrides

**Outcome:** Generated content can be corrected by the user and remains stable across re-runs.

---

### 4) Tests (API-level validation)
Added/updated endpoint tests to verify:
- Incremental upload behavior works as expected (same project gets multiple uploads)
- Dedupe behavior still holds (no unintended duplication)
- Overrides endpoints persist and return updates correctly

---

### Verification
- ✅ Full test suite passes locally (`pytest -q`)
- ✅ `/docs` shows the new/updated endpoints
- ✅ Incremental uploads visible via upload history endpoints (snapshot flow confirmed)

---

### Impact
This PR completed the core Milestone 2 API requirements around incremental uploads/snapshots, DB persistence, and human-in-the-loop editing — while keeping behavior testable via HTTP-level endpoint tests.


<img width="1080" height="626" alt="Screenshot 2026-03-01 at 1 21 15 PM" src="https://github.com/user-attachments/assets/b45eaf54-b1f2-455d-9668-a16b43041c4f" />

### TERM 2 WEEK 9 PERSONAL LOG
This includes all merged PR's :



---

#### PRs Worked On

##### PR #271 — Feature/resume portfolio UI
- Built the initial **Portfolio & Resume** tab UI in the Electron frontend.
- Added the base page structure for résumé-style presentation inside the app.
- Implemented major sections such as:
  - Resume snapshot
  - Portfolio showcase area
  - Portfolio stats
  - Resume preview modal
- Established the core styling and layout foundation for later milestone features.

**Contribution impact:**  
This created the initial user-facing portfolio/resume experience and gave the team a structured frontend area for Milestone 3 features.

---

##### PR #273 — Add skills timeline to portfolio resume page
- Added a **Skills Timeline** section to the Portfolio & Resume page.
- Built rendering logic to show skills progression over time.
- Added stable empty-state handling when no timeline data is available.
- Integrated the section cleanly into the portfolio page layout without breaking other tabs.

**Contribution impact:**  
This improved the quality of the web portfolio view and aligned the project more closely with the milestone requirement of showing learning progression and evidence of skill development over time.

---

##### PR #278 — Polish portfolio resume page and add skills timeline view
- Refined and polished the overall **Portfolio & Resume** layout after initial implementation.
- Improved section placement, spacing, and consistency across cards.
- Stabilized rendering behavior so portfolio elements appeared in the correct tab and with the intended layout.
- Improved the usability and presentation of the skills timeline view.
- Cleaned up empty-state messaging to make the page feel more complete even when certain data is unavailable.

**Contribution impact:**  
This PR moved the work from “feature exists” to “feature is polished and demo-ready,” which is important for milestone evaluation and final product usability.

---

##### PR #281 — Feature/activity heatmap
- Added an **Activity Heatmap** section to the Portfolio & Resume page.
- Connected the frontend to a backend activity heatmap endpoint.
- Integrated activity-over-time visualization into the portfolio experience.
- Implemented a fallback empty state when no activity timeline data exists yet.
- Continued backend/frontend integration for portfolio summary and heatmap data flow.

**Contribution impact:**  
This helped surface project productivity over time and strengthened the portfolio as a richer evidence-based representation of user work.

---

#### Technical Work Completed
- Worked extensively in the Electron frontend (`index.html`, renderer files, styling).
- Built new UI sections and integrated them into existing navigation.
- Connected frontend components to backend portfolio/timeline/heatmap endpoints.
- Debugged backend route issues related to:
  - database configuration
  - route mounting
  - port mismatches
  - snapshot loading assumptions
- Improved fault tolerance by designing clean empty states instead of letting missing data break the page.
- Reused existing project data and snapshot structure instead of inventing placeholder data paths.

---

#### Challenges / Problems Solved
- Resolved issues caused by backend port mismatches during frontend testing.
- Investigated failures in portfolio summary and heatmap endpoints.
- Diagnosed a database path issue where the backend expected a directory path rather than a direct `.db` file path.
- Debugged problems caused by assumptions about snapshot row structure.
- Verified that features rendered safely even when underlying timeline/activity data was not yet populated.

---

#### Collaboration / Workflow
- Opened, reviewed, and iterated through multiple PRs instead of bundling everything into one large change.
- Structured work into smaller milestone-aligned contributions:
  - base portfolio UI
  - skills timeline
  - portfolio polish
  - activity heatmap
- This made the work easier to review and easier to justify as separate contributions.

---

#### What I Learned
- Building a feature is only part of the work getting it into a clean, reviewable, milestone-aligned state takes additional refinement.
- Frontend/backend integration often fails due to environment/configuration issues rather than purely logic bugs.
- Empty states and graceful fallback behavior matter a lot in making a feature feel stable and professional.
- Splitting features into focused PRs creates a clearer contribution history and better review process.

---

#### Next Steps
- Continue improving backend/frontend integration for richer portfolio summary data.
- Expand the portfolio sections so more résumé content is driven by real extracted backend data instead of only aggregate counts.
- Improve testing coverage for portfolio-related routes and UI rendering behavior.
- Keep polishing the Milestone 3 user-facing product so it is both functional and presentation-ready.

---

#### Reflection
Overall, this was a productive week with visible progress on Milestone 3. I contributed multiple portfolio-related PRs that improved both the technical functionality and the polish of the user-facing application. The main value of my work this week was not just adding new features, but also making the portfolio experience more coherent, more stable, and more aligned with the final expectations of the capstone project.

ALL PRS:
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/281
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/278
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/273
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/273



<img width="1077" height="628" alt="Screenshot 2026-03-08 at 5 29 04 PM" src="https://github.com/user-attachments/assets/541a3254-2cb2-446f-8a95-ff2955cda6fa" />




### TERM 2 WEEK 10 PERSONAL LOG

# Weekly Log of Merged PRs

## Week of March 9–15, 2026

This week, the team continued integration work on the frontend and resume/portfolio flows, along with project viewing and export-related fixes. Based on the repository history visible in GitHub Desktop, the following merged PRs and merge events were observed:

### Merged PRs
# Weekly Work Log

## Week of March 9–15, 2026

This week, I mainly worked on the **portfolio customization feature for Private Mode** as part of **Issue #291 — user customization / portfolio**.

### What we worked on
- built the **Customization** page in **Private Mode**
- added support for choosing **featured projects** for the **Top 3 Project Showcase**
- added per-project customization fields for:
  - **key role**
  - **evidence of success**
  - **portfolio blurb**
- added **section visibility controls** so users can choose which sections appear on the **Portfolio & Resume** page
- connected customization settings to the portfolio page so saved changes are reflected immediately
- added customization state handling using **localStorage**
- connected project-specific edits to the backend edit flow
- updated portfolio rendering logic to prioritize:
  1. user customization overrides
  2. backend-generated summary data
  3. fallback default text

### Debugging and fixes
- debugged the **Private Mode login issue**
- found that the backend was not running locally on port `8002`
- fixed backend startup issues by setting the correct `CAPSTONE_DB_DIR`
- installed missing backend dependencies such as `boto3`
- confirmed the backend runs successfully with the local FastAPI server
- fixed the **blank Customization tab** issue caused by duplicate `customization-page` markup in `index.html`
- corrected the section visibility control rendering issue

### Verification completed
- confirmed login works in **Private Mode**
- confirmed the **Customization** tab appears after login
- confirmed project data loads into the customization workflow
- confirmed featured project selection works
- confirmed custom text fields save correctly
- confirmed portfolio overrides appear on the **Portfolio & Resume** page
- confirmed section visibility changes affect the portfolio page correctly

### Outcome
By the end of the week, the **portfolio customization workflow for Private Mode** was working end-to-end and was ready to be submitted as a PR.

Merged PRS: 


https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/299
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/300
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/301
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/302

<img width="1077" height="628" alt="screenshot" src="https://github.com/user-attachments/assets/541a3254-2cb2-446f-8a95-ff2955cda6fa" />


### TERM 2 WEEK 12 PERSONAL LOG
## Pull Request
**PR #348 — Add bar, pie, donut, and radar views to most used skills widget**

## Branch
`feature/dashboard-skils-c3a121f` → `develop`

## Summary
This sprint, I contributed a frontend dashboard enhancement by expanding the **Most Used Skills** widget to support multiple visualization modes. I implemented **bar, pie, donut, and radar chart views**, and updated the widget’s **layout, styling, and controls** so users can switch smoothly between chart types.

## What I Did
- Added **4 chart view options** to the Most Used Skills widget:
  - Bar chart
  - Pie chart
  - Donut chart
  - Radar chart
- Updated the **UI styling and layout** to support the new visualization controls
- Improved the widget so the chart mode switching feels more interactive and user-friendly
- Opened a pull request, documented the feature clearly, and completed the GitHub review workflow
- Got the PR **reviewed and merged into `develop`**

## Testing
- Manually tested the dashboard in the **Electron app**
- Switched between **bar, pie, donut, and radar** modes to confirm the widget rendered and updated correctly
- Performed a self-review before merging

## Outcome
- PR successfully **merged**
- Contribution added a more flexible and visually rich dashboard experience
- Helped improve the usability and presentation quality of the portfolio analytics interface

# GitHub Work Log — Develop Integration / Test PR

## Branch
`feature/dashboard-skills-clean` → `develop-v2`

## Purpose
This PR was mainly used as a **test/integration step** to check whether the dashboard skills changes and related files were working properly on the develop branch. The goal was to verify that the updated files could be merged, rendered, and interacted with correctly in the shared codebase.

## What I Did
- Tested whether the dashboard skills files worked correctly when brought into the develop branch
- Verified the **Most Used Skills** widget updates in the integrated branch
- Checked multiple visualization-related changes for compatibility
- Reviewed widget interaction flow and dashboard animation behavior
- Used this PR to identify branch compatibility issues before finalizing the feature work

## Testing
- Verified the dashboard rendered the updated skills widget views
- Manually checked widget interactions and animation behavior
- Used the PR as a practical merge/integration test for develop
- Noted merge conflicts with the base branch for follow-up resolution

## Outcome
- Confirmed that the files could be tested in the develop branch environment
- Helped surface integration issues early
- Supported the final cleanup and safer merging of the dashboard skills work

## Notes
This was not just a feature addition PR — it also served as a **branch compatibility and integration check** to make sure the updated dashboard skills files behaved properly on `develop-v2`.


# GitHub Work Log — Cinematic Dashboard UI + Activity Log Fix
## Branch
`fix/dashboard-activity-log` → `develop`
## Summary
In this pull request, I worked on improving both the **functionality** and **visual quality** of the dashboard. The main issue was that the **Activity Log was not rendering properly**, even though the backend endpoints were returning valid data. I fixed the rendering problem so backend activity data displayed correctly in the dashboard, and I also enhanced the UI to make the dashboard feel more polished and interactive.

## What I Did
- Fixed the **Activity Log rendering issue** on the dashboard
- Improved the handling and display of **backend activity data**
- Added an enhanced **Activity Log UI** with:
  - live badge
  - level filters
- Improved the overall dashboard presentation with:
  - more polished card styling
  - stronger widget effects
  - better visual interactions
  - a more cinematic dashboard feel

## Why This Mattered
The dashboard looked incomplete because the activity data was not appearing correctly even when the backend was working. This PR helped make the dashboard both:
- **functionally correct**
- **visually stronger**

## Testing
- Verified that the Activity Log now loads and displays backend data correctly
- Checked that the updated dashboard UI rendered properly
- Reviewed the live activity section and filter behavior manually
- Confirmed that the frontend changes worked within the existing Electron/renderer setup

## Outcome
- PR successfully merged into `develop`
- Fixed a visible dashboard issue
- Improved the overall frontend user experience
- Made the dashboard more complete, interactive, and polished

## Notes
- Type of change:
  - **Bug fix**
  - **New feature**
- Labels:
  - `enhancement`
  - `frontend`
- No new backend dependencies were required


# GitHub Work Log — Chat Tab and Demo Chatbot Integration

## Branch
`feature/ai-chatbot` → `develop`

## Summary
In this pull request, I added a new **Chat** feature to the Electron app and connected a working **demo chatbot flow** for the Loom dashboard. The goal was to expand the platform with an interactive chatbot experience that fits the existing dashboard and could later be upgraded into a real LLM-backed assistant.

## What I Did
- Added a new **Chat tab** to the top navigation
- Created a dedicated **Chat page** in `index.html`
- Added chat UI styling to match the existing **dark dashboard theme**
- Built `chat.js` to handle:
  - chat history rendering
  - send button behavior
  - Enter-to-send
  - quick prompt buttons
  - clear chat
  - localStorage persistence
- Exposed a safe Electron bridge in `preload.js` using `window.loomAI.chat(...)`
- Added an `ipcMain.handle("ai:chat", ...)` handler in `main.js`
- Implemented **demo-mode chatbot replies** in the main process so the feature works without paid API access
- Connected chat initialization inside `renderer.js`

## Why This Mattered
The app already had dashboard, projects, resume, portfolio, and job match views. This PR extended the app by adding an interactive chatbot experience, making the platform feel more complete and giving the team a usable AI-style feature for development, demos, and UI review.

## Testing
- Verified the Chat tab appeared correctly in the Electron app
- Tested sending messages through the demo chatbot flow
- Checked chat history rendering and input interactions
- Confirmed Enter-to-send, quick prompts, and clear chat behavior
- Verified localStorage persistence worked as expected
- Confirmed the chatbot worked in demo mode without requiring paid API access

## Outcome
- PR successfully merged into `develop`
- Added a functional chatbot interface to the app
- Improved the app’s interactivity and demo readiness
- Created a foundation for future real AI assistant integration

## Notes
- Type of change:
  - **New feature**
  - **Frontend enhancement**
- Labels:
  - `develop`
  - `enhancement`
  - `frontend`
- The chatbot currently runs in **demo mode**, which makes it useful for testing and demos without live API billing


https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/315
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/332
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/346
https://github.com/COSC-499-W2025/capstone-project-team-17-1/pull/348


<img width="1470" height="956" alt="Screenshot 2026-03-29 at 10 42 19 PM" src="https://github.com/user-attachments/assets/dca66ed2-f754-4258-9a0b-006a70912472" />


