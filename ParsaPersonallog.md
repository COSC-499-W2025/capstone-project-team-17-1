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

