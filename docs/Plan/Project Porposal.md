# COSC 499 Capstone Software Engineering Project  
**Mining Digital Work Artifacts – Team 17 (2025/26)**  

**Week 4 — Project Proposal**  
**Authors:** Parsa Aminian, Raunak Khanna, Yuxuan Sun, Shuyu Yan, Michelle Zhou

---

## 1. Project Scope and Usage Scenario

We’re building a **local-first desktop tool** that gives users a clear account of their work activity. After installation, users select folders or GitHub repositories to analyze. The system iterates across many artifact types—source code, documents, downloads, design files, images, and videos—and processes results into a unified dashboard.

The dashboard reports **what was worked on**, **where effort went**, and **how progress is trending**, including **percentage-based indicators** inspired by Workday’s degree tracker. Users can drill down from any chart to the exact files or commits that produced a metric (avoiding “black-box” analytics).

**Who benefits:**
- **Students:** export structured reports (PDF/CSV) to strengthen CVs and portfolios.
- **Early-career software engineers:** present verified evidence for appraisals.
- **Project managers / HR:** review artifact-based progress rather than self-reported claims.

**Why this approach is distinctive:**
- **Privacy:** everything runs on-device; exports can use aggregation and light noise.
- **Breadth:** unifies diverse artifact types, not just code or cloud sources.
- **Engagement:** milestones and lightweight badges (in the spirit of Khan Academy) motivate without cluttering the professional focus.

**Reliability & Security:** resumable scans, integrity checks, CPU throttling, cross-platform support, encrypted database, token-protected local API, and export audit logs.

**Future-friendly:** modular design for résumé/LinkedIn exports, optional cloud storage or Jupyter integrations, and team dashboards.

---

## 2. Proposed Solution

A **desktop application** that turns scattered digital artifacts into structured, verifiable insights while keeping all processing on the user’s device.

**Pipeline (high-level):**
1. User selects folders or repos.
2. System scans code, documents, images, videos, downloads, and design files.
3. Extracts details (names, types, sizes, timestamps); removes duplicates via hashing.
4. Organizes results into categories and surfaces timelines, balances, and progress indicators.
5. Every metric is traceable; clickthrough reveals the underlying files/commits.

---

## 3. Use Cases

### Use Case 1 — Installation and Setup
- **Primary Actor:** User  
- **Precondition:** Installer downloaded  
- **Postcondition:** App installed locally and ready  
- **Main Scenario:**  
  1. User runs installer  
  2. System installs components  
  3. User launches app  
- **Extension:** Insufficient permissions → notify user and prompt re-install.

### Use Case 2 — Import Artifacts
- **Primary Actor:** User  
- **Precondition:** App running  
- **Postcondition:** Selected resources registered for processing  
- **Main Scenario:**  
  1. Click **Add Resource**  
  2. Browse local folders/repos  
  3. System confirms and adds to sources  
- **Extension:** Inaccessible repo → pop-up notification.

### Use Case 3 — Analyze Artifacts
- **Primary Actor:** System  
- **Precondition:** At least one source added  
- **Postcondition:** Artifacts scanned and categorized  
- **Main Scenario:**  
  1. User selects **Scan Sources**  
  2. System identifies files (docs, code, media)  
  3. Extracts metadata  
  4. Removes duplicates  
  5. Stores locally  
- **Extension:** Corrupted file → skip and log error.

### Use Case 4 — View Metrics
- **Primary Actor:** User  
- **Precondition:** Artifacts analyzed  
- **Postcondition:** Metrics displayed  
- **Main Scenario:**  
  1. Navigate to **Metrics**  
  2. Select a project  
  3. System shows charts/graphs  
- **Extension:** No projects → prompt to import artifacts.

### Use Case 5 — Generate Portfolio
- **Primary Actor:** User  
- **Precondition:** Resources analyzed and organized  
- **Postcondition:** Viewable portfolio ready to save/export  
- **Main Scenario:**  
  1. Click **Generate**  
  2. Review selected data  
  3. System compiles report  
- **Extension:** Insufficient artifacts → prompt to add sources.

### Use Case 6 — Store Portfolio
- **Primary Actor:** User  
- **Precondition:** Portfolio created  
- **Postcondition:** Portfolio stored and retrievable  
- **Main Scenario:**  
  1. Click **Save**  
  2. System stores in database  
  3. System organizes/categorizes  
- **Extension:** Attempt to save too early → prevent and notify.

### Use Case 7 — Search and Filter Artifacts
- **Primary Actor:** User  
- **Precondition:** Artifacts imported and organized  
- **Postcondition:** Relevant artifacts displayed  
- **Main Scenario:**  
  1. Enter keywords/apply filters  
  2. System searches indexes  
  3. Results returned  
- **Extension:** No matches → notify user.

### Use Case 8 — Export/Share Portfolio
- **Primary Actor:** User  
- **Precondition:** Portfolio created  
- **Postcondition:** Portfolio exported in chosen format  
- **Main Scenario:**  
  1. Click **Export**  
  2. Choose format  
  3. System generates export  
- **Extension:** File too large → system splits export.

---

## 4. Requirements, Testing, and Verification

### Tech Stack

- **Application Form:** Electron desktop app, local-first, offline by default  
  Process model: Renderer (UI) + Main Process  
- **Renderer:** React + TypeScript (or Vue); Charts: Recharts or ECharts; UI kit: Tailwind  
- **Main:** Node.js + TypeScript  
- **Database:** SQLite  
- **CI/CD:** GitHub Actions  
- **Testing:** Vitest (unit), React Testing Library (component)

### Functional Requirements (with tests)

| Requirement | Description | Test Cases | Owner | Difficulty |
|---|---|---|---|---|
| Artifact Scanning | Scan a selected directory and identify supported types (code, docs, images) | Positive: select a directory → files detected; Negative: empty folder → no results; Error handling: invalid path | Parsa | Medium |
| Metadata Extraction | Extract file path, size, type, timestamp | Positive: verify metadata for known files; Negative: very large file; Negative: corrupted file | Parsa | Medium |
| Database Insertion | Store extracted artifact metadata in DB schema | Positive: insert known files and query; Negative: avoid duplicates; Schema validation | Yuxuan | Hard |
| Search & Filter | Search by type, date, keyword | Positive: code-only search; Filter by time; Edge: no matches | Shuyu | Medium |
| Privacy / Opt-Out | Exclude directories or delete scanned artifacts | Positive: mark folder ignored → no scan; Delete record → verify DB removal; Edge: delete non-existent record | Yuxuan | Hard |
| Performance & Scalability | Handle large datasets efficiently | Scan 10,000 files within 10 s; Stress test with 1 GB+ media; Negative: no read permission → clear error | Raunak | Hard |
| Data Integrity | Prevent data loss across crashes | Simulate crash mid-scan → data persists; Normal restart → data still available; Export DB → verify | Michelle | Hard |
| Export & Reporting | Export artifacts/metrics as CSV/JSON | Positive: valid dataset exports; Empty dataset → valid empty file | Raunak | Medium |
| Cross-Platform Compatibility | Run on Windows/Mac/Linux | Path parsing on Win/Linux; UI launches on Mac; Unsupported OS → clear error | Parsa | Medium |
| Error Logging | Record errors for debugging and support | Normal ops → no error logs; Invalid path → log; DB failure logged correctly | Michelle | Medium |
| User Authentication | Secure login before accessing artifacts | Valid login; Invalid password; Session timeout | Yuxuan | Medium |
| Generate Productivity Metrics | Compute metrics (#artifacts, time trends, complexity indicators) | Positive: generate for 10 artifacts; Negative: empty dataset; Performance: large dataset < 5 s | Michelle | Hard |
| Store Portfolio | Save portfolio with artifacts + metrics | Positive: save & reload; Negative: prevent saving empty; Error: DB disconnected | Shuyu | Medium |
| Generate Highlights | Auto-generate key project highlights | Positive: top 3 largest/most recent artifacts; Negative: no artifacts → “no highlights”; Validate highlight text | Shuyu | Hard |
| Export & Share Portfolio | Export/share portfolio as CSV/JSON | Positive: CSV fields correct; Empty portfolio → valid empty file; Share link opens | Raunak | Medium |

---

## 5. Proposed Workload Distribution

### Ownership Areas and Success Metrics

1. **Ingestion & Preprocessing (core coding)**  
   Design and implement file discovery, type detection, hashing, metadata extraction, and queuing.  
   **Success:** end-to-end ingest speed ≥ **200 files/min** on a typical laptop; zero data loss; reproducible hashes.

2. **Metadata Schema & Storage (coding + indexes)**  
   Define canonical schema and implement indexed persistence for fast queries.  
   **Success:** typical lookups **< 100 ms** for filters like type, owner, date, project tag.

3. **Privacy & Security Guardrails (coding)**  
   Local-only mode, selective redaction, permission checks, secure deletion workflow.  
   **Success:** redaction applied to all designated fields verified by automated tests + manual spot-check script.

4. **Analytics & Insights (coding)**  
   Features: recency, velocity, uniqueness score, basic clustering of similar items.  
   **Success:** top five insights correct on a seeded demo workspace and validated against ground truth.

5. **CI, Testing, and Dev Tooling (coding and git)**  
   Unit/integration tests, data fixtures, smoke test runner.  
   **Success:** **90%** pipeline coverage; green build on `main`; **one-command** local setup.

6. **Architecture Docs & Demos (presentation and doc)**  
   System architecture diagram, data-flow diagrams, short demo script.  
   **Success:** teammates can explain the pipeline in **≤ 2 minutes** using the diagram and script.

### Team Roles

- **Parsa Aminian:** ingestion & preprocessing, documentation & demos, artifact scanning, metadata extraction, cross-platform readiness.  
- **Michelle Zhou:** productivity metrics, data integrity, error logging, accurate analysis.  
- **Shuyu Yan:** portfolio persistence, search/filter mechanisms, automated highlight generation.  
- **Raunak Khanna:** data processing, front-end and back-end development, test support.  
- **Yuxuan Sun:** database schema design, runtime read/write & storage, performance optimization, participation in FE/BE design and system testing.

---

## Sprint Plan and Deliverables

**Sprint 1 — Discovery & Scaffolding**  
- Deliverables: ingestion spikes for code and PDF, draft metadata schema, repo structure, minimal run script.  
- Collaboration: align on tech stack and success metrics.

**Sprint 2 — Ingestion MVP**  
- Deliverables: directory crawl, type sniffing, hashing, basic metadata extraction, local storage, ten unit tests, ingest CLI.  
- Collaboration: API contract with search/UI teammate.

**Sprint 3 — Indexing & Query**  
- Deliverables: indexed storage, filter & sort, pagination, query benchmarks, profile report, fifteen tests.  
- Collaboration: simple service endpoint handoff for UI integration.

**Sprint 4 — Privacy Pass**  
- Deliverables: redaction rules, local-only switch, secure delete workflow, audit log, threat-model checklist, tests.  
- Collaboration: quick UX for redaction review with UI owner.

**Sprint 5 — Analytics v1**  
- Deliverables: recency/velocity features, similarity fingerprints, top five insights per user, validation notebook.  
- Collaboration: align on insight copy/cards.

**Sprint 6 — Performance & Scale**  
- Deliverables: parallel ingestion, batched writes, backpressure, memory caps, large-catalog benchmarks, tuning notes.  
- Collaboration: coordinate end-to-end scenarios.

**Sprint 7 — Polish & Docs**  
- Deliverables: refined architecture diagram, runbook, contributor guide, troubleshooting, demo script, sample dataset.  
- Collaboration: dry-run final presentation.

**Sprint 8 — Release & Handoff**  
- Deliverables: tagged release, reproducible demo environment, metrics snapshot, postmortem, and backlog.

---

## Interfaces and Collaboration Points

1. **Storage Interface**  
   CRUD for artifacts and a search endpoint with filters.  
   **Consumers:** search module and UI.

2. **Event Hooks**  
   Events: artifact discovered/indexed/redacted/deleted.  
   **Consumers:** analytics module and UI notification bar.

3. **Redaction Policy File**  
   YAML/JSON declaring fields to mask or drop.  
   **Consumers:** ingestion pipeline and UI redaction review.

---

## Risks and Mitigations

1. **Heterogeneous File Types**  
   **Mitigation:** plugin extractor pattern; graceful fallback to raw metadata.

2. **Large Catalogs**  
   **Mitigation:** streaming, batching, memory ceilings with backpressure.

3. **Privacy Gaps**  
   **Mitigation:** redaction-first defaults; explicit allow-lists; unit tests with realistic fixtures.
