# Capstone Analyzer (Python)

Capstone Analyzer is a local-first software analysis tool for processing project archives and generating portfolio/resume-oriented insights.  
The system supports three workflows: CLI analysis, interactive menu usage, and FastAPI HTTP endpoints.

## README Navigation

- [Quickstart(involve Windows instruction--open loom)](#quickstart)
- [Installation Guide for Future Development Team](#installation-guide-for-future-development-team)
- [OpenAI API key (developers and testers)](#openai-api-key-developers-and-testers)
- [MAC instruction--open loom](#mac-instruction--open-loom)
- [Usage](#usage)
- [API Route Map (Table)](#api-route-map-table)
- [Test Report](#test-report)
- [Known Bugs](#known-bugs)
- [Test Data ZIPs](#test-data-zips)
- [Work Breakdown Structure](#work-breakdown-structure)
- [DFD Level 0](#dfd-level-0)
- [DFD Level 1](#dfd-level-1)
- [system_architecture_design](#system_architecture_design)
- [Team Contract](#team-contract)

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

# 5) Install LaTeX (required for PDF resume export)
#    macOS / Linux:
bash scripts/setup.sh
#    Windows (PowerShell, run as Administrator):
.\scripts\setup.ps1

# 5b) OpenAI API key — set before starting the backend if you use LLM-backed features (Sienna, error analysis, etc.).
#     Windows (Command Prompt or PowerShell):  setx OPENAI_API_KEY "your_api_key_here"
#     Then close and reopen your terminal so the variable is picked up.
#     Details, macOS/Linux, and why we cannot ship a shared key: see "OpenAI API key" under the Installation Guide below.

# 6) Run Backend
#    macOS:
python -m capstone.run_server
#    Windows:
capstone api --host 127.0.0.1 --port 8003 --db-dir data

# 7) Run Frontend
#    macOS /  Windows:
cd frontend
npm start
```

Requirements:
- Python 3.10+
- pip
- git
- tkinter (required by the file picker in CLI interactive flows)
  - Ubuntu/Debian: `sudo apt-get install python3-tk`
  - macOS/Windows: usually included with standard Python installers

## Installation Guide for Future Development Team

This section is the recommended setup path for the next team working on the repository.

### Deliverables Navigation

| Deliverable / Review Topic | Where to start |
|---|---|
| Installation guide for future developers | [Installation Guide for Future Development Team](#installation-guide-for-future-development-team) |
| Backend source code | [`src/capstone/`](src/capstone) |
| CLI entry point | [`src/capstone/cli.py`](src/capstone/cli.py) |
| Interactive app entry point | [`main.py`](main.py) |
| FastAPI server | [`src/capstone/api/server.py`](src/capstone/api/server.py) |
| API reference | [`docs/api.md`](docs/api.md) |
| Electron frontend | [`frontend/`](frontend) |
| Python backend tests | [`tests/`](tests) |
| Frontend tests | [`frontend/test/`](frontend/test) |
| Demo and regression ZIPs | [`test_data/`](test_data) |
| Setup scripts | [`scripts/`](scripts) |
| Frontend startup (macOS) | [MAC instruction--open loom](#mac-instruction--open-loom) |
| Known limitations and workarounds | [Known Bugs](#known-bugs) |
| OpenAI API key setup | [OpenAI API key (developers and testers)](#openai-api-key-developers-and-testers) |

### 1. Clone and create a Python environment

```bash
git clone https://github.com/COSC-499-W2025/capstone-project-team-17-1.git
cd capstone-project-team-17-1
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Install backend dependencies

```bash
pip install -e .
pip install -r requirements-dev.txt
```

Why both commands are used:
- `pip install -e .` installs the package in editable mode for development.
- `requirements-dev.txt` adds test, API, and optional integration dependencies used across the repo.

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

The Electron frontend test suite is under `frontend/test/`, and `npm install` is required before running packaged frontend workflows.

### 4. Install system-level tools when needed

- LaTeX is required for PDF resume export.
- Run `bash scripts/setup.sh` on macOS/Linux.
- Run `.\scripts\setup.ps1` on Windows PowerShell as Administrator.
- `tkinter` is required for some interactive CLI file-picking flows.

### 5. Verify the environment

Backend:

```bash
capstone --help
python -m pytest tests/test_config.py -q
```

Frontend:

```bash
cd frontend
node --test test/**/*.test.mjs
cd ..
```

### 6. Start the main workflows

- CLI: `capstone analyze /path/to/project.zip`
- Interactive menu: `python main.py`
- API server: `capstone api --host 127.0.0.1 --port 8002 --db-dir data`

### 7. Environment notes for future teams

- The Python package target is [`src/capstone/`](src/capstone).
- Main backend entry points are [`main.py`](main.py) and the CLI entry defined from [`src/capstone/cli.py`](src/capstone/cli.py).
- The Electron app lives in [`frontend/`](frontend).
- API route details are documented in [`docs/api.md`](docs/api.md).
- Sample archives for demos and regression checks live in [`test_data/`](test_data).
- The current test suite assumes local filesystem access for generated app data and logs.

### OpenAI API key (developers and testers)

Several features (including LLM-backed HTTP routes and tooling that uses [`src/capstone/llm_client.py`](src/capstone/llm_client.py)) expect an **`OPENAI_API_KEY`** environment variable. Without it, those features return configuration errors or fall back where implemented.

#### Why we do not put a key in this repository

**Do not commit API keys to GitHub.** OpenAI and similar providers routinely **detect, revoke, or block keys** that appear in public repositories, gists, or other leaked locations. For that reason this project **does not include a shared team API key** in the repo. **Developers and testers must supply their own key**, or use a **pre-built / course-distributed application** if one is provided that already bundles or configures access appropriately.

#### Windows (recommended command for a persistent user variable)

Open **Command Prompt** or **PowerShell** and run (replace the placeholder with your real secret from the [OpenAI API keys](https://platform.openai.com/api-keys) page):

```cmd
setx OPENAI_API_KEY "your_api_key_here"
```

**Important:** `setx` updates the environment for **new** processes only. **Close and reopen** your terminal, IDE, and Electron app (if applicable) before starting the backend so `OPENAI_API_KEY` is visible to Python.

#### macOS / Linux

For the current shell session:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

To persist across sessions, add the same `export` line to `~/.zshrc`, `~/.bashrc`, or the profile file your shell loads on startup, then open a new terminal.

#### Verify

With your virtual environment activated, you can confirm the variable is set (command varies by shell); then start the API server as usual. If the key is missing, endpoints that require OpenAI will respond with errors such as `OPENAI_API_KEY is not set` until you configure it.

## MAC instruction--open loom

### Overview

Use this flow on macOS when validating the Electron frontend against the local backend. The goal is to confirm that login, project upload, visualization, and persisted backend-backed data all work from the actual desktop app flow.

Before starting this section, complete the shared setup in [Installation Guide for Future Development Team](#installation-guide-for-future-development-team). The steps below are the recommended macOS launch flow for opening Loom in development mode.

### Option A: install the packaged macOS app locally

If you want to install Loom as a local macOS application instead of running it from `npm start`, use the packaged macOS disk image:

- Apple Silicon macOS installer: [`frontend/dist/Loom-1.0.0-arm64.dmg`](frontend/dist/Loom-1.0.0-arm64.dmg)

Recommended install flow on macOS:
- Open the `.dmg` file.
- Drag `Loom.app` into the `Applications` folder.
- Launch `Loom.app` from Applications.

Use this option when testing the packaged desktop app experience on macOS.

### Option B: run Loom in development mode

Use this option when you want to run the Electron app directly from the repository during development.

### Prerequisites

- The Python virtual environment has already been created.
- Backend dependencies have already been installed with `pip install -r requirements-dev.txt` and `pip install -e .`.
- Frontend dependencies have already been installed with `cd frontend && npm install`.

### Terminal 1: start the backend

```bash
cd /path/to/capstone-project-team-17-1
source .venv/bin/activate
python -m capstone.run_server
```

The frontend expects the backend on port `8002`.

Optional for packaged-app testing only:

```bash
PYINSTALLER_CONFIG_DIR=/tmp/pyinstaller \
.venv/bin/python -m PyInstaller src/capstone/capstone_backend.spec --clean
```

You do not need this rebuild step for normal development mode with `npm start`.

### Terminal 2: start the frontend

```bash
cd /path/to/capstone-project-team-17-1
cd frontend
npm start
```

### Verify the backend connection

Open:

```text
http://127.0.0.1:8002/health
```

If it returns a healthy response, the backend and frontend should be able to connect.

### Suggested peer-testing checks

- Confirm the app launches without a frontend-backend connection error.
- Test account login and verify the authenticated view loads correctly.
- Upload a project and confirm it appears in the project list.
- Open project views and verify charts, summaries, or visualizations render.
- Restart the app/backend and confirm expected data persists through the hosted/local backend state.

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

Example startup flow:

```text
python main.py
============================================================
            Data and Artifact Mining Application
               Portfolio & Resume Generator
============================================================


Welcome! Thanks for being here. Let's get started :)


NOTE: This application processes and stores your project data. Do you wish to proceed? (This can be changed later)
Grant consent for this session (y/n): y
Save consent decision for future sessions (y/n): y
Saving consent for future sessions.


Proceeding with analysis...

Input shortcuts: b = back, m = main menu, Enter = cancel.

========================================
Main Menu
========================================
1.  Analyze new project archive (ZIP)
2.  Import from GitHub URL
3.  View all projects
4.  View project details
5.  Generate portfolio summary
6.  Resume
7.  View chronological project timeline
8.  View chronological skills timeline
9.  Delete project insights
10. Manage consent (LLM/external services)
11. Contributor rankings (Quick Access)
12. AI-based project analysis (external LLM)
13. Manage user profile
14. Project Representation Settings
15. Analyze User Role in Project
16. Set Project Success Evidence
17. Set Project Thumbnail
18. Exit

Please select an option (1-18):
```

Input shortcuts in interactive mode:
- `b` = back
- `m` = main menu
- `Enter` = cancel current prompt (where supported)

### Run API Backend

```bash
# Start FastAPI on port 8002
capstone api --host 127.0.0.1 --port 8002 --db-dir data
```

Base URL: `http://127.0.0.1:8002`

API docs:
- Swagger UI: `http://127.0.0.1:8002/docs`
- OpenAPI JSON: `http://127.0.0.1:8002/openapi.json`
- Route debug (mounted routers + import errors): `http://127.0.0.1:8002/__debug/routers`

## API Route Map (Table)

### System

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/` | API status | Implemented |
| GET | `/health` | Health check | Implemented |
| GET | `/api/health` | Alternate health check | Implemented |
| GET | `/system/system-metrics` | System metrics snapshot | Implemented |
| GET | `/__debug/routers` | Route/debug mount inspection | Implemented |

### Consent

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/privacy-consent` | Get privacy consent | Implemented |
| POST | `/privacy-consent/local` | Save local consent | Implemented |
| POST | `/privacy-consent/external` | Save external/AI consent | Implemented |

### Projects

| Method | Path | Description | Status |
|---|---|---|---|
| POST | `/projects/upload` | Upload zip and store project snapshot | Implemented |
| POST | `/projects/upload-bundle` | Upload a multi-project zip bundle | Implemented |
| GET | `/projects` | List projects | Implemented |
| GET | `/projects/{id}` | Get project details | Implemented |
| DELETE | `/projects/{id}` | Delete project | Implemented |
| POST | `/projects/{id}/thumbnail` | Upload project thumbnail | Implemented |
| GET | `/projects/{id}/thumbnail` | Get project thumbnail | Implemented |
| GET | `/projects/{id}/uploads` | List project uploads | Implemented |
| PATCH | `/projects/{id}` | Update project overrides | Implemented |
| POST | `/projects/{id}/edit` | Legacy alias for project edit | Implemented |
| GET | `/projects/{id}/overrides` | Get project overrides | Implemented |
| POST | `/projects/{project_id}/generate-resume` | Generate a resume from one project | Implemented |
| GET | `/projects/{project_id}/tree` | Get project file tree | Implemented |
| GET | `/projects/{project_id}/file` | Read a project file | Implemented |
| POST | `/projects/update-file` | Update a project file | Implemented |
| GET | `/projects/{project_id}/analysis` | Get project analysis view | Implemented |
| GET | `/projects/collaboration/{project_id}` | Get collaboration-focused project data | Implemented |

### Skills

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/projects/{project_id}/skills` | Get detected skills for project | Implemented |
| GET | `/skills` | Aggregate skills across projects | Implemented |
| GET | `/skills/timeline` | Get skills timeline data | Implemented |

### Resumes

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/resumes` | List resumes | Implemented |
| POST | `/resumes` | Create a resume | Implemented |
| POST | `/resumes/generate` | Auto-generate a resume | Implemented |
| POST | `/resumes/render-pdf` | Render resume payload as PDF | Implemented |
| GET | `/resumes/{resume_id}` | Get a resume | Implemented |
| PATCH | `/resumes/{resume_id}` | Update resume metadata | Implemented |
| DELETE | `/resumes/{resume_id}` | Delete a resume | Implemented |
| GET | `/resumes/{resume_id}/export` | Export a resume (`json|markdown|pdf`) | Implemented |
| GET | `/resumes/{resume_id}/sections` | List resume sections | Implemented |
| POST | `/resumes/{resume_id}/sections` | Create a resume section | Implemented |
| POST | `/resumes/{resume_id}/sections/reorder` | Reorder resume sections | Implemented |
| PATCH | `/resumes/{resume_id}/sections/{section_id}` | Update a resume section | Implemented |
| DELETE | `/resumes/{resume_id}/sections/{section_id}` | Delete a resume section | Implemented |
| GET | `/resumes/{resume_id}/sections/{section_id}/items` | List section items | Implemented |
| POST | `/resumes/{resume_id}/sections/{section_id}/items` | Create a section item | Implemented |
| POST | `/resumes/{resume_id}/sections/{section_id}/items/reorder` | Reorder section items | Implemented |
| PATCH | `/resumes/{resume_id}/sections/{section_id}/items/{item_id}` | Update a section item | Implemented |
| DELETE | `/resumes/{resume_id}/sections/{section_id}/items/{item_id}` | Delete a section item | Implemented |

### Portfolio / Showcase

| Method | Path | Description | Status |
|---|---|---|---|
| POST | `/portfolio/generate` | Generate portfolio summaries | Implemented |
| POST | `/portfolio/showcase/edit` | Edit showcase summary by project id | Implemented |
| POST | `/portfolio/{id}/edit` | Edit portfolio summary | Implemented |
| GET | `/portfolio/latest/summary` | Get one-page portfolio summary | Implemented |
| GET | `/portfolio/activity-heatmap` | Get portfolio activity heatmap data | Implemented |
| GET | `/portfolio/project-evolution` | Get project evolution/showcase data | Implemented |
| GET | `/portfolio/{id}/export` | Export portfolio data | Implemented |
| GET | `/showcase/*` | Showcase-prefixed aliases | Implemented |
| GET | `/portfolios/*`, `/users/*` | Legacy compatibility aliases | Implemented |

### Auth

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/auth/bootstrap` | Get auth bootstrap/session state | Implemented |
| POST | `/auth/register` | Register a user | Implemented |
| POST | `/auth/login` | Log in a user | Implemented |
| GET | `/auth/me` | Get current authenticated user | Implemented |
| PUT | `/auth/me` | Update current user profile | Implemented |
| GET | `/auth/me/education` | Get current user education entries | Implemented |
| PUT | `/auth/me/education` | Update current user education entries | Implemented |
| POST | `/auth/password` | Change password | Implemented |
| POST | `/auth/logout` | Log out current session | Implemented |

### GitHub / External Import

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/github/repos` | List authenticated GitHub repositories | Implemented |
| POST | `/github/import` | Import a GitHub repository as a project | Implemented |
| POST | `/github/pull` | Refresh/pull GitHub project data | Implemented |
| GET | `/github/auth-status` | Check GitHub auth status | Implemented |
| POST | `/github/login` | Save GitHub token/login state | Implemented |
| GET | `/github/branches` | List repository branches | Implemented |

### Dashboard / Analytics / Activity

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/dashboard/recent-projects` | Get recent projects for dashboard | Implemented |
| GET | `/activity` | Get activity log entries | Implemented |
| GET | `/analytics/project-health` | Get project health analytics | Implemented |
| GET | `/errors` | List stored error analyses | Implemented |
| POST | `/errors/analyze` | Run error analysis | Implemented |

### Sienna / AI

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/sienna/projects` | List projects available to Sienna | Implemented |
| POST | `/sienna/chat` | Chat with Sienna | Implemented |
| POST | `/sienna/voice` | Generate/return Sienna voice output | Implemented |

### Job Matching

| Method | Path | Description | Status |
|---|---|---|---|
| POST | `/job-matching/match` | Match one project to a job description | Implemented |
| POST | `/job-matching/rank` | Rank projects against a job description | Implemented |

### Cloud

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/cloud/test` | Cloud connectivity test | Implemented |
| GET | `/cloud/test-upload` | Cloud upload test | Implemented |
| GET | `/cloud/db` | Inspect cloud DB state | Implemented |
| POST | `/cloud/db/upload` | Upload DB to cloud storage | Implemented |
| POST | `/cloud/db/download` | Download DB from cloud storage | Implemented |
| POST | `/cloud/projects/download-all` | Download all project archives | Implemented |
| POST | `/cloud/project/upload` | Upload a project archive to cloud storage | Implemented |
| POST | `/cloud/project/download` | Download a project archive from cloud storage | Implemented |

Note:
- Full endpoint details, payload shapes, and aliases are documented in [`docs/api.md`](docs/api.md).
- This table summarizes the main routes currently mounted by [`src/capstone/api/server.py`](src/capstone/api/server.py).

## Example Requests

Upload a project zip:

```bash
curl -X POST "http://127.0.0.1:8002/projects/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/project.zip;type=application/zip"
```

List projects:

```bash
curl "http://127.0.0.1:8002/projects"
```

Get project skills:

```bash
curl "http://127.0.0.1:8002/projects/<project_id>/skills"
```

Generate a resume:

```bash
curl -X POST "http://127.0.0.1:8002/resumes/generate" \
  -H "Content-Type: application/json" \
  -d '{"user_id":1}'
```

## Test Report

### Test Commands Used

| Area | Command | Purpose |
|---|---|---|
| Python backend | `python -m pytest` | Full backend suite execution |
| Python backend | `python -m pytest --collect-only -q` | Discover what tests are currently collectible |
| Frontend | `cd frontend && node --test test/**/*.test.mjs` | Run renderer/helper tests with Node's built-in test runner |

### Test Status by Suite

| Suite | Files | Status in current environment | Notes |
|---|---|---|---|
| Frontend unit/runtime tests | [`frontend/test/`](frontend/test) | Passing | `38/38` tests passed |
| Python backend verified subset | [`tests/test_code_bundle.py`](tests/test_code_bundle.py), [`tests/test_config.py`](tests/test_config.py), [`tests/test_deep_review_prompt.py`](tests/test_deep_review_prompt.py), [`tests/test_llm_client.py`](tests/test_llm_client.py), [`tests/test_metrics_extractor.py`](tests/test_metrics_extractor.py), [`tests/test_resume_pdf_builder.py`](tests/test_resume_pdf_builder.py), [`tests/test_safe_delete.py`](tests/test_safe_delete.py), [`tests/test_clean.py`](tests/test_clean.py), [`tests/test_pipeline.py`](tests/test_pipeline.py), [`tests/test_summarize_top_projects.py`](tests/test_summarize_top_projects.py) | Passing | `41` tests passed across these files in the current environment |
| Python backend full collection | [`tests/`](tests) | Collects successfully | `497` tests were collected with `python -m pytest --collect-only -q` |

### Test Files Verified to Work

| Area | Verified file |
|---|---|
| Python | [`tests/test_code_bundle.py`](tests/test_code_bundle.py) |
| Python | [`tests/test_config.py`](tests/test_config.py) |
| Python | [`tests/test_deep_review_prompt.py`](tests/test_deep_review_prompt.py) |
| Python | [`tests/test_llm_client.py`](tests/test_llm_client.py) |
| Python | [`tests/test_metrics_extractor.py`](tests/test_metrics_extractor.py) |
| Python | [`tests/test_resume_pdf_builder.py`](tests/test_resume_pdf_builder.py) |
| Python | [`tests/test_safe_delete.py`](tests/test_safe_delete.py) |
| Python | [`tests/test_clean.py`](tests/test_clean.py) |
| Python | [`tests/test_pipeline.py`](tests/test_pipeline.py) |
| Python | [`tests/test_summarize_top_projects.py`](tests/test_summarize_top_projects.py) |
| Frontend | [`frontend/test/authShared.test.mjs`](frontend/test/authShared.test.mjs) |
| Frontend | [`frontend/test/consentShared.test.mjs`](frontend/test/consentShared.test.mjs) |
| Frontend | [`frontend/test/displayPreferencesShared.test.mjs`](frontend/test/displayPreferencesShared.test.mjs) |
| Frontend | [`frontend/test/onboardingShared.test.mjs`](frontend/test/onboardingShared.test.mjs) |
| Frontend | [`frontend/test/portfolioHeatmapRuntime.test.mjs`](frontend/test/portfolioHeatmapRuntime.test.mjs) |
| Frontend | [`frontend/test/portfolioResumeShared.test.mjs`](frontend/test/portfolioResumeShared.test.mjs) |
| Frontend | [`frontend/test/portfolioSkillLevels.test.mjs`](frontend/test/portfolioSkillLevels.test.mjs) |
| Frontend | [`frontend/test/portfolioState.test.mjs`](frontend/test/portfolioState.test.mjs) |
| Frontend | [`frontend/test/speechInput.test.mjs`](frontend/test/speechInput.test.mjs) |

### Test Collection Status

The previous logging-path collection issue has been fixed by falling back to a writable local or temporary log directory when the default Loom log path is not writable.

| Status | Scope | Result |
|---|---|---|
| Collection | Full Python suite | `497` tests collected successfully |
| Execution | Verified Python subset | `41` tests passed |
| Execution | Frontend Node suite | `38/38` tests passed |

### Test Strategies Used

| Strategy | How it is used in this repo |
|---|---|
| Unit testing | Pure Python modules such as config handling, prompt generation, code bundling, metrics extraction, and PDF helper logic are exercised in isolation |
| API integration testing | FastAPI routes are tested through HTTP-style request/response assertions with `TestClient` |
| CLI regression testing | Selected tests invoke CLI entry points and validate observable behavior rather than internal implementation details |
| Filesystem and persistence testing | Storage and safe-delete flows use temporary directories/databases to validate state changes |
| Frontend runtime logic testing | Node's built-in test runner validates renderer-side helpers, consent gating, onboarding logic, state selection, and speech-input fallbacks |
| Failure-path testing | Several tests explicitly cover missing API keys, unavailable browser APIs, empty inputs, and fallback logic |

### Current Test Result Summary

| Metric | Result |
|---|---|
| Frontend Node test suite | `38/38` passed |
| Python subset verified in this environment | `41` tests passed |
| Python full-suite collection | `497` tests collected successfully |

## Additional Notes

- `requirements-dev.txt` includes API/test deps: `fastapi`, `httpx`, `pytest`, `python-multipart`, `uvicorn`.
- PDF export requires a LaTeX engine. On macOS you can use:

```bash
./scripts/setup.sh
```

## Test Data ZIPs

The repo includes sample ZIPs for demos and validation under `test_data/`:
- [`test_data/test-data-code-collab-earlier.zip`](test_data/test-data-code-collab-earlier.zip)
- [`test_data/test-data-code-collab-later.zip`](test_data/test-data-code-collab-later.zip)
- [`test_data/test-data-multi-projects.zip`](test_data/test-data-multi-projects.zip)
- Source bundle for regeneration: [`test_data/multi_project_bundle/`](test_data/multi_project_bundle)

## Known Bugs

| Bug | Trigger | Impact | Workaround |
|---|---|---|---|
| PDF export is not self-contained | Calling resume/portfolio PDF generation without a local TeX engine; see [`src/capstone/resume_pdf_builder.py`](src/capstone/resume_pdf_builder.py) and [`src/capstone/portfolio_pdf_builder.py`](src/capstone/portfolio_pdf_builder.py) | PDF generation fails at runtime | Install `tectonic`, `xelatex`, `lualatex`, or `pdflatex`, or avoid PDF export in environments without LaTeX |
| Logging now depends on fallback paths in restricted environments | Running the app or tests where the default `~/Loom/log/` path is not writable | Logs are redirected to a writable fallback directory instead of the default Loom directory | Set `CAPSTONE_LOG_DIR` explicitly if you need logs in a specific location |
| Interactive CLI file-picking depends on `tkinter` | Running interactive flows on systems where `tkinter` is not installed or not available to the Python build | File picker based workflows do not work as expected | Install `python3-tk` on Linux or use a Python distribution that bundles `tkinter` |
| System metrics behavior is platform-sensitive | Using Windows-oriented monitoring assets such as [`src/capstone/tools/system_metrics/LibreHardwareMonitor/LibreHardwareMonitor.exe`](src/capstone/tools/system_metrics/LibreHardwareMonitor/LibreHardwareMonitor.exe) on non-Windows systems | Hardware monitoring features may be unavailable or inconsistent across macOS/Linux | Treat metrics features as Windows-first unless cross-platform support is explicitly added and tested |
| First-time load delays for new users | Initial use of features such as GitHub import, dashboard loading, resume export, or project analysis | Features may take up to a few minutes to fully load, giving the impression the app is unresponsive | Wait for initial processing to complete; performance improves after first load due to cached data |
| Project descriptions not updating | Viewing project details after analysis or changes where UI state does not refresh properly | Project descriptions may appear outdated or incorrect | Use the “Reset to Analysis” button to reload and apply the correct generated descriptions |
| GitHub import authentication issues | Using a GitHub token without required permissions (`repo`, `workflow`, `project`) | GitHub repositories may fail to import or return incomplete data | Ensure the GitHub personal access token includes `repo`, `workflow`, and `project` scopes |
| UI changes not reflecting immediately | Making updates within the app that do not trigger a full UI re-render | Changes may not appear even though they were applied successfully | Use the refresh button in the top right to reload the interface and reflect updates |

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

## Milestone #3

## 31.0 Produce a One-Page Résumé
  - 31.1 Include education and awards information
  - 31.2 Present skills categorized by expertise level
  - 31.3 Highlight projects with evidence of user contribution and impact

## 32.0 Deliver a Web Portfolio
  - 32.1 Display a skills timeline that demonstrates learning progression and increased expertise/depth
  - 32.2 Display a heatmap of project activities showing productivity over time
  - 32.3 Showcase the top 3 projects and illustrate process/evolution of changes

## 33.0 Support Private Dashboard Customization
  - 33.1 Provide a private mode for the dashboard
  - 33.2 Allow the user to interactively customize specific dashboard components before going live
  - 33.3 Allow the user to customize specific visualizations before going live

## 34.0 Support Public Dashboard Viewing
  - 34.1 Provide a public mode for the dashboard
  - 34.2 Restrict dashboard changes in public mode to search controls
  - 34.3 Restrict dashboard changes in public mode to filter controls

# DFD Level 0
<img width="1110" height="658" alt="Screenshot 2026-03-28 at 5 10 56 PM" src="https://github.com/user-attachments/assets/8c76963e-fec6-4e9f-bfaa-69034abd803d" />

The Level 0 diagram presents the overall context of the Capstone Analyzer System and its interactions with external entities. The system acts as a central hub that connects users, GitHub, an AI analysis service, an authentication service, and cloud storage.

Users submit requests such as repository uploads, analysis, and portfolio or resume generation. The system retrieves repository data and metadata from GitHub, sends project context to the AI analysis service to generate insights, and handles user authentication through the auth service. All project data and generated results are stored and retrieved from cloud storage. The system then returns analysis results, authentication status, and generated outputs back to the user.

# DFD Level 1
<img width="1292" height="568" alt="Screenshot 2026-03-28 at 6 23 59 PM" src="https://github.com/user-attachments/assets/d1a7d132-635a-4afc-992f-4b0685bc5373" />

The Level 1 diagram decomposes the Capstone Analyzer System into its core functional components and illustrates the internal data flow between them.

The process begins with Ingest Project Sources, where project data is collected either from user-uploaded archives or external repositories such as GitHub. The retrieved files are stored in the File/Artifact Store and passed to the Analyze Project Artifacts module. This module processes artifact contents to extract structured information such as project snapshots, detected skills, metrics, and contributor data, which are then stored in the Project Database. During this stage, system-generated errors, warnings, and activity logs are recorded in the Activity/Error Logs.

Based on the analyzed data, the Generate Portfolio and Resume module produces portfolio summaries and resume outputs in formats such as PDF or JSON. These outputs are derived from stored project metadata and summaries in the database.

Finally, the Present Dashboard and Reports module retrieves processed data, metrics, and logs to generate dashboards, visualizations, and reports for the user. The user can interact with the system through requests such as project uploads, generation requests, and filtered views, and receives outputs including portfolios, resumes, and analytical dashboards.

# system_architecture_design
<img width="1001" height="669" alt="Screenshot 2026-03-28 at 6 14 56 PM" src="https://github.com/user-attachments/assets/727b2bc8-01c5-4ece-9cb0-37af9efb7c94" />

The system is designed as a local-first application that analyzes a user’s own project artifacts to help them understand, track, and present their work history. It targets students and early professionals who want to generate structured insights, timelines, and portfolio-ready summaries without exposing their data externally. All core processing and storage occur locally by default, with optional external services gated behind explicit user consent.

Functionally, the system begins with user-controlled data ingestion, allowing users to import projects via ZIP uploads or GitHub repositories. An artifact identification and parsing pipeline processes the input, handling unsupported, corrupted, or duplicate files through validation and hashing. Files are then classified by type (e.g., code, documents) and routed into analysis pipelines.

The system performs multi-stage analysis. Code artifacts undergo structural analysis to identify programming languages, frameworks, contributors, keywords, and activity patterns such as commit frequency. Non-code artifacts (e.g., documents) are processed through content analysis to extract skills, topics, and summaries. When external processing is permitted, an alternative pipeline enables anonymization followed by AI-assisted insight generation. All extracted features and summaries are passed to a metrics calculation module, which computes higher-level indicators such as activity timelines, contribution patterns, and key skills.

Processed data is stored in a local SQLite database, with separate handling for activity logs and errors to ensure transparency and debuggability. The system supports portfolio and resume generation, producing structured outputs (PDF/JSON) based on stored project summaries and metrics. A dashboard and reporting module enables interactive exploration through filters (e.g., time, project, file type), visualizations, and summaries.

Non-functional requirements emphasize privacy, performance, and usability. Data remains local by default with least-privilege access, secure storage, and optional anonymization before any external interaction. The system supports incremental and resumable processing, responsive dashboards, and clear user feedback including progress indicators and surfaced errors. Maintainability is supported through modular architecture, testability, and clear data flow separation across ingestion, analysis, storage, and presentation layers.
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
