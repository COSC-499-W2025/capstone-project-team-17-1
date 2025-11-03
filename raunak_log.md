# COSC 499 TEAM 17 Personal Log - Raunak Khanna

## Table of Contents
- [Week 3 Personal Log](#week-3-personal-log)
- [Week 4 Personal Log](#week-4-personal-log)
- [Week 5 Personal Log](#week-5-personal-log)
- [Week 6 Personal Log](#week-6-personal-log)
- [Week 7 Personal Log](#week-7-personal-log)
- [Week 8 Personal Log](#week-8-personal-log)
- [Week 9 Personal Log](#week-9-personal-log)

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
