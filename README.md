# Capstone Analyzer (Python)

Capstone Analyzer is a local-first software analysis tool for processing project archives and generating portfolio/resume-oriented insights.  
The system supports three workflows: CLI analysis, interactive menu usage, and FastAPI HTTP endpoints.

## Tips
For any ZIP upload, make sure to run the following command in the project’s root directory before compressing it:
```
git log --pretty=format:"commit:%H|%an|%ae|%ct|%s" --numstat > git_log.txt
```
This generates the required commit metadata file for parsing.

Alternatively, for greater convenience, you can directly provide the GitHub repository URL along with an API token to perform repository-based analysis via the GitHub API.

## Quickstart

```bash
# 1) Clone repository
git clone https://github.com/COSC-499-W2025/capstone-project-team-17-1.git
cd capstone-project-team-17-1

# 2) Create virtual environment
python -m venv .venv
```

Activate virtual environment:

```bash
# macOS/Linux
source .venv/bin/activate
```

```powershell
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```cmd
REM Windows (Command Prompt)
.venv\Scripts\activate.bat
```

```bash
# 3) Install package
pip install -e .

# 4) Install dev/API dependencies
pip install -r requirements-dev.txt

# 5) Quick verification
capstone --help
```

Requirements:
- Python 3.10+
- pip
- git

## Usage

Run mode guidance:
- `CLI (capstone ...)` - best for scripted/local automation and reproducible analysis runs.
- `Interactive Menu (python main.py)` - best for guided demos and manual workflows.
- `FastAPI Backend (capstone api ...)` - best for frontend integration, API clients, and HTTP-based testing.

### Run CLI

```bash
# consent
capstone consent local grant

# analyze local zip
capstone analyze /path/to/project.zip

# optional: import and analyze repository
capstone import-repo https://github.com/<org>/<repo>.git

# optional: print summary JSON
capstone analyze /path/to/project.zip --summary-to-stdout
```

### Run Interactive Menu

```bash
python main.py
```

Input shortcuts in interactive mode:
- `b` = back
- `m` = main menu
- `Enter` = cancel current prompt (where supported)

### Run API Backend

```bash
# Start FastAPI on port 8003
capstone api --host 127.0.0.1 --port 8003 --db-dir data
```

Base URL: `http://127.0.0.1:8003`

API docs:
- Swagger UI: `http://127.0.0.1:8003/docs`
- OpenAPI JSON: `http://127.0.0.1:8003/openapi.json`
- Route debug (mounted routers + import errors): `http://127.0.0.1:8003/__debug/routers`

## API Route Map (Overview)

### System
- `GET /` - API status
- `GET /health` - health check

### Consent
- `POST /privacy-consent` - save privacy consent choice
- `GET /privacy-consent` - get current privacy consent

### Projects
- `POST /projects/upload` - upload `.zip` and create/update project snapshot
- `GET /projects` - list uploaded projects
- `GET /projects/{id}` - get project details
- `DELETE /projects/{id}` - delete project
- `GET /projects/{id}/uploads` - list all uploads for a project
- `PATCH /projects/{id}` - update project overrides (role, evidence, resume/portfolio edits)
- `GET /projects/{id}/overrides` - get project overrides

### Skills
- `GET /projects/{project_id}/skills` - detect skills for a specific project
- `GET /skills` - aggregate skills across projects

### Resume
- `GET /resume` - list/search resume entries
- `POST /resume` - create resume entry
- `GET /resume/{id}` - get resume entry
- `PATCH /resume/{id}` - update resume entry
- `DELETE /resume/{id}` - delete resume entry
- `POST /resume/generate` - generate resume output (`json|markdown|pdf`)
- `POST /resume/render-pdf` - render resume payload to PDF (base64 response)
- `GET /resume-projects` - list/get project-specific resume wording
- `POST /resume-projects` - upsert project-specific resume wording
- `POST /resume-projects/generate` - auto-generate resume wording from snapshots

### Portfolio / Showcase
- `GET /portfolio/{id}` - get portfolio/showcase summary for project
- `POST /portfolio/generate` - generate portfolio summaries
- `POST /portfolio/{id}/edit` - edit project portfolio summary
- `GET /showcase/...` - showcase-prefixed aliases
- `GET /portfolios/...` and `GET /users...` - legacy compatibility aliases

Note:
- Full endpoint details, payload shapes, and extra aliases are documented in `docs/api.md`.

## API Route Map (Table)

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/` | API status | Implemented |
| GET | `/health` | Health check | Implemented |
| POST | `/privacy-consent` | Save privacy consent | Implemented |
| GET | `/privacy-consent` | Get privacy consent | Implemented |
| POST | `/projects/upload` | Upload zip and store project snapshot | Implemented |
| GET | `/projects` | List projects | Implemented |
| GET | `/projects/{id}` | Get project details | Implemented |
| DELETE | `/projects/{id}` | Delete project | Implemented |
| GET | `/projects/{id}/uploads` | List project uploads | Implemented |
| PATCH | `/projects/{id}` | Update project overrides | Implemented |
| GET | `/projects/{id}/overrides` | Get project overrides | Implemented |
| GET | `/projects/{project_id}/skills` | Get detected skills for project | Implemented |
| GET | `/skills` | Aggregate skills across projects | Implemented |
| GET | `/resume` | List/search resume entries | Implemented |
| POST | `/resume` | Create resume entry | Implemented |
| GET | `/resume/{id}` | Get resume entry | Implemented |
| PATCH | `/resume/{id}` | Update resume entry | Implemented |
| DELETE | `/resume/{id}` | Delete resume entry | Implemented |
| POST | `/resume/generate` | Generate resume (`json|markdown|pdf`) | Implemented |
| POST | `/resume/render-pdf` | Render resume payload as PDF | Implemented |
| GET | `/resume-projects` | List/get resume wording by project | Implemented |
| POST | `/resume-projects` | Upsert project resume wording | Implemented |
| POST | `/resume-projects/generate` | Auto-generate resume wording | Implemented |
| GET | `/portfolio/{id}` | Get portfolio/showcase summary | Implemented |
| POST | `/portfolio/generate` | Generate portfolio summaries | Implemented |
| POST | `/portfolio/{id}/edit` | Edit portfolio summary | Implemented |
| GET | `/showcase/*` | Showcase-prefixed aliases | Implemented |
| GET | `/portfolios/*`, `/users/*` | Legacy compatibility aliases | Implemented |

## Example Requests

Upload a project zip:

```bash
curl -X POST "http://127.0.0.1:8003/projects/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/project.zip;type=application/zip"
```

List projects:

```bash
curl "http://127.0.0.1:8003/projects"
```

Get project skills:

```bash
curl "http://127.0.0.1:8003/projects/<project_id>/skills"
```

Generate resume JSON:

```bash
curl -X POST "http://127.0.0.1:8003/resume/generate" \
  -H "Content-Type: application/json" \
  -d '{"format":"json","limit":20}'
```

## Testing

Backend/API:

```bash
python -m pytest
```

Alternative unittest run:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Testing notes:
- API endpoints are tested with FastAPI TestClient through HTTP-style requests.
- Prefer `python -m pytest` to avoid interpreter/environment mismatch.
- Coverage focuses on API route behavior (status codes/payloads), core analysis/storage logic, and CLI-related integration paths.

## Additional Notes

- `requirements-dev.txt` includes API/test deps: `fastapi`, `httpx`, `pytest`, `python-multipart`, `uvicorn`.
- PDF export requires a LaTeX engine. On macOS you can use:

```bash
./scripts/setup.sh
```

## Test Data ZIPs

The repo includes sample ZIPs for demos and validation under `test_data/`:
- `test_data/test-data-code-collab-earlier.zip`
- `test_data/test-data-code-collab-later.zip`
- `test_data/test-data-multi-projects.zip`
- Source bundle for regeneration: `test_data/multi_project_bundle/`

# Work Breakdown Structure
# Milestone #1
[Link to WBS](docs/Plan/wbs.md)
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
  - 17.2 Evidence Gatherer for pull PR links, commits, issues, benchmark
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

## 21.0 Allow incremental information by adding another zipped folder of files for the same portfolio or résumé
  - 21.1 Support uploading additional zipped folders for an existing portfolio or résumé
  - 21.2 Merge newly added files with previously ingested artifacts
  - 21.3 Preserve existing project data and user customizations across uploads

## 22.0 Recognize duplicate files and maintains only one in the system
  - 22.1 Generate unique identifiers (e.g., hashes) for all ingested files
  - 22.2 Detect duplicate files across multiple uploads
  - 22.3 Maintain a single canonical copy of duplicated files in the system

## 23.0 Allow users to choose which information is represented
  - 23.1 Allow manual re-ranking of projects
  - 23.2 Enable user corrections to project chronology
  - 23.3 Allow selection of attributes for project comparison
  - 23.4 Allow selection of skills and projects for showcase

 ## 24.0 Incorporate key role of the user in a given project
  - 24.1 Capture the user’s primary role within each project
  - 24.2 Store role information as part of project metadata

## 25.0 Incorporate evidence of success for a given project
  - 25.1 Associate quantitative metrics with projects
  - 25.2 Allow inclusion of qualitative feedback or evaluations
  - 25.3 Persist evidence of success for later display

## 26.0 Allow user to associate an image for a given project to use as the thumbnail
  - 26.1 Allow user to upload or select an image for a project
  - 26.2 Associate the image with the project as a thumbnail
  - 26.3 Store and retrieve image metadata

## 27.0 Customize and save information about a portfolio showcase project
  - 27.1 Customize project descriptions for portfolio presentation
  - 27.2 Save portfolio-specific project information
  - 27.3 Maintain user-defined showcase settings

## 28.0 Customize and save the wording of a project used for a résumé item
  - 28.1 Customize concise project wording for résumé use
  - 28.2 Save résumé-specific project descriptions
  - 28.3 Support updates without affecting portfolio text

## 29.0 Display textual information about a project as a portfolio showcase
  - 29.1 Generate textual representations of projects for portfolio display
  - 29.2 Include user-selected content, roles, and evidence

## 30.0 Display textual information about a project as a résumé item
  - 30.1 Generate résumé-ready textual project descriptions
  - 30.2 Display only résumé-selected projects and wording

# DFD Level 1
https://github.com/COSC-499-W2025/capstone-project-team-17-1/blob/docs-finalization/docs/design/dfd.md
<img width="1134" height="569" alt="image" src="https://github.com/user-attachments/assets/4c2d9c6b-ff7a-452c-85e7-b1f4403be251" />
<br/>


The Level 1 DFD outlines how user-selected sources are processed to extract, analyze, and visualize digital artifacts.The process begins when a User selects sources, triggering the upload module to scan and detect files. These are processed by identifying file types, eliminating corrupt files, and extracting information. During this stage, the system will record an error log for any unreadable or corrupted files in the logs database for troubleshooting.

Processed files are categorized and metrics are derived. These metrics are saved in the database and then passed to the visualization module to create dashboard/portfolio reports for the user.

Additionally, users are able to search, filter, and save generated portfolios in the database. This allows them to retrieve/export for external use whenever they desire. All actions are tracked through logs. The data flow concludes with the final outputs returned to the user, completeing a clear and transparent user-controlled cycle.


# system_architecture_design
https://github.com/COSC-499-W2025/capstone-project-team-17-1/blob/docs-finalization/docs/design/system_architecture_design.md
<img width="1617" height="1074" alt="image" src="https://github.com/user-attachments/assets/38a4aacd-d73c-4b7a-a808-a95611492823" /><br/>


The document proposes a local first app that mines a user’s own files to help them understand and showcase their work history. It targets students and early professionals who want clear timelines, trends, and portfolio style summaries without sending data off the device. In scope are scanning chosen folders, classifying common file types, deduplicating with strong hashes, storing results in a local data store, and presenting dashboards plus simple exports. Users control what is scanned, can pause or resume, and see transparent previews and progress with errors surfaced. Typical use cases include presentations, reviews, resumes, and quick retrospectives.

Functionally, the system lets a user pick sources, crawls and classifies artifacts, builds searchable indexes and filters by time, type, project, and path, and produces insights like activity timelines and type distributions. Non functional goals stress fast setup, efficient and resumable scans, responsiveness, accessibility, and strong privacy and security. Data stays local with least privilege, encrypted storage using the operating system keystore, a localhost only API with per session tokens, secure deletion, and redaction of sensitive patterns in cached snippets. Maintainability expectations include straightforward developer setup, high automated test coverage, pinned dependencies, signed releases, and clear documentation.

For an initial milestone, the team should ship source selection, common type detection, hashing into SQLite with indexes, a live progress bar with pause and resume, basic dashboards for timeline and type distribution, search and filters, delete from index, a minimal local API, and CSV or JSON export with a preview. Success looks like accurate classification for most common types, a medium scan that completes within minutes on a typical laptop, common interactions that respond within a couple of seconds, and users reporting that the visualizations improve their understanding of their work. Key risks are privacy leaks, interruptions, and performance slowdowns, addressed by on device processing with redaction, checkpoint and resume, and resource caps with a light scan mode.

## Team Contract
https://docs.google.com/document/d/1Lw_CeWKMtIAGRbn4z4xmESP87En25rSU8GsUcTXPijQ/edit?usp=sharing
## Vision and Goals

We strive to be a team that is respectful, reliable, and supportive.
Our goals include:
1. Deliver a high quality project that meets the course requirements and the needs of our client.
2. Help each other learn new skills and grow throughout the term.
3. Communicate early and openly so that problems are handled effectively.
4. Share responsibilities in a way that is balanced and transparent.

## Expectations

### Meetings

- **Punctuality and General Attendance:** Everyone will be present at meetings.
- **Preparedness:** Everyone comes to meetings having completed their agreed tasks, reviewed the agenda, and looked at any shared documents or code that will be discussed.
- **Engagement:** During meetings, everyone participates in the discussion, listens to others, and raises concerns or ideas. Side conversations or multitasking should be kept to a minimum so we stay focused.
- **Documentation:** Meetings minutes and decisions will be recorded in a shared space (Discord) within 24 hours of each meeting.

### Communication and Collaboration

- **Frequency of Communication:** Communication will be done on Discord. Everyone will check messages at least once per day and respond to direct questions within twenty four hours.
- **Communication Behaviour:** All communication must remain respectful and professional. There will be no insults, sarcasm aimed at team members, or inappropriate jokes. If there is a misunderstanding, we will clarify rather than assume with bad intent.
- **Channels for Discussions:** Quick questions and updates happen in the discord channel. Planning and major decisions happen in scheduled meetings or voice calls. Technical issues and tasks are tracked in a kanban board so that work is visible to everyone.
- **Collaboration Process:** If two or more members are collaborating on a task, they will first agree on a clear goal, delegate responsibilities. They will keep each other updated on progress and blockers, and review each other’s work before presenting it to the rest of the group.

## Resolution Strategy

**In the event of a conflict, we will:**

1. Seek to understand the interests and concerns of each party involved before arriving at any conclusion.
2. Speak and listen without judgement or aggression, and respond with constructive, specific feedback.
3. NOT involve any personal issues or disagreements outside the scope of the capstone project.
4. Document key decisions and agreed-upon action items so expectations are clear to everyone.

**In the event a member wants to execute the Firing Clause, we will:**

1. Communicate directly with the member in question, clearly explaining the concerns.
2. Provide a reasonable timeline and concrete expectations for improvement.
3. Document all major discussions and warnings related to performance or behaviour.
4. Revisit after the agreed-upon timeline to assess efforts of improvement and whether change has been made.

Firing will only be considered as a last resort, after attempts have been made to resolve the issue. Additionally, all members must be in agreement and the final decision must be unanimous.

## Distribution and delivery of work

**Tasks:** Project tasks are defined in the GitHub README and Issues tab.
**Task Pick Up:** After the initial WBS is posted, each member claims the same number of major tasks, refines them in a shared Google Doc, then moves them into the README and creates/assigns matching GitHub issues.
**Task Delegation:** Because everyone’s tasks are clearly assigned from the beginning, conflicts occur at a minimum. The team will meet regularly to support progressing towards the end product. If conflicts arise, team members will communicate actively to resolve them and/or collectively choose the best solution.
**Task Accountability:** Each issue will have a clear assignee(s) and rough due date (end of each cycle); the assignee will be responsible for completing it on time with acceptable quality. Work will only be merged after approved peer reviews.

### Statement on commitment to avoid inappropriate behavior

1. **Respectful Environment**

- We will treat each other with respect regardless of background, identity, or skill level. Discriminatory or harassing behaviours will not be accepted in any form.

2. **Academic Integrity**
   
- All work will follow the course and university rules. We will not plagiarize, share forbidden materials, or misrepresent our contributions.

3. **Professional Conduct Online and In Person**

- Messages, comments, and code reviews must stay constructive. We will focus on the work, not personal attacks. When giving feedback, we will address the task or behaviour, not the person.

## Other ground rules

1. **Take responsibility for mistakes:** When something goes wrong, we own it, fix it, and learn from it without hiding or shifting blame.

2. **Honour meeting norms:** We arrive on time, stay focused, and let people finish their thoughts. Cameras and mics are used appropriately during virtual meetings.

I am committed to contributing to a team environment where everyone feels respected, supported, and able to work safely. I will treat my teammates with fairness, listen actively, and communicate in a way that maintains a positive and collaborative atmosphere. I understand that a respectful environment is essential for trust and effective teamwork.
I also commit to upholding academic integrity in all shared work. This includes being honest about my contributions, completing tasks responsibly, and following course and institutional guidelines. I recognize that integrity within a team protects the quality of our work and ensures that every member’s efforts are acknowledged.
I will conduct myself professionally both online and in person. This means communicating thoughtfully, using appropriate language, being mindful of tone, and avoiding any behaviour that could harm or undermine others. I will take responsibility for my actions, and when unsure about expectations, I will seek clarification rather than make assumptions.
My goal is to support a team culture built on respect, honesty, and professionalism, so that every member can participate comfortably and contribute meaningfully.

## Names and Signatures

By signing below, each member confirms that they have read, understood, and agreed to this team contract.

Member Name: **Parsa Aminian** Signature: **Parsa.A**  Date: **11/24/2025**

Member Name: **Yuxuan Sun** Signature: **Yuxuan Sun**  Date: **11/24/2025**

Member Name: **Raunak Khanna** Signature: **Raunakk>.** Date: **11/24/2025**

Member Name: **Shuyu Yan** Signature: **Shuyu yan** Date: **11/24/2025**

Member Name: **Michelle Zhou** Signature: **Michelle Zhou** **Date: 11/24/2025**
