# COSC499 Team 127 Personal Log - Parsa Aminian (41202862)

## Week 3 Personal Log [Sept 15 – Sept 21, 2025]

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
