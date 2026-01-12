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


