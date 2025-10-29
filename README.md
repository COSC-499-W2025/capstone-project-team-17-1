# Capstone Analyzer (Python)

Local, consent-aware archive analysis implemented entirely in Python – no Electron dependencies required. Use the `capstone` CLI to manage consent preferences and to extract metadata, collaboration insights, languages, frameworks, and timeline metrics from zipped projects.

## Quickstart

```bash
# (Optional) create and activate a virtual environment before running commands
python -m venv .venv
source .venv/bin/activate

# Install the package in editable mode
pip install -e .

# Record consent for analysis
capstone consent grant

# Analyse an archive (results saved to analysis_output/ by default)
capstone analyze /path/to/project.zip

# Stream the summary JSON to the terminal
capstone analyze /path/to/project.zip --summary-to-stdout

# Run the Python unit test suite (config, consent, CLI, metrics, etc.)
python -m unittest discover -s tests -p "test_*.py" -v
```

Key features:
- Encrypted local configuration that stores consent decisions, analysis preferences, and last-opened folders.
- Consent workflow that blocks analysis until users explicitly grant permission.
- JSONL metadata with per-file language classification and activity type (code, documentation, asset, other).
- Collaboration labelling (individual vs collaborative) driven by Git log evidence found within the archive.
- Automatic fallback to local analysis whenever external processing is unavailable or not approved.
- Rich summary including language counts, framework detection (from `requirements.txt`/`package.json`), activity timeline, and scan duration.
- Entire test suite is Python-based; use `python -m unittest ...` rather than `npm test`.
- Additional helpers replicate legacy Electron behaviours: config reset/validation, interactive consent prompting, markdown detection for Node/Electron apps, and skill confidence scoring.

# Work Breakdown Structure
[Link to WBS](docs/Plan/wbs.md)
# Milestone #1
The focus of this milestone is to create the functionality for parsing and outputting information correctly. We will be very particular about your system design and testing approach during this phase. All the output for this milestone is expected to be in text (that is, you can opt for a CSV, JSON, plain text output, etc., or a combination that facilitates your future development). The specific requirements are below.
The system must be able to ... :

## 1.0 User Interaction and Consent Module
  - 1.1 Data Access Consent
      - 1.1.1 Display user consent dialog before data access
      - 1.1.2 Record and store consent decision
      - 1.1.3 Block operations for users who have not granted consent
  - 1.2 External Service Permission
      - 1.2.1 Request explicit permission to use external LLM or APIs
      - 1.2.2 Display privacy implications and data usage details
      - 1.2.3 Implement fallback (local) analysis if external service is not approved

## 2.0 Parse a specified zipped folder containing nested folders and files
  - 2.1 Verify the .zip extension
  - 2.2 Iterate through nested folders inside the zip
  - 2.3 For each file: extract path, size, modified time
  - 2.4 Build artifact records with unique IDs
  - 2.5 Store parsed metadata as JSON lines
  - 2.6 Generate summary: number of files, total bytes, scan duration

## 3.0 Return an error if the specified file is in the wrong format
  - 3.1 Detect non-zip inputs (e.g .pdf, .jpg .exe)
  - 3.2 Define standard error schema: { "error": "InvalidInput", "detail": "..."}
  - 3.3 Store the error logs

## 4.0 Request User Permission Before Using External Services
  - 4.1 Current Status
      - At this stage of the project (Milestone #1), the system does not use any online tools or AI models (like LLMs). All analysis happens locally on the user’s computer. However, this module prepares the system for future milestones where online or AI-based features might be added (for example, a cloud analysis tool or an AI summary generator).
  - 4.2 Consent and Transparency
      - Whenever external processing is introduced in the future, the system will:
          - Display a clear consent message before any data is shared.
      - Inform the user about:
          - What data will be sent (e.g., text or metadata).
          - Why it is being sent (e.g., for generating summaries or analytics).
          - Where it is going (e.g., a trusted API).
          - How privacy and data storage are handled.
          - Offer options to Allow Once, Always Allow, or Deny, and remember the user’s choice.
          - Record each response with a date, time, and user ID for transparency.
          - Block any external request if permission is denied.
  - 4.3 Expected Outcome
      - Users clearly understand any future privacy implications and will always have control over their data.
      - During this milestone, no data leaves the computer, and the system remains fully local and privacy-safe.

## 5.0 Have Alternative Analyses in Place If Sending Data to an External Service Is Not Permitted
  - 5.1 Purpose
      - Ensure the software continues to function completely even when users do not allow online processing or when the computer is offline.
  - 5.2 Implementation Plan
      - Provide offline (local) analysis options for all major features, such as detecting programming languages, skills, and user contributions.
      - Only disable optional online tools (for example, AI summaries) if permission is denied.
      - Keep the same output style (JSON, CSV, or text) for both online and offline modes.
      - Display a small “Local Analysis Mode” label so users know their data is being processed only on their computer.
      - Test both local and online modes to confirm that results remain consistent.
  - 5.3 Expected Outcome
      - The system stays fully operational, accurate, and privacy-friendly even without internet access or user consent for external processing.

## 6.0 Store User Configurations for Future Use
  - 6.1 Purpose
      - Save each user’s settings and preferences so they do not have to reset everything every time they open the program.
  - 6.2 Implementation Plan
      - Store preferences such as last opened folder, analysis mode, and theme in a small configuration file or database table.
      - Include the user’s consent choice in these saved settings.
      - Protect private details through basic encryption.
      - Automatically load saved settings when the program starts.
      - Provide a “Reset Settings” button to restore default values.
      - Update saved settings whenever the user changes preferences.
  - 6.3 Expected Outcome
      - User configurations are remembered across sessions, creating a smooth, consistent, and personalized experience each time the software is used.

## 7.0 Distinguish Individual Projects from Collaborative Projects
  - 7.1 Purpose
      - Identify whether a project was completed by one person or by a team, so that contribution reports and rankings are fair and accurate.
  - 7.2 Implementation Plan
      - Review project information and Git commit logs to find how many contributors worked on each project.
      - Classify projects as:
          - Individual – one author only.
          - Collaborative – multiple contributors.
      - Measure the main user’s contribution level (e.g., number of commits or lines of code).
      - Exclude automated accounts or bots from the contributor count.
      - Show this information in project summaries, dashboards, and ranking lists.
  - 7.3 Expected Outcome
      - Each project is correctly labeled as individual or collaborative.
      - This allows fair evaluation of personal work and teamwork in reports and summaries.

## 8.0 Identify Coding Programming Language and Framework
  - 8.1 Technology Identification Module
      - 8.1.1 Identify supported programming languages
      - 8.1.2 Identify supported frameworks
  - 8.2 Language Detection Algorithm
      - 8.2.1 Implement file-type and syntax-based language recognition
      - 8.2.2 Validate detection accuracy across multiple repositories
  - 8.3 Framework Identification Process
      - 8.3.1 Parse dependency files
      - 8.3.2 Extract and classify framework usage
  - 8.4 Integration and Reporting
      - 8.4.1 Store metadata in database for later use 

## 9.0 Collaboration Analysis Module
  - 9.1 Define Data Collection Process
      - 9.1.1 Identify version control systems (Retrieve commit logs, pull requests)
  - 9.2 User Contribution Mapping
      - 9.2.1 Parse commits and associate each change with an individual
      - 9.2.2 Handle shared accounts and automated commits
  - 9.3 Contribution Extrapolation
      - 9.3.1 Weight contributions based on lines of code, commits, and review activity
      - 9.3.2 Normalize results for equal comparison
  - 9.4 Metric Visualization
      - 9.4.1 Export data summaries (CSV, JSON, dashboard/portfolio view)

## 10.0 Metrics Extraction Module
  - 10.1 Define Key Metrics (duration, frequency, volume)
  - 10.2 Implement Activity Classification
    10.2.1 Classify contributions (.py = code, .md = doc)
  - 10.3 Timeline Analysis
      - 10.3.1 Find activity trends over project cycle
      - 10.3.2 Identify active and inactive phases

## 11.0 Extract Key Skills
  - 11.1 Extract Technical Skills
      - 11.1.1 Identify languages, frameworks, libraries, and tools used per individual
  - 11.2 Extract Project-Related Skills
      - 11.2.1 Infer collaboration, documentation, and testing skills from activity data
  - 11.3 Create Skill Profiles
      - 11.3.1 Summarize individual and team-level skillsets
      - 11.3.2 Export skills data for portfolio integration

## 12.0 Output all the key information for a project
  - 12.1 Group artifacts by project ID
  - 12.2 Compute file counts, sizes, types, first & last modified dates
  - 12.3 Create timeline (histogram of activity per day/week)
  - 12.4 Produce JSON summary for the project (CSV / TXT may also be used)
  - 12.5 Handle edge cases (duplicate files, null dates, missing types)

## 13.0 Store Project Information into a Database
  - 13.1 Database Schema Design
    - 13.1.1 Define entity models (Project, Skill, Contribution, UserConfig)
    - 13.1.2 Establish relationships between entities (e.g., Project ↔ User, Project ↔ Skill)
    - 13.1.3 Create indexing and foreign keys for efficient retrieval
  - 13.2 Database Implementation
      - 13.2.1 Initialize database (e.g., MySQL/Prisma schema migration)
      - 13.2.2 Implement ORM models for CRUD operations
      - 13.2.3 Configure environment variables and connection settings
  - 13.3 Data Insertion Workflow
      - 13.3.1 Serialize parsed project data into standardized format
      - 13.3.2 Insert project summary and related metadata into tables
      - 13.3.3 Log transaction results and handle insertion errors
  - 13.4 Data Validation and Backup
      - 13.4.1 Verify record integrity after insertion
      - 13.4.2 Create data backup or export routines for versioning

## 14.0 Retrieve Previously Generated Portfolio Information
  - 14.1 Query Design
      - 14.1.1 Define SQL/ORM queries to fetch stored portfolio data
      - 14.1.2 Optimize query performance using indexes
      - 14.1.3 Add pagination and sorting for scalable display
  - 14.2 API or Service Layer Implementation
      - 14.2.1 Build REST/GraphQL endpoint for portfolio retrieval
      - 14.2.2 Implement authentication and access control
      - 14.2.3 Integrate error-handling and response standardization
  - 14.3 Frontend Integration
      - 14.3.1 Create a dashboard or visualization component for viewing portfolios
      - 14.3.2 Format retrieved data into user-friendly summaries
      - 14.3.3 Enable download/export of portfolio data (e.g., JSON, PDF)

## 15.0 Retrieve Previously Generated Résumé Item
  - 15.1 Data Model and Linking
      - 15.1.1 Identify résumé-related data structures in the database
      - 15.1.2 Map résumé entries to corresponding project or skill data
  - 15.2 Retrieval Logic
      - 15.2.1 Implement backend queries for specific résumé sections
      - 15.2.2 Support keyword-based and date-based filtering
      - 15.2.3 Handle missing or outdated résumé entries gracefully
  - 15.3 Output and Formatting
      - 15.3.1 Convert retrieved résumé data into standardized résumé format (Markdown, JSON, PDF)
      - 15.3.2 Display résumé preview in the application interface
      - 15.3.3 Enable export or integration with résumé generation tools

## 16.0 Rank importance of each project based on user's contributions
  - 16.1 Create the weight algorithm
  - 16.2 Extract features and transform to numeric weight value (artifact count, total bytes, recency, activity, diversity)
  - 16.3 Sort projects by score
  - 16.4 Output ranked list with breakdown of factors and weights

## 17.0 Top Project Summaries
  - 17.1 Summary template
  - 17.2 Evidence Gatherer for pull PR links, commits, issues, benchmark)
  - 17.3 Auto-Writer (offline first; optional LLM use)
  - 17.4 Hallucination guardrails (quote facts, add refs, confidence flags)
  - 17.5 Exporters (Markdown, PDF one-pager, README snippet)

## 18.0 Safe Insight Deletion
  - 18.1 Insight catalog and IDs (give every insight a stable identifier)
  - 18.2 Dependency graph (graphs for files/artefacts it references)
  - 18.3 Reference counting/ownership (don’t delete files with refcount > 0)
  - 18.4 Safe-delete workflow (dry-run, preview, confirm, purge)
  - 18.5 Audit and redo (trash bin and log of deletion)
 
## 19.0 Chronological list of projects
  - 19.1 Date policy (start/end commit merged to main unless overridden)
  - 19.2 Timeline extractor (range per repo + tag/releases)
  - 19.3 Sorting and bucketing (year/quarter; overlapping projects handled)
  - 19.4 Output views (table, Markdown timeline)
  - 19.5 Gap handling (unknown dates to “undated” bucket with reason)

## 20.0 Chronological list of skills 
  - 20.1 Skill taxonomy (language, framework, tool, domain; map via files/PR labels)
  - 20.2 Skill detector (per commit/release via file extensions, package manifests)
  - 20.3 Time Attribution (first seen, last active, active spans)
  - 20.4 Aggregation (per year/quarter, intensity score)
  - 20.5 Exports (skill timeline table, “top skills by year” chart data)

# DFD Level 1
https://github.com/COSC-499-W2025/capstone-project-team-17-1/blob/docs-finalization/docs/design/dfd.md
<img width="1229" height="754" alt="image" src="https://github.com/user-attachments/assets/ee6a44e8-8e9b-46e8-8527-83f5b632fe49" /><br/>


The Level 1 DFD outlines how user-selected sources are processed to extract, analyze, and visualize digital artifacts.The process begins when a User selects sources, triggering the upload module to scan and detect files. These are processed by identifying file types, eliminating corrupt files, and extracting information. During this stage, the system will record an error log for any unreadable or corrupted files in the logs database for troubleshooting.

Processed files are categorized and metrics are derived. These metrics are saved in the database and then passed to the visualization module to create dashboard/portfolio reports for the user.

Additionally, users are able to search, filter, and save generated portfolios in the database. This allows them to retrieve/export for external use whenever they desire. All actions are tracked through logs. The data flow concludes with the final outputs returned to the user, completeing a clear and transparent user-controlled cycle.


# system_architecture_design
https://github.com/COSC-499-W2025/capstone-project-team-17-1/blob/docs-finalization/docs/design/system_architecture_design.md
<img width="1617" height="1074" alt="image" src="https://github.com/user-attachments/assets/38a4aacd-d73c-4b7a-a808-a95611492823" /><br/>


The document proposes a local first app that mines a user’s own files to help them understand and showcase their work history. It targets students and early professionals who want clear timelines, trends, and portfolio style summaries without sending data off the device. In scope are scanning chosen folders, classifying common file types, deduplicating with strong hashes, storing results in a local data store, and presenting dashboards plus simple exports. Users control what is scanned, can pause or resume, and see transparent previews and progress with errors surfaced. Typical use cases include presentations, reviews, resumes, and quick retrospectives.

Functionally, the system lets a user pick sources, crawls and classifies artifacts, builds searchable indexes and filters by time, type, project, and path, and produces insights like activity timelines and type distributions. Non functional goals stress fast setup, efficient and resumable scans, responsiveness, accessibility, and strong privacy and security. Data stays local with least privilege, encrypted storage using the operating system keystore, a localhost only API with per session tokens, secure deletion, and redaction of sensitive patterns in cached snippets. Maintainability expectations include straightforward developer setup, high automated test coverage, pinned dependencies, signed releases, and clear documentation.

For an initial milestone, the team should ship source selection, common type detection, hashing into SQLite with indexes, a live progress bar with pause and resume, basic dashboards for timeline and type distribution, search and filters, delete from index, a minimal local API, and CSV or JSON export with a preview. Success looks like accurate classification for most common types, a medium scan that completes within minutes on a typical laptop, common interactions that respond within a couple of seconds, and users reporting that the visualizations improve their understanding of their work. Key risks are privacy leaks, interruptions, and performance slowdowns, addressed by on device processing with redaction, checkpoint and resume, and resource caps with a light scan mode.
