# COSC499 Team 127 Personal Log - Parsa Aminian (41202862)

## Week 3 Personal Log [Sept 15 – Sept 21, 2025] {#week-3}

This week I contributed to multiple parts of our project’s requirement specification document:

### Non-Functional Requirements
- Helped define performance expectations, such as efficiency and reliability of artifact mining.  
- Specified scalability goals (e.g., system should handle large catalogs and use CPU cores efficiently).  
- Contributed to usability requirements including accessibility, onboarding, and responsiveness.  
- Outlined key security measures (encryption, least-privilege access, secure deletion).  
- Added maintainability standards such as automated test coverage, documentation updates, and CI checks.  
- Ensured privacy considerations were included (local-only analysis, redaction of sensitive data, idle lock).  

### Data Requirements
- Specified supported file types (code, text, PDF, images, audio, video, design files).  
- Defined metadata fields to capture (path, name, size, timestamps, owner).  
- Added hashing/deduplication requirements using SHA-256 for integrity checks.  
- Defined storage formats (SQLite or JSON with indexing).  
- Included data quality checks and conflict reporting.  
- Outlined export formats (CSV/JSON) and data volume limits (≥5 million artifacts).  

### Technical Requirements
- Proposed use of SQLite or JSON with write-ahead logging for local storage.  
- Defined cross-platform build requirements (Windows, macOS, Linux).  
- Added support for Git repository metadata extraction.  
- Specified JSON API on localhost for modular design.  
- Required metadata extraction from media files (dimensions, duration, codec).  
- Defined Unicode/path handling requirements.  
- Proposed concurrency model using worker pools with back-pressure.  
- Specified configuration handling through user settings and environment variables.  

### Reflection
This week I gained a stronger understanding of how detailed requirements shape the foundation of a project. I learned the importance of balancing **functional scope with non-functional qualities**, and how technical and data requirements ensure the system is both practical and scalable. Writing these sections gave me experience in thinking not just about what the system should do, but how it should behave under real-world conditions. 

---

## Week 4 Personal Log [Sept 22 – Sept 28, 2025]

This week I focused on moving our project forward through early design and planning deliverables:

### Architecture Design Diagram
- Created the first draft of our system’s architecture design diagram.  
- Outlined the key components including data ingestion, metadata extraction, storage, and user interface.  
- Added communication flows between modules to show how data moves through the system.  
- Ensured the diagram reflected scalability and modularity by separating concerns into distinct layers.  
- Highlighted potential integration points for APIs and external tools.  

### Project Proposal
- Drafted the **Proposed Workload Distribution (Parsa)**, outlining ownership of the ingestion and preprocessing pipeline, metadata schema and indexed storage, privacy and security guardrails, analytics and insights, CI/testing and developer tooling, plus architecture documentation and demo prep.
- Defined **measurable success metrics** for each ownership area, including ingest throughput (≥ 200 files per minute with zero data loss), indexed lookup latency (< 100 ms on common filters), redaction verification via automated tests and a spot-check script, correct top-five insights on a seeded workspace, and pipeline code coverage targets with a one-command local setup.
- Authored an **8-sprint plan** with concrete deliverables:
  - **Sprint 1** discovery and scaffolding  
  - **Sprint 2** ingestion MVP  
  - **Sprint 3** indexing and query  
  - **Sprint 4** privacy pass  
  - **Sprint 5** analytics v1  
  - **Sprint 6** performance and scale  
  - **Sprint 7** polish and docs  
  - **Sprint 8** release and handoff
- Specified **interfaces and collaboration points**:
  - Storage service with CRUD for artifacts plus search and filters  
  - Event hooks for discovered, indexed, redacted, and deleted artifacts  
  - Repository redaction policy file in YAML or JSON consumed by ingestion and UI review
- Documented **key risks and mitigations**:
  - Heterogeneous file types → plug-in extractor pattern with safe fallback  
  - Large catalogs → streaming, batching, backpressure, memory ceilings  
  - Privacy gaps → redaction-first defaults and explicit allow lists with unit tests
- Took ownership of **architecture documentation and demo materials**, including the system architecture diagram, data-flow diagrams, and a short demo script teammates can use to explain the pipeline in two minutes.

### Reflection
Working end-to-end on ownership, metrics, sprints, interfaces, and risk mitigations strengthened my ability to turn broad goals into executable plans. By specifying measurable targets and clear collaboration points, I made it easier for the team to integrate work, validate progress, and de-risk the pipeline from ingestion through analytics to the final demo.

---

## Week 5 Personal Log [Sept 29 – Oct 5, 2025] 
This week I worked with **Michelle** and **Raunak** to produce our **DFD Level 0 and Level 1** for the Data Mining App. The diagrams below reflect the finalized processes and data stores exactly as in our team drawing.

> **Peer Eval**
>
> ![DFD L0 & L1 — Data Mining App](![alt text](Assets/Peer%20Eval%20Week%205.png))
> _Figure 0. peer evaluation._

---

> **Diagram placeholder — replace with your export**
>
> ![DFD L0 & L1 — Data Mining App](![alt text](/Assets/DFD.png))
> _Figure 1. Level 0 and Level 1 DFD._

---

### DFD Level 0 — Context

**External Entities**
- **User**
- **System API** (external service we request analysis from / receive analysis back)

**System**
- **Data Mining App**

**Level-0 Flows**
- **User → Data Mining App:** `User Authentication`, `Data Mining Request`
- **Data Mining App → User:** `Output Portfolio`
- **Data Mining App → System API:** `Request Data Analysis`
- **System API → Data Mining App:** `Provide Data Analysis`

> *Balancing:* All inbound/outbound data at Level 0 reappears in Level 1 as aggregated equivalents.

---

### DFD Level 1 — Decomposition

**Processes**
1. **Source Selection** — user chooses input source(s)  
   - *Flow:* `Select Source` (User → Source Selection)
2. **Mining / Scan** — executes scan tasks and generates file records  
   - *Flow:* `Scan Task` (Source Selection → Mining/Scan)  
   - *Outputs:* `File Records` (→ **Artifact DB**), `Scan Logs` (→ **Error Logs**)
3. **Analytics & Metrics Generation** — computes metrics and insights from artifacts  
   - *Inputs:* reads **Artifact DB** (implicit via `File Records`)  
   - *Outputs:* `Metrics & Insights` (→ Visualization & Export), `Data Results` (→ **Error Logs**)  
     *(we keep “Data Results → Error Logs” to mirror the team diagram’s diagnostic capture)*
4. **Visualization & Export** — assembles dashboard and export views  
   - *Inputs:* `Metrics & Insights`  
   - *Outputs:* `Dashboard Report` and `Return Output` (→ User)
5. **Save Portfolio** — persists selected results  
   - *Inputs:* `Save Portfolio` (User → Save Portfolio)  
   - *Outputs:* `Store Data` (→ **Portfolio Database**)
6. **Export Portfolio** — produces external deliverables from saved data  
   - *Inputs:* `Export Data` (reads from **Portfolio Database**)  
   - *Outputs:* `Export Logs` (→ **Error Logs**)

**Data Stores**
- **Artifact DB** — persists `File Records` from scans  
- **Portfolio Database** — holds saved portfolio data  
- **Error Logs** — central sink for `Scan Logs`, `Data Results`, and `Export Logs`

**User-Facing Flows**
- `Dashboard Report` and `Return Output` (Visualization & Export → User)

---

### Decisions & Alignment with the Diagram
- **Centralized logging:** All operational diagnostics route to **Error Logs** from scanning, analytics, and export, matching the diagram’s right-side bus.
- **Portfolio lifecycle split:** We separated **Save Portfolio** (persist) from **Export Portfolio** (publish) with **Portfolio Database** in between, as shown.
- **External analysis path:** Level-0 API interaction is captured implicitly at Level-1 within **Mining/Scan** + **Analytics**, which is where outbound requests and inbound results are handled in our implementation plan.



### Reflection
Translating the whiteboard into balanced Level-0/Level-1 diagrams clarified ownership boundaries and logging strategy. Collaborating with Michelle and Raunak helped us standardize flow names (`Scan Task`, `File Records`, `Metrics & Insights`, etc.), and the explicit **Portfolio Database** node makes the save/export UX and audit trail straightforward for the peer evaluation.

---

## Week 6 Personal Log [Oct 6 to Oct 12, 2025] {#week-6}

This week our team finalized task assignments and I focused on platform setup, planning, and early implementation work.

> **Peer Eval**
>
> ![Week 6 — Data Mining App](![alt text]
> <img width="1086" height="637" alt="image" src="https://github.com/user-attachments/assets/264b1aa2-2561-4af3-9880-4de67dbd418d" />
> _Figure 0. peer evaluation._

### Environment and Tooling Setup
- Set up Docker for local development with a base image, dev dependencies, and a multi stage build for smaller images  
- Wired Electron scaffolding so the desktop shell can run the app locally and inside a container  
- Documented run, build, and troubleshoot commands so teammates can reproduce the setup  

### Work Breakdown Structure and Planning
- Broke the project into concrete tasks with clear owners and acceptance criteria  
- Sequenced tasks for the next sprint and added estimates and dependencies to reduce blocker risk  
- Linked WBS items to our repo issues to keep tracking and status consistent  

### Requirements Walkthrough
- Wrote an explaination for Week 3 requirements in the team logs, clarifying performance, security, and data constraints  
- Captured open questions and updated notes where wording was ambiguous  
- Verified alignment between requirements and the current WBS items  

### Coding Progress
- Added initial boilerplate to start the app with a minimal Electron main process and a placeholder renderer  
- Wrote starter scripts for lint, format, and type checks to keep the codebase consistent  
- Committed a sample module to exercise the build and run pipeline end to end  

### Reviews and Pull Requests
- Reviewed teammates code and pull requests for clarity, correctness, and consistency with requirements  
- Left actionable comments and suggested small refactors to reduce tech debt early  
- Verified that new changes build cleanly in Docker and still run in Electron

### Reflection
This week was about enabling the team. Getting Docker and Electron stable gave everyone a common platform and fewer environment bugs. Turning requirements into a concrete WBS helped us see scope, ordering, and risks. The small amount of starter code proved the path from source to a running desktop app, and early reviews kept quality in check. I feel confident that our foundation is solid and that the next sprint can focus on features rather than setup.

---

## Week 7 Personal Log [Oct 13 – Oct 19, 2025] {#week-7}

This week I implemented and shipped a full **Tech Stack Detector** feature and wired it into our Electron app.

 **Peer Eval**
>
> ![Week 7 — Data Mining App](![alt text]
> <img width="1084" height="632" alt="image" src="https://github.com/user-attachments/assets/53911e5e-e216-42ee-9f5c-823bf7138fbc" />

> _Figure 0. peer evaluation._


### Feature: Tech Stack Detection and UI Integration
- Built `detectTechStack.js` to scan the repo and identify languages, frameworks, tools, and package managers, and to generate `TECH_STACK.md`.  
- Exposed an IPC channel `tech:detect` in the main process and a `window.tech.detect()` bridge in `preload.js`.  
- Added a new section in the renderer with a Detect tech stack button, summary cards, and a live preview of the generated markdown.  
- Verified output in app matches CLI dry run and shows Electron and Jest correctly for our project.

### Testing and Tooling
- Created a Node test runner suite `test/detectTechStack.node.test.js` that mocks a tiny project and asserts detector output and markdown creation.  
- Fixed package scripts so the team can run `npm test` consistently without breaking the existing Node test workflow.  
- Resolved path issues by switching to `__dirname` based requires in `main.js`.

### Bug Fixes and Polishing
- Repaired PHP composer parsing using safe bracket notation for `require-dev`.  
- Removed paste artifacts that caused ReferenceError and syntax errors.  
- Cleaned relative paths so imports work from `src/` without aliasing.

### Documentation and PR
- Added `detect:tech` and `detect:tech:dry` npm scripts.  
- Wrote and filled a PR description that closes Issue 39 and explains testing and scope.  
- Updated the PR template to match our project and added a concise review checklist.

### Reflection
This week taught me how to move quickly from a command line utility to a fully integrated app feature. I practiced clean IPC design, safer file system mocking for tests, and careful script configuration so the whole team can run tests the same way. Seeing the detector surface real project signals in the UI felt great and set us up for clearer onboarding and audits.

---

## Week 8 Personal Log [Oct 20 – Oct 26, 2025] {#week-8}

This week I worked on two big areas: polishing the frontend/UX of our Electron app and implementing the new **Key Skills Extraction** feature that analyzes contributors’ work and surfaces what each teammate is strong in. I also got tests working in CI again after refactoring backend logic.

**Peer Eval**  
>
> ![Week 8 — Data Mining App](![alt text]
> <img width="1064" height="623" alt="image" src="https://github.com/user-attachments/assets/261a17cc-9332-420f-937a-ac80ec4a54de" />

> _Figure 0. peer evaluation._

---

### Frontend / UI Work

**Branding + polish**
- Rebranded the app from the default Electron boilerplate to our own name, **Loom**.
- Added a custom app icon (SVG → ICO/ICNS) and updated `BrowserWindow` so the icon shows instead of the Electron logo.
- Swapped in a full-screen gradient background and moved the UI into styled cards with rounded borders, subtle shadows, and a dark navy theme. This made the dashboard look way more like a product and less like a prototype.
- Customized the scrollbars to match our color scheme (dark track, accent thumb), and removed the ugly default Windows light gray scrollbars.
- Made the Electron window open “borderless fullscreen style” (maximized client area) so the app fills the screen on launch instead of a tiny dev window.

**Landing / UX**
- Started planning a Welcome screen (separate HTML) so that when the app opens we can show “Welcome / Get Started →” instead of immediately dumping raw tables.
- Hooked up the renderer layout to be more modular so we can swap between views (welcome vs dashboard).

**Result:** The UI now feels like an actual product demo we could hand to someone, not just an internal debug tool.

---

### Feature: Key Skills Extraction

We added a full skills analyzer that answers:  
**“What does each teammate actually work on?”**

#### Backend skills pipeline
- Built `detectSkills` which:
  - Looks at commit histories and breaks down who edited which files and how many lines in each language / tech area.
  - Maps file extensions (like `.js`, `.ts`, `.sql`, `.cs`) to higher-level skills (`JavaScript`, `TypeScript`, `SQL/Databases`, `C#`, `Electron`).
  - Ignores noise like `.md`, `.json`, `.yml`, images, lockfiles, etc.
- Added logic to attribute lines only to authors/co-authors, not reviewers. This makes the signal about actual code ownership instead of approvals.
- Tracks `linesByExt` per contributor, so we know “Alice touched 900 lines of JS and 100 lines of SQL.”
- From that, we compute:
  - **Impact bar** per skill = how much of this person’s work is that skill.
  - **Confidence %** per skill = how certain we are that the person actually works in that area.  
    We turned this into a dynamic curve: higher share of edits in that skill → higher confidence. Low/no evidence = lower confidence, not just a flat 60%.

#### Filtering / quality control
- Added an allow-list of meaningful skills (JavaScript, SQL/Databases, Electron, C#, etc.).
- Added thresholds so junk doesn’t show:
  - Drop a skill for a person if it’s < N lines or < X% of their total work.
  - Drop a skill from project chips if it barely appears overall.
- This gets rid of spam like “CSS” or “Markdown” showing up as someone’s “top skill” just because they fixed a README once.

#### IPC + renderer integration
- Added a new IPC channel `skills:get` in `main.js`.
  - It builds a snapshot of all contributors, runs `detectSkills`, then returns `{ projectSkills, contributorSkills }` to the renderer.
- In the renderer (index.html):
  - Created a **Key skills** card with:
    - “Detect key skills” button that calls `window.loomSkills.get()` and renders results.
    - Chips across the top for the project’s dominant skills.
    - A table of contributors where each row shows:
      - the skill name,
      - an “impact” progress bar,
      - the confidence percentage for that skill.
    - “Copy JSON” button for debugging and “Export CSV” button that generates a proper comma-separated export with `email, skill, confidence, impact, lines, sources`.
  - Filtered out contributors who had no real evidence so we don’t show blank rows.

Result: we can now point at the app and say “this person is mostly JavaScript, this person’s top secondary area is SQL/Databases,” with confidence numbers and supporting evidence.

---

### Testing & Stability

**Skills tests**
- Added `test/skills.test.js` which:
  - Builds a fake snapshot (JS-heavy plus some SQL) and checks that:
    - `detectSkills` returns the expected high-signal skills for that project.
    - One contributor’s JavaScript confidence is higher than their SQL confidence.
    - Noise like markdown-only edits doesn’t get flagged as a “real skill.”
- Hooked these into our test runner (`npm test`) using Electron’s Node mode (`ELECTRON_RUN_AS_NODE=1 electron --test`).

**Fixing broken tests in existing code**
- After refactoring contributor analysis, the old tests for `gitContributors` started failing with `author is not defined` and bogus `linesAdded`/`linesDeleted` fields.
- I fixed `buildCollaborationAnalysis` to:
  - Stop referencing undefined `author` / `coauthors` variables.
  - Attribute line counts using the actual parsed fields (`commit.additions` / `commit.deletions`).
  - Split line credit between the real participants (author + co-authors) only, leaving reviewers out, which is what the tests expect.
- After that, the team’s original tests for classification (“individual vs collaborative”), shared-account detection, CSV export, etc. all started passing again.

**Dev environment fixes**
- Helped fix the native module mismatch for `better-sqlite3` on a new machine.
  - It was compiled for a different Node ABI than the version bundled with our Electron build.
  - Documented and ran `npm install` + `npm run rebuild:electron` (`electron-rebuild`) to rebuild `better-sqlite3` against our Electron runtime.
- Added guidance that we may want a `postinstall` script to auto-run `electron-rebuild` so teammates don’t get blocked by ABI errors when they pull.

---

### PR / Process

- Wrote PR descriptions for:
  - Frontend polish & branding (“Loom”, fullscreen window, gradient background, custom icon).
  - The Key Skills feature: what it does, how we calculate impact and confidence, and how we tested it (manual flow + automated tests).
- Filled in the Testing section in the PR template:
  - Manual steps (click Detect, inspect table, export CSV).
  - Automated steps (`npm test` / `npm run test:watch`).
- Connected the PR to Issue #53 (“Extract Key Skills”) so it can auto-close.

---

### Reflection

This week felt like a legit product turn instead of just raw data plumbing:
- I took something that was originally just internal numbers (lines-per-ext, commit metadata) and exposed it in a way that teammates and maybe even stakeholders could understand at a glance.
- I gave the app an identity (Loom), cleaned up visuals, and started thinking about first-run UX.
- I also had to do some “integration janitor” work: fixing test failures caused by refactors, dealing with native module rebuilds, and making sure our scripts work across machines.

The coolest part was watching the Key Skills panel evolve from “dump some JSON” to a proper dashboard with impact bars, % confidence, and CSV export. It feels like the first real version of our collaboration analytics story.

---

## Week 9 Personal Log [Oct 27 – Nov 2, 2025] 

This week our team shifted the project backbone from Electron to Python because the spec requires all code to be in Python. We paired up to move backend logic into a clean Python package and kept Electron only as a future shell for the desktop UI. I focused on designing and shipping the Safe Insight Deletion workflow and wiring tests so the feature is reliable.

**Peer Eval**  
>
> ![Week 9 — Data Mining App]
> <img width="1064" height="623" alt="image" src="https://github.com/user-attachments/assets/261a17cc-9332-420f-937a-ac80ec4a54de" />
>
> _Figure 0. peer evaluation._

---

### Backend migration to Python

* Coordinated with the team to move core analysis and storage into a `capstone` Python package.
* Added an insight catalog with stable identifiers and a dependency graph so we can answer who uses what.
* Exposed a simple CLI for now and left a FastAPI surface ready for later so Electron can call into Python when the UI returns.
* Documented the new structure and how to run unit tests with `python -m unittest`.

**Result**  
We now have a Python first backend that matches the course requirement and is easier to test and ship.

---

### Feature: Safe Insight Deletion

Built an end to end safe delete pipeline so no one can accidentally remove an insight that others still need.

* **Reference model**  
  * Incoming edges count as references. The system counts only active dependents so soft deleted items do not block a purge.
* **Workflow**  
  * Dry run gives a full impact report and a plan.  
  * Soft delete moves items into a trash area and keeps a JSON snapshot for restore.  
  * Restore recreates insights and their edges exactly as before.  
  * Purge removes data for real and leaves an audit trail.
* **Storage**  
  * SQLite tables for insights, deps, files, trash, and audit.

**CLI usage now available**  
Create insights, add dependencies, dry run, soft delete, restore, purge, list trash, and view audit log.

---

### Testing and stability

* Wrote a `unittest` suite that covers block versus cascade behavior, round trip restore, purge rules, and the audit trail.  
* Fixed a Windows file lock issue by explicitly closing the SQLite connection between tests.  
* All tests pass locally.

**Command**  
`python -m unittest discover -s tests -p "test_safe_delete.py" -v`

---

### PR and process

* Opened a PR titled **Safe Insight Deletion and Python backend migration**.  
* Filled the template with a summary, manual steps, and unit test instructions.  
* Linked the work to **Issue 66 Safe Insight Deletion** so it closes on merge.  
* Left optional `api.py` in the repo so future Electron work can call the backend through HTTP without more plumbing.

---

### Reflection

This week was a pivot and a level up. We aligned the tech stack with the course rules and built a real safety net for our data. The safe delete feature feels like a platform piece since everything else can rely on it without fear of breaking references. The best part was seeing green tests after the Windows fix which gives the team confidence to keep building on top. Next I want to add a small retention policy for the trash and connect the CLI flows to FastAPI so the future UI can call the same paths.

---

## Week 10 Personal Log [Nov 3 – Nov 9, 2025]

This week I delivered the backend for **Retrieve Previously Generated Portfolio Information** and hardened our SQLite usage on Windows. I implemented clean read paths with pagination and a small REST surface, then hunted down a persistent file lock by guaranteeing the cached DB connection closes after CLI runs.

**Peer Eval**  
>
> ![Week 10 — Data Mining App]
> <img width="1064" height="615" alt="image" src="https://github.com/user-attachments/assets/1ab940a9-122d-444f-9bb6-58a40236c2ca" />


>
> _Figure 0. peer evaluation._

---

### Feature: Portfolio Retrieval backend and API

* Added `capstone/portfolio_retrieval.py` with:
  * `list_snapshots` (pagination, sorting, optional filters)  
  * `get_latest_snapshot` (latest per project)
  * `ensure_indexes` creating `(project_id, created_at)` index for fast reads
* Exposed minimal Flask endpoints:
  * `GET /portfolios/latest?projectId=...`
  * `GET /portfolios?projectId=...&page=&pageSize=&sort=created_at:desc`
* Standardized response envelope and simple Bearer token auth.

**Result**  
We can reliably retrieve previously generated portfolio snapshots by project, either the latest or a paginated list, and we are ready to plug a UI on top later for milestone 2.

---

### Stability: Windows SQLite lock fix

* Introduced a `_db_session` context manager that:
  * Normalizes `db_dir` to `Path` before calling `open_db`
  * Sets `PRAGMA journal_mode=DELETE` in tests
  * Always calls `close_db()` or `conn.close()` on exit
* Updated the CLI ranking handler to `finally: close_db()` so temp dirs can delete `capstone.db` without `[WinError 32]`.

---

### Testing and verification

* Wrote `tests/test_portfolio_retrieval.py` covering:
  * `test_get_latest_snapshot`
  * `test_list_snapshots_pagination`
  * `test_flask_latest_endpoint` (runs when Flask is installed)
* Full suite now passes locally on Windows:

---

### PR and process

* Opened PR for **Portfolio Retrieval Backend + Windows DB lock fix**.
* Filled template with summary, manual API steps, and unit test instructions.
* Linked to Issue **#60 Retrieve Previously Generated Portfolio Information** so it closes on merge.

---

### Reflection

This week was about making data access production ready and removing flaky platform issues. The retrieval layer gives us clean, testable reads with room to grow into GraphQL or richer filtering later. Fixing the Windows lock was a big quality of life win because it keeps our CI and local runs green. Next I want to add richer filters for contributor and classification, expose total counts consistently across endpoints, and draft a tiny frontend panel to verify results visually when the team prioritizes UI again.

---

## Week 12 Personal Log [Nov 17 – Nov 23, 2025]

This week I focused on getting our CLI workflow feeling like a real tool and shipping the first version of the job–matching pipeline. I wired up a `capstone` command that works cleanly inside a virtualenv, debugged the demo project so it writes proper snapshots to `project_analysis`, and built a backend that can take a pasted job description, extract skills, and compare them against a stored project.

**Peer Eval**  
>
> ![Week 12 — Data Mining App]
> <img width="1068" height="623" alt="image" src="https://github.com/user-attachments/assets/6ca71695-c9ae-4005-aaea-aea2ee76fc86" />

>
> _Figure 0. peer evaluation._

---

### Feature: End-to-end job description → project match (Step 1+2+3)

* Added a new `capstone.job_matching` module that:
  * Normalizes job descriptions and extracts skills using a curated `JOB_SKILL_KEYWORDS` dictionary (Python, C++, React, SQL, Docker, cloud tools, data/ML keywords, etc.).
  * Computes simple coverage scores so we know which required/preferred skills from the JD are actually present in a project’s skill list.
  * Returns a structured `JobMatchResult` that includes matched skills, coverage percentage, and a high-level “good match vs no strong match” verdict.
* Extended the CLI with a `job-match` subcommand:
  * `capstone job-match --project-id demo --db-dir data --job-file job_description.txt`
  * Loads the job text, fetches the latest snapshot for the given project from SQLite, runs the matching logic, and prints a friendly message (either listing matched skills or telling the user there isn’t a strong match yet).
* Laid groundwork for later steps:
  * The result object already exposes enough information for Step 4 to generate tailored resume snippets later.
  * The same extraction code can be reused by Step 3 when we start aggregating company-specific traits from multiple postings.

---

### Stability: Demo pipeline + metrics fixes

* Cleaned up the “demo” path so `run_demo()` now runs a full archive analysis, prints the summary, and then reads rows from `project_analysis` without schema errors (aliasing the internal `id` column as `project_id` in the sample query).  
* Used the demo output to verify that:
  * Collaboration snapshots now store `classification`, `primary_contributor`, and `skills` in a stable schema.
  * The skills JSON actually flows through end-to-end into the database, which is required for the new job-matching feature.
* Revisited the metrics extractor and chronological project view:
  * Confirmed that the `ongoing` flag works correctly so projects with no explicit end date show `Present` as their end when printing the timeline.
  * Checked that our metrics API still saves per-project summaries into `metrics.db` without Windows locking issues.

---

### CLI + environment wiring

* Installed the package in editable mode (`python -m pip install -e .`) so `capstone` is available as a command in the virtualenv instead of only as `python -m capstone.cli`.
* Verified that the job-matching command works inside the venv and that our new subcommand doesn’t interfere with existing ones like `analyze`, `clean`, or `rank-projects`.
* Documented the basic workflow for teammates:
  * Activate venv → run `capstone analyze ...` to ingest a zip.
  * Then run `capstone job-match ...` against that project to test the new feature.

---

### Testing and verification

* Created `tests/test_job_matching.py` using `unittest` to cover:
  * Basic keyword extraction from a realistic job description (ensuring keywords like “Python”, “C++”, “SQL”, “Docker”, “cloud” are picked up even when buried in text).
  * Matching logic on a fake project snapshot so we get deterministic coverage scores.
  * A CLI-level test that patches `open_db` / `fetch_latest_snapshot` to simulate both “good match” and “no match” scenarios.
* Re-ran the full test suite after the demo/schema fixes to confirm that:
  * The previous `project_analysis` mismatch is resolved.
  * Our metrics and demo helpers still behave the same from the tests’ perspective.

---

### PR and process

* Opened a PR for **Job Description Matching (Step 1+2) + Demo Pipeline Fixes**.
* Wrote a short summary explaining:
  * New `job-match` CLI and backend module.
  * Fix for the demo’s `project_analysis` SELECT that used the wrong column name earlier.
  * How to reproduce the flow locally (run `run_demo()` or `capstone analyze`, then `capstone job-match` with a JD file).
* Left notes in the issue thread to clarify that Step 3 (company-specific traits) and Step 4 (resume generation) will build on the JSON profile produced by the current code.

---

### Reflection

This week felt like moving from “toy script” to “actual product.” Getting `capstone` working as a first-class CLI command and debugging the demo DB issues gave me a much clearer picture of how all the pieces fit together. The new job-matching pipeline is still simple, but it already supports a realistic UX: paste a job posting, point at a project, and see whether your portfolio lines up or not. Next I want to 1) tighten the keyword extraction so it handles more phrasing variations, 2) support matching across *all* projects instead of just one `--project-id`, and 3) start shaping the JSON output so Step 4 can generate a polished resume section directly from these matches.

---

## Week 13 Personal Log [Nov 24 – Nov 30, 2025]

This week I focused heavily on finishing **Step 4: Full Resume Generation**, wiring it into our CLI, and transforming it into a real feature rather than a placeholder. I also worked on our capstone presentation slides for Wednesday.

**Peer Eval**  
>
> ![Week 13 — Capstone Resume Builder]
> <img width="645" height="689" alt="image" src="https://github.com/user-attachments/assets/83912a6c-fc4d-48bd-a86c-4dadda9ceb54" />
>
> _Figure 0. peer evaluation._

---

### Feature: End-to-end resume generation (Step 4)

This week I implemented the complete resume generator pipeline, taking the job-description matching output (Step 2), company profile (Step 3), and building a tailored resume with scored, ranked projects. Major pieces:

* Added a new `resume_pdf_builder.py` that converts the structured resume into Markdown and then a polished PDF using **Pandoc + wkhtmltopdf**, replacing the original toy PDF generator.
* Updated `resume_generator.py` so `resume_to_pdf()` now calls the new builder and produces clean, professional PDFs.
* Added Markdown formatting for skills, project bullets, values, and company traits to consistently render across systems.
* Ensured that JSON output still works for debugging and alternative formatting.

---

### SQLite persistence + CLI fixes

* Modified `_handle_analyze` so it properly writes project snapshots to SQLite using `store_analysis_snapshot()`—a critical requirement for Step 4 to read real data.
* Fixed SQLite file-lock issues on Windows by properly closing DB connections in both `analyze` and `generate-resume`. This resolved several `WinError 32` test failures.
* Reworked `--summary-to-stdout` so it outputs **pure JSON only** and does not pollute stdout with debug text, fixing the `JSONDecodeError: Extra data` failures in `test_cli`.
* Cleaned the code path so resume generation correctly loads all snapshots from SQLite via `fetch_latest_snapshots()`.

---

### PDF engine setup + environment work

Because we switched away from the toy PDF renderer, I debugged and resolved issues around dependency setup:

* Installed **Pandoc** system-wide and verified detection in the CLI.
* Installed **wkhtmltopdf** for Windows, fixed PATH issues, and documented how contributors should install it.
* Patched the PDF builder to use `wkhtmltopdf` instead of LaTeX engines, avoiding MiKTeX version mismatch errors.
* Confirmed that the CLI now renders PDF resumes without LaTeX-related failures.

---

### Testing and verification

I added a complete test suite for the resume generator:

* `tests/test_resume_generator.py` covers:
  * top-K project ranking  
  * skill-flag correctness  
  * JSON serialization  
  * PDF builder delegation (mocked Pandoc call)  
* Test suite also required documenting installation steps for Pandoc + wkhtmltopdf so teammates can reproduce the tests locally.
* Fixed several failures in `test_cli` including:
  * JSON pollution from debug prints  
  * open SQLite connection blocking temp folder cleanup  
  * missing return codes causing `exit_code is None`

After these patches, the test suite returns cleanly with all resume-related tests passing.

---

### Presentation preparation (Milestone demo)

I also worked on the **presentation** scheduled for Wednesday:

* Updated slide spacing and layout based on feedback.
* Reorganized content flow for the 5-step pipeline and ensured consistency with the resume-builder architecture.
* Included visuals and explanations from this week's work so the team can clearly present Step 4.

---

### PR and process

* Opened a PR titled **“Complete Resume Generator (Step 4) + PDF Engine + SQLite Snapshot Integration”**.
* Filled out the full PR template including instructions for installing Pandoc and wkhtmltopdf during testing.
* Included detailed code review notes, clear testing steps, and context on how the resume generator links previous steps together.
* Mentioned all breaking changes (new external dependencies) and described how they strengthen the overall pipeline.

---

### Reflection

This week was one of the most productive and challenging ones so far. I had to connect everything we built across Steps 1–3 and make it behave like a polished, real-world CLI tool. Debugging Windows path issues, Pandoc engines, JSON output, SQLite persistence, and test failures helped me fully understand how all the parts of our system interact. Seeing the pipeline finally produce a clean, well-formatted resume PDF felt like a massive milestone. We now have a full end-to-end workflow—from analyzing projects to generating a company-specific resume—working inside our CLI.

Next goals are to refine the resume layout, improve project bullet quality, and prepare the demo for Milestone #1.

---

## Week 14 Personal Log [Dec 1 – Dec 7, 2025]

This week I focused on laying the foundation for deeper LLM powered analysis in our capstone tool, so that later we can ask questions like whether a project has problems, how code or documentation can be improved, and get focused summaries for specific user needs. I also spent a lot of time finishing our presentation, doing mock practice, and helping the team get the video demo ready for the deadline.

**Peer Eval**  
>
> ![Week 14 — LLM Client and Demo Prep]
> <img width="644" height="692" alt="image" src="https://github.com/user-attachments/assets/bba0333a-e2cb-4090-822b-d6f0ca19cf49" />
>
> _Figure 0. peer evaluation._

---

### LLM client infrastructure for deeper insights

This week I implemented the first step of bringing an external LLM into our pipeline in a safe and testable way.

* Added a new `llm_client.py` module with an `OpenAILlmClient` class that wraps the OpenAI Responses API behind a simple `generate_summary(prompt)` method that matches what our `AutoWriter` expects.
* Implemented a `build_default_llm()` factory that only returns a real client when the OpenAI library is installed and `OPENAI_API_KEY` is present, otherwise it returns `None` so the rest of the system can fall back to offline analysis.
* Added a guarded import of `build_default_llm` in `top_project_summaries.py` so future steps can plug in LLM support without changing any existing behavior yet, which keeps the current ranking and summary logic stable.
* Made sure the new client fails softly by logging and returning an empty string when configuration is missing or a call fails, instead of crashing the CLI.

---

### Dummy LLM client and tests

To avoid burning credits while still wiring everything up, I added a dummy LLM implementation and tests for this new layer.

* Implemented `DummyLlmClient`, which never touches the network and returns a short, predictable prefix plus a trimmed snippet of the prompt so we can test prompts, formatting, and flow without using the real API.
* Created `tests/test_llm_client.py` using `unittest` to verify that the dummy client behaves as expected, that `build_default_llm()` returns `None` when there is no API key, and that `OpenAILlmClient` safely skips calls when misconfigured.
* Ran the tests locally and confirmed that the new module imports cleanly both with and without `OPENAI_API_KEY` set, which is important for contributors who may not have API access.
* Opened a pull request describing this as the first building block for LLM based project and document insights, and filled out the PR template with testing steps.

---

### Presentation finalization and mock practice

In parallel with coding, I continued working with my team to polish our presentation for the capstone milestone.

* Helped refine wording on the slides so the explanation of our steps fits within the time limit and is easier for classmates and instructors to follow.
* Did mock practice runs with the team before the actual presentation day, focusing on transitions between speakers and timing so we stay within our allotted slot and do not rush the important parts.

---

### Video demo preparation and coordination

We also needed to prepare our video demo that is due on Sunday, so I contributed to making sure that recording goes smoothly.

* Worked with my teammates to plan the demo flow so it clearly shows analysis, ranking, resume generation.
* Helped double check that the commands we plan to record run correctly on our machines, including database reads and CLI output, to avoid last minute technical issues during recording.
* Coordinated responsibilities for who records, who narrates, and who reviews the final cut so that the demo looks coherent and professional.
* Spent time running through the demo script to catch any rough edges before we record, especially around explaining technical details in simple language.

---

### Reflection

This week felt like a bridge between what we already built and the next level of intelligence we want from our tool. Adding the LLM client and dummy client did not change any user facing behavior yet, but it gives us a clean and safe way to start asking smarter questions about projects, code, and documents without breaking the existing system. At the same time, polishing the slides, doing mock presentations, and getting ready for the video demo helped me see the whole project as a unified story rather than separate features. Next steps are to hook the LLM adapter into `generate_top_project_summaries`, design prompts that target specific user questions, and finish strong with our final presentation and demo.

---

## Week 1 Personal Log [Jan 5 – Jan 11, 2026]

This week I focused on improving the reliability of our SQLite storage layer and adding unit test coverage around retrieving the latest analysis snapshots. The main goal was to unblock summarize projects workflows by ensuring we can consistently fetch one latest snapshot per project and avoid Windows file locking issues during tests.

**Peer Eval**  
>
> ![Week 1 — improving the storage]
> <img width="647" height="693" alt="image" src="https://github.com/user-attachments/assets/9be664b5-490d-4bd3-a886-bc14d13a1fdd" />
>
> _Figure 0. peer evaluation._

---

### Storage snapshot retrieval improvements

This week I reviewed and updated our `storage.py` logic related to reading snapshots from the database.

* Reviewed the updated `storage.py` implementation, including schema initialization and legacy backfill behavior for older rows.
* Improved the `fetch_latest_snapshot` query ordering to be deterministic by ordering on `created_at` and using `id` as a tie breaker, preventing ambiguity when timestamps match.
* Updated the `fetch_latest_snapshots` logic to reliably return one latest snapshot per project, even when multiple rows share the same timestamp, and added an optional limit to support returning only the most recently updated projects.
* Ensured invalid snapshot JSON does not crash the pipeline by safely defaulting to an empty snapshot payload when JSON parsing fails.

---

### Unittest coverage and Windows cleanup fixes

Most of the effort this week was making sure tests run consistently on Windows without leaving the database file locked.

* Added a dedicated unittest file `test_storage_latest_snapshots.py` to cover empty database behavior, multiple snapshots per project, deterministic tie breaking when timestamps match, limit ordering, and invalid JSON handling.
* Debugged repeated `WinError 32` failures during test cleanup and fixed the root cause by restructuring tests so database closure happens before temporary directory cleanup.
* Ran the storage specific tests locally with `python -m unittest discover -s tests -p "test_storage_latest_snapshots.py" -v` and confirmed all tests pass.

---

### PR preparation

To wrap the work cleanly, I prepared a PR with clear review information.

* Filled out the PR template with a concise description of the snapshot retrieval fix, test coverage details, and exact reproduction steps for running the tests locally.

---

### Reflection

This week was mostly about stability and correctness. The snapshot retrieval logic is now deterministic and test covered, and the test harness is structured in a way that behaves correctly on Windows. This should reduce friction for contributors and make it easier to build on summarize projects features without database edge cases breaking the flow. Next steps are to make sure the CLI summarize projects tests also consistently close database handles and to expand coverage around real CLI paths that depend on stored snapshots.

---

## Week 2 Personal Log [Jan 12 – Jan 18, 2026]

This week I focused on extending our CLI functionality by adding a new command to summarize top ranked projects based on the latest stored analysis snapshots. The main goal was to reuse the existing ranking and summary pipeline while exposing a clean, non conflicting CLI entry point, and to ensure the feature is properly tested using `unittest` within our src based project structure.

**Peer Eval**  
>
> ![Week 2 — summarize top projects CLI]
> <img width="648" height="690" alt="image" src="https://github.com/user-attachments/assets/13e8b6de-3391-4e38-a850-fc6fccec37d3" />
>
> _Figure 0. peer evaluation._

---

### New CLI command for top project summaries

This week I implemented a new CLI command to generate summaries for the highest ranked projects.

* Added a new `summarize-top-projects` command to avoid conflicts with the existing `summarize-projects` CLI entry.
* Wired the command to load the latest snapshot per project from the database and pass them through the existing ranking and summary generation pipeline.
* Ensured the command supports configurable limits, markdown or JSON output formats, and an optional `--use-llm` flag for enriched summaries.
* Normalized snapshot data at the CLI boundary to ensure compatibility with ranking logic that expects a dictionary keyed by project id.

---

### Debugging and error resolution

A significant portion of the week involved debugging integration issues and resolving edge cases discovered during manual testing.

* Diagnosed and fixed argparse subcommand conflicts caused by duplicate command names.
* Identified and corrected a data shape mismatch where snapshots were passed as a list instead of a dictionary.
* Resolved an import error related to an incorrect LLM builder name by aligning the CLI with the existing `build_default_llm` implementation.
* Verified correct behavior with sparse snapshot data, confirming that zero portfolio scores are expected when feature signals are limited.

---

### Unittest coverage for CLI functionality

I added unit test coverage to ensure the new CLI command is stable and does not regress.

* Created `unittest` based tests to validate that the `summarize-top-projects` command is correctly registered with argparse.
* Added handler level tests that mock database access and snapshot retrieval to verify end to end execution without relying on a real database or LLM.
* Fixed test import issues related to the src layout by updating `tests/__init__.py` to ensure the `capstone` package is discoverable during test runs.
* Ran all tests locally using `python -m unittest discover -s tests` and confirmed they pass consistently on Windows.

---

### PR preparation

To finalize the work, I prepared a clean pull request for review.

* Filled out the PR template describing the new CLI feature, testing strategy, and reproduction steps.
* Verified that the change is non breaking and integrates cleanly with existing summarize and ranking workflows.

---

### Reflection

This week was focused on integration and reliability rather than new algorithms. By reusing existing ranking and summary logic, the new CLI command adds useful functionality with minimal duplication. The added unit tests and fixes around src based imports improve long term maintainability and reduce friction for future contributors. Next steps include improving snapshot richness so ranking scores are more meaningful and expanding CLI coverage to include JSON output validation and edge case handling.

---

## Week 3 Personal Log [Jan 19 – Jan 25, 2026]

This week I focused on completing the remaining AI related milestones for the capstone project, specifically around improving AutoWriter prompt quality, integrating an AI powered project insight feature, and safely gating all LLM usage behind explicit user consent. The work involved prompt engineering, backend integration, environment configuration, graceful fallback handling, and comprehensive `unittest` coverage to ensure the system remains reliable and explainable even when external services are unavailable.

**Peer Eval**  
>
> ![Week 3 — AI insights and consent gating]
> <img width="1065" height="624" alt="image" src="https://github.com/user-attachments/assets/4553abfc-9c6a-44c7-9a10-cbab33b76187" />

>
> _Figure 0. peer evaluation._
>
---

### AutoWriter prompt restructuring for resume friendly summaries

A major portion of the week was spent improving the AutoWriter prompt construction to better align with resume and LinkedIn use cases.

* Updated the AutoWriter prompt to explicitly incorporate evidence references, contributor ownership, project timelines, and detected skills and tech stack.
* Added clear constraints to enforce concise, structured output, including a fixed number of bullet points, word limits, and mandatory evidence citations.
* Ensured the prompt highlights technical impact, contributor role, and growth over time rather than producing generic summaries.
* Verified that the updated prompt remains compatible with both LLM based summaries and offline fallback summaries.

---

### Unittest coverage for AutoWriter prompt shape

To ensure the new prompt structure is stable and regression resistant, I added targeted unit test coverage.

* Created `unittest` based tests to validate that the AutoWriter prompt includes required sections such as Ownership, Timeline, Skills and Stack, Evidence, and Output Instructions.
* Ensured tests assert intent and structure rather than brittle string equality, making them resilient to small formatting changes.
* Ran  tests locally using `python -m unittest` and confirmed consistent passing behavior.

---

### AI powered project insight feature

I implemented a new AI insight pipeline that allows users to ask free form questions about analyzed projects and receive evidence grounded responses.

* Added a stateless LLM client wrapper that isolates external API usage from core application logic.
* Built a structured prompt generator that derives context from stored project snapshots, rankings, collaboration data, and extracted evidence.
* Ensured the AI responses are grounded strictly in internal metadata rather than raw source code to avoid hallucination and excessive token usage.
* Verified the feature end to end by querying real project snapshots and validating that responses correctly identify strengths, weaknesses, activity levels, and collaboration patterns.

---

### Environment configuration and API key handling

While integrating the LLM client, I resolved several environment related issues specific to Windows and virtual environments.

* Diagnosed why environment variables set via `setx` were not visible inside the active virtual environment.
* Implemented a robust solution using session level environment variables and optional `.env` loading to ensure reproducible local development.
* Verified correct API key resolution inside the Python runtime using direct environment inspection.
* Confirmed that the system behaves correctly when API keys are missing, invalid, or rate limited.

---

### Graceful fallback and quota handling

To ensure system reliability, I added defensive handling around external API usage.

* Implemented graceful fallback behavior when the LLM API is unavailable due to quota limits or missing credentials.
* Ensured that fallback responses still provide meaningful offline summaries without crashing or blocking execution.
* Validated that the system remains fully functional even when external AI services are disabled.

---

### Consent gated LLM usage (Step 4)

The final major task this week was gating all LLM usage behind explicit user consent using the existing consent framework.

* Integrated the external consent system to require permission before any LLM call using a dedicated service identifier.
* Ensured consent decisions are remembered using the existing consent journal so users are not repeatedly prompted.
* Implemented a clean fallback path that skips AI analysis entirely when consent is denied.
* Added clear logging to make it explicit in debug output whether LLM usage was allowed or skipped.
* Verified correct behavior for both consent granted and consent denied scenarios through manual testing.

---

### Unittest coverage for consent gating

To validate consent behavior deterministically, I added unit tests that mock external dependencies.

* Created `unittest` based tests that verify the LLM is not invoked when external consent is denied.
* Added tests to confirm the LLM is invoked exactly once when consent is granted.
* Mocked snapshot retrieval, ranking logic, and LLM responses to ensure tests do not rely on external APIs.
* Ran the full test suite locally and confirmed all tests pass without warnings.

---

### PR preparation and review readiness

To wrap up the work, I prepared clean pull requests for each completed milestone.

* Filled out PR templates detailing design decisions, testing strategy, and expected behavior.
* Verified that all changes are non breaking and integrate cleanly with existing pipelines.
* Ensured PR descriptions clearly communicate AI usage, consent handling, and fallback behavior to reviewers.

---

### Reflection

This week emphasized system design, reliability, and responsible AI integration rather than introducing new algorithms. By grounding AI usage in stored metadata, gating it behind explicit user consent, and ensuring graceful degradation when external services are unavailable, the project now demonstrates production ready AI integration patterns. The added test coverage improves long term maintainability and ensures that future contributors can extend AI functionality without introducing regressions. Next steps include expanding documentation around AI usage and exploring additional CLI entry points for interactive project analysis.

---

## Week 4 Personal Log [Jan 26 – Feb 1, 2026]

This week I focused on stabilizing and extending several core CLI features in the capstone project, with an emphasis on usability, correctness, and end to end workflow completion. The main areas of work included fixing the chronological project timeline output, fully integrating the AI project insights feature into the main menu, and completing the resume pipeline by adding PDF export support with user selected save locations. Much of the work involved debugging edge cases, clarifying data flow across modules, and ensuring features behave predictably in real user scenarios. I worked on these changes based on the feedback we got from the peer testing.

**Peer Eval**  
>
> ![Week 4 — Timeline fixes, AI menu integration, resume export]
> <img width="1065" height="624" alt="image" src="https://github.com/user-attachments/assets/4553abfc-9c6a-44c7-9a10-cbab33b76187" />
>
> _Figure 0. peer evaluation._
>
---

### Chronological project timeline (Option 7) fixes

One major task this week was repairing and completing the chronological project timeline feature, which was previously incomplete and confusing.

* Investigated why start and end dates were showing as `Unknown` or incorrect and traced the issue to missing or uninitialized project metadata.
* Designed a clear data model where timeline information can be optionally provided by the user during project analysis rather than inferred unreliably from file timestamps.
* Added support for manually supplied start date, end date, and project status (ongoing or completed) during ZIP analysis.
* Persisted timeline metadata correctly in storage and ensured it is loaded consistently when rendering the timeline view.
* Updated Option 7 output to clearly display project name, active period, and status in a readable and meaningful format.
* Fixed multiple scope and initialization errors related to database connections and project ID resolution.

---

### AI project insights integration into the main menu

Another major focus was fully integrating the AI project insights feature into the main CLI menu so it is usable by end users.

* Connected the existing AI analysis pipeline to a dedicated main menu option.
* Added project selection logic that allows users to choose which analyzed project to send for AI analysis.
* Ensured the feature retrieves the latest snapshot per project and builds a structured prompt from stored metadata.
* Integrated the existing consent framework so all external LLM usage is explicitly gated and auditable.
* Diagnosed and fixed environment variable issues on Windows that prevented the API key from being detected at runtime.
* Verified end to end behavior by running real AI analyses and validating that insights are generated and displayed correctly.
* Added defensive handling for empty results, invalid selections, and missing configuration.

---

### Resume PDF export and save location selection

The final major task was completing the resume generation workflow by enabling users to export resumes as PDFs.

* Extended the auto generate resume option to prompt users for optional PDF export after previewing the resume.
* Integrated a system file save dialog so users can select where the PDF should be saved instead of hardcoding paths.
* Connected the resume preview data to the existing Pandoc based PDF builder.
* Fixed path handling issues by standardizing on `pathlib.Path` instead of raw strings.
* Debugged rendering issues where sections were missing and ensured project summaries render correctly in the PDF.
* Verified that generated PDFs are written successfully and open correctly outside the application.

---

### Resume content validation and skill aggregation

While testing the PDF output, I identified gaps in the resume content itself.

* Discovered that project skills were not appearing in the generated resume despite being present in analysis metadata.
* Traced the issue to missing skill propagation into resume entries rather than a PDF rendering bug.
* Updated the resume markdown generator to aggregate skills from project items when available.
* Ensured the resume output remains robust even when some sections (experience, education, achievements) are missing.

---

### Debugging and integration work

Across all features, a significant portion of the work involved debugging and integration.

* Resolved multiple `UnboundLocalError` and scope related bugs in the CLI flow.
* Used targeted debug output to inspect deeply nested resume and snapshot structures.
* Ensured database connections are consistently opened and closed across menu options.
* Verified that new features do not break existing functionality or navigation flow.

---

### PR preparation and issue tracking

To conclude the week, I prepared the work for review and integration.

* Created and updated GitHub issues to clearly define feature scope and expected behavior.
* Filled out PR templates documenting design decisions, testing steps, and known limitations.
* Ensured changes are isolated, non breaking, and aligned with milestone requirements.

---

### Reflection

This week was heavily focused on turning partially implemented features into complete, user ready workflows. Rather than adding new high level functionality, the work emphasized correctness, clarity, and integration across modules. Fixing the timeline feature, exposing AI insights through the main menu, and completing the resume export pipeline significantly improve the usability and perceived polish of the application. The system now better reflects real world usage patterns, where users expect features to be discoverable, configurable, and persistent. Next steps include refining resume section coverage and expanding documentation for the new CLI options.

---

## Week 5 Personal Log [Feb 2 – Feb 8, 2026]

This week I focused on reviewing, completing, and validating the FastAPI backend for the capstone project to ensure it fully supports the required frontend and CLI workflows. The main goal was to close remaining API gaps, and performing manual end to end testing using Postman.

**Peer Eval**  
>
> ![Week 5 — API completion and Postman testing]
> <img width="1605" height="933" alt="image" src="https://github.com/user-attachments/assets/d228c899-b84e-4936-af37-0bf9beeffdf9" />
>
> _Figure 0. peer evaluation._
>
---

### API audit and missing endpoint analysis

A major task this week was performing a full audit of the existing FastAPI routes to ensure all required functionality is properly exposed and no critical lifecycle operations were missing.

* Reviewed all existing API route files including consent, projects, skills, resume, and portfolio routes.
* Compared implemented endpoints against the capstone requirements and frontend usage patterns.
* Identified that while consent could be set via the API, there was no endpoint to retrieve the current consent state.
* Identified that uploaded projects could not be deleted, leaving an incomplete project lifecycle.
* Confirmed that all resume, portfolio, and AI driven generation endpoints were already functionally complete and correctly scoped.

---

### Consent API completion

To improve privacy transparency and frontend usability, I extended the consent API.

* Added a `GET /privacy-consent` endpoint to allow clients to query the current consent state.
* Ensured consent handling remains explicitly gated and simple, without exposing AI internals.
* Verified that consent can be set and retrieved correctly through the API.
* Confirmed that AI powered generation endpoints remain implicitly protected behind consent checks.

---

### Project lifecycle completion

To close the remaining CRUD gap in the projects API, I added project deletion support.

* Implemented `DELETE /projects/{project_id}` to remove uploaded projects.
* Ensured associated database records and stored files are cleaned up correctly.
* Verified that deleted projects no longer appear in project listings and cannot be accessed afterward.
* Confirmed that deletion does not impact unrelated snapshots, resume entries, or portfolio data.

---

### Postman based API testing

To support team testing and demonstration requirements, I validated the API using Postman.

* Installed and configured Postman for manual API testing.
* Tested core endpoints including health checks, consent handling, project upload, project deletion, and resume generation.
* Verified correct request and response behavior outside of Swagger UI.
* Captured screenshots of successful requests and responses for documentation and reporting.
* Confirmed that Postman testing complements existing Swagger based testing rather than replacing it.

---

### PR preparation and documentation

To conclude the work, I prepared the changes for review and integration.

* Filled out a detailed PR template describing the added endpoints and design rationale.
* Documented testing steps and validation methods clearly.
* Ensured all changes are non breaking and isolated to API surface improvements.
* Marked additional potential endpoints such as project reanalysis as future work rather than in scope changes.

---

### Reflection

This week focused on turning an already functional API into a complete and defensible system. By auditing the existing endpoints, filling small but important gaps, and validating the design of the AI integration, the backend now cleanly supports the full consent to upload to generate workflow. Using Postman for external testing also strengthens the project’s credibility by demonstrating that the API behaves correctly outside of the built in Swagger interface. Overall, this work improved the completeness, clarity, and polish of the system without introducing unnecessary complexity.

---

## Week 6 Personal Log [Feb 9 – Feb 15, 2026]

This week I focused on extending the capstone CLI AI workflow by adding an optional deeper code review feature. The main goal was to let users upload a project archive, select specific source files, and request targeted AI feedback on bugs, improvements, and suggested fixes while keeping the consent model explicit and safe. A significant portion of the work also involved rebuilding my local environment after a hard reset, restoring Python tooling, and validating the feature with repeatable `unittest` coverage.

---

### Environment recovery and tooling setup

A prerequisite for completing the work was restoring my development environment after a hard reset.

* Reinstalled Python and verified interpreter availability from PowerShell.
* Recreated the project virtual environment and reinstalled required dependencies.
* Reconfigured the `OPENAI_API_KEY` environment variable and validated visibility inside the activated venv.
* Diagnosed configuration issues where the key was set but the OpenAI client dependency was missing, and ensured the LLM integration could initialize correctly.

---

### Deep AI code review feature design

I designed a deeper AI analysis path that builds on the existing AI insights feature without breaking the current workflow.

* Kept the existing AI insights flow intact and added an optional deep review step after the normal project insights output.
* Implemented a bounded “code bundle” approach to avoid sending entire archives to the LLM and to keep requests small and predictable.
* Ensured the deep review route uses explicit external permission gating with clear messaging that selected source files will be shared.
* Structured the prompt to include snapshot context (languages, file summary, collaboration context) alongside the selected code files for better quality suggestions.

---

### Code selection and bundling logic

To support selective deep analysis, I implemented a small pipeline for selecting files and packaging them for the prompt.

* Added ZIP scanning to enumerate reviewable source files based on a controlled set of textual extensions.
* Implemented a file selection experience where users choose files by index rather than typing file names.
* Added bundling safeguards including maximum file count, maximum total size, and per file truncation to prevent oversized prompts.
* Added basic redaction behavior for obvious secret looking lines before sending content to the LLM.

---

### Prompt construction and output formatting

I focused on making deep review output usable directly in the CLI.

* Built a dedicated deep review prompt builder that formats selected files with clear boundaries and includes metadata context.
* Adjusted prompt instructions so the returned output is readable in the console instead of rigid JSON only responses.
* Validated the integration end to end by selecting a real ZIP, picking specific files such as SQL migrations and Python entrypoints, granting consent, and confirming the response is printed correctly.

---

### Testing and validation using unittest

To lock in the behavior and prevent regressions, I added targeted unit tests.

* Wrote `unittest` coverage for the code bundler to verify inclusion filtering, extension rules, truncation behavior, total size limits, and redaction behavior.
* Wrote `unittest` coverage for the deep review prompt builder to ensure snapshot context, question text, and file blocks are correctly included and robust to missing snapshot fields.
* Ran the tests locally and confirmed they pass consistently after environment rebuild.

---

### Debugging and integration fixes

Several small issues surfaced during integration, and I fixed them systematically.

* Resolved import mismatches caused by function naming differences between the bundler implementation and the call site.
* Fixed a prompt builder call signature mismatch that caused runtime errors during deep review execution.
* Fixed a CLI bug where the deep question variable was referenced before definition and corrected a parenthesis error that broke the try block.
* Verified the final flow works end to end through the main menu without adding new CLI arguments.

---

### Reflection

This week focused on adding a practical and user friendly “deep review” feature while keeping our consent and privacy posture explicit. The feature now supports a realistic workflow where users can choose exactly which files to send for analysis instead of dumping an entire project, and the new unit tests provide confidence that bundling and prompt formatting behavior will remain stable. The extra time spent recovering my local environment also helped me ensure that the setup and dependency assumptions are clear and reproducible for future development and peer testing.

---

## Week 8 Personal Log [Feb 23 – Mar 1, 2026]

This week I focused on designing and implementing a fully functional real time System Health dashboard inside our Electron frontend, backed by a new FastAPI system metrics endpoint. The primary goal was to transform a static UI card into a production quality monitoring panel that displays CPU, memory, GPU, storage usage, temperatures, health status, and live mini charts. A significant portion of the work involved backend hardware integration, resolving Windows monitoring constraints, and polishing frontend visualization logic for smooth real time updates.

**Peer Eval**  
>
> ![Week 8 — forntend mock design]
> <img width="1071" height="621" alt="image" src="https://github.com/user-attachments/assets/e77e15af-a801-4047-9dbb-50b3182e0b80" />
>
> _Figure 0. peer evaluation._
>
---

### Backend system metrics endpoint design

I began by designing and implementing a new `/system/system-metrics` API endpoint in FastAPI to provide live hardware metrics to the Electron frontend.

* Implemented CPU usage retrieval using `psutil`.
* Implemented memory usage, used GB, and total GB calculations.
* Implemented storage usage as a fallback metric when GPU is not detected.
* Integrated Libre Hardware Monitor (running in background mode) to extract CPU and GPU temperature data.
* Resolved COM and threading issues related to WMI access and migrated to Libre’s `data.json` HTTP endpoint for stable metric extraction.
* Ensured GPU detection logic gracefully falls back to storage metrics when no GPU is present.
* Added CORS middleware to allow Electron to fetch backend metrics.
* Verified correct JSON structure and validated endpoint behavior via Swagger and direct requests.

---

### Background hardware monitor integration

To avoid requiring a visible monitoring window in production, I implemented automatic Libre Hardware Monitor startup in headless mode.

* Configured Libre to expose `data.json` via its internal web server.
* Ensured it launches silently without displaying a UI window.
* Validated that the monitoring service runs reliably in the background when the app starts.
* Confirmed that JSON polling is stable and does not block the backend process.

---

### Electron frontend system health card redesign

The existing static “System Health” card was redesigned into a fully dynamic monitoring component.

* Replaced static content with SVG based half arc gauges for CPU, Memory, and GPU.
* Implemented dynamic stroke dash offset animation for real time gauge updates.
* Added system status indicator using `/health` endpoint with green and red visual state.
* Integrated CPU and GPU temperature display beneath each gauge.
* Structured HTML and CSS to ensure proper alignment and prevent overflow beyond card boundaries.
* Converted a single chart implementation into three independent mini charts aligned beneath each respective gauge.

---

### Real time chart implementation and refinement

To improve clarity and usability, I refined the visualization logic for live usage trends.

* Implemented three separate Chart.js instances for CPU, Memory, and GPU.
* Added sliding window history buffers to maintain the last 40 data points.
* Increased stroke width for improved visual clarity.
* Adjusted layout so each chart is directly positioned under its corresponding gauge.
* Eliminated rendering crashes caused by scope errors and misplaced metric references.
* Ensured all DOM updates are synchronized with fetch intervals to prevent stale UI states.

---

### Dynamic usage based color gradients

To improve visual feedback and make the dashboard feel more production ready, I implemented dynamic gauge coloring.

* Designed a continuous gradient interpolation function for usage values from 0 to 100.
* Implemented smooth blending from green (low usage) to yellow (medium) to red (high).
* Applied dynamic color updates directly to SVG stroke properties.
* Extended color logic to update chart line colors based on current usage values.
* Verified smooth transitions without abrupt threshold jumps.

---

### Debugging and stability improvements

Several frontend and backend integration issues surfaced and were resolved.

* Fixed a scope error where metrics were referenced outside of `fetchMetrics()`, causing runtime crashes.
* Resolved GPU percentage text not updating despite arc animation working.
* Fixed intermittent GPU usage update issues caused by mixed data sources.
* Ensured all fetch calls include error handling to prevent silent UI freezes.
* Confirmed consistent one second polling behavior without blocking Electron rendering.

---

### Reflection

This week significantly improved the professionalism and technical depth of the project. The System Health card evolved from a placeholder UI element into a fully functional real time monitoring panel powered by custom backend hardware integration and dynamic frontend visualization. The combination of background hardware monitoring, structured API design, SVG animation, and gradient based usage indicators demonstrates strong full stack integration and attention to detail. The result is a responsive and production quality dashboard component that enhances both usability and technical sophistication of the application.
