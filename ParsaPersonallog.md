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
> ![Week 6 — Data Mining App](![alt text](Assets/Peer%20Eval%20Week%205.png))
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
