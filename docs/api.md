API Endpoints

Overview
- The API is served by `capstone.api.server.create_app` (FastAPI).
- All endpoints are JSON, but response envelopes are not fully uniform yet:
  some endpoints return `{ data, error, meta? }`, while others return direct JSON objects.
- Base URL defaults to `http://127.0.0.1:<port>` when launched via the CLI.

System
- `GET /`
  - Basic API status message.
- `GET /health`
  - Health check.
Auth
- If `PORTFOLIO_API_TOKEN` or `--token` is set, pass `Authorization: Bearer <token>` for every request.

API Testing (No Real Server Required)
- API endpoints are tested using FastAPI's `TestClient`, which exercises routes as HTTP requests/responses without starting a real server process.
- Tests validate status codes and response payloads (e.g., `tests/test_api_incremental_upload.py`, `tests/test_api_project_edits.py`, `tests/test_api_snapshot_diff.py`).
- We also manually validated key endpoints with Postman for integration/demo checks.

Consent
- `POST /privacy-consent`
  - Body: `{ "consent": true|false }`
- `GET /privacy-consent`
  - Returns current consent state.

Projects
- `POST /projects/upload`
  - Upload a `.zip` project archive.
  - If `project_id` is omitted, the server can auto-detect and reuse an existing project id for snapshot uploads of the same project.
  - Response includes `message`, `dedup`, and `auto_detected_project_id`.
- `GET /projects`
  - Lists uploaded project archives.
- `GET /projects/{id}`
  - Returns a single uploaded project archive.
- `DELETE /projects/{id}`
  - Deletes an uploaded project and its stored file.
- `GET /projects/{id}/uploads`
  - Lists all uploads for a project (oldest to newest).
  - Includes `snapshot_diff` (earliest vs latest upload) when at least two uploads exist.
  - `snapshot_diff` includes file changes (`added`, `removed`, `modified`) and skill changes (`before`, `after`, `changes`).
- `PATCH /projects/{id}`
  - Updates project-level overrides used for portfolio/resume editing.
  - Body supports: `key_role`, `evidence`, `portfolio_blurb`, `resume_bullets`, `selected`, `rank`.
- `GET /projects/{id}/overrides`
  - Returns the saved overrides for a project.

Portfolios
- `GET /portfolios/latest?projectId=<id>&view=portfolio|resume`
  - Returns the latest snapshot for a project (`view=portfolio`, default) or the active resume wording (`view=resume`).
  - Query: `projectId` (required), `view` (optional).
  - Optional: `user` to include `userRole` in `meta`.
- `GET /portfolios?projectId=<id>&page=1&pageSize=20&sort=created_at:desc`
  - Returns paginated snapshots for a project.
  - Query: `projectId` (required), `page`, `pageSize`, `sort` (`<field>:asc|desc`), `classification`, `primaryContributor`.
- `GET /portfolios/evidence?projectId=<id>`
  - Returns a simple evidence/metrics summary for a project.

Portfolio API (`src/capstone/api/routes/portfolio.py`)

Users
- `GET /users`
  - Returns a list of contributor usernames (bot accounts filtered out).
- `GET /users/{user}/projects`
  - Returns the project IDs a contributor appears in.
- `GET /portfolio/summary?user=<user>&limit=3`
  - Returns markdown portfolio summaries for a user.

Resume API (`src/capstone/api/routes/resume.py`)

Resume Entries
- `GET /resume?format=preview|json&section=projects&keyword=...`
  - Lists resume entries or returns a preview payload when `format=preview`.
  - Query: `format`, `section` (repeatable), `keyword` (repeatable), `startDate`, `endDate`,
    `includeOutdated`, `limit`, `offset`.
- `GET /resume/{id}`
  - Returns a single resume entry by id.
  - Alias: `GET /resume/<entry_id>`.
- `POST /resume`
  - Creates a resume entry.
  - Body: `section`, `title`, `body` required. Optional `summary`, `status`, `metadata` (object),
    `projects` (array), `skills` (array), `created_at`.
- `PATCH /resume/{id}`
  - Updates a resume entry.
  - Body: any subset of `section`, `title`, `summary`, `body`, `status`, `metadata`, `projects`, `skills`.
- `POST /resume/{id}/edit`
  - Alias for updating a resume entry (same payload as PATCH).
- `DELETE /resume/{id}`
  - Deletes a resume entry.

Resume Generation
- `POST /resume/generate`
  - Exports resume data.
  - Body: `format` = `json|markdown|pdf`, optional filters `sections`, `keywords`, `startDate`,
    `endDate`, `includeOutdated`, `limit`, `offset`.
  - Response: `data.payload` is JSON/markdown, or base64 for PDF.
- `POST /resume/render-pdf`
  - Renders a resume JSON payload to PDF (base64 in response).
  - Body: `{ "resume": { ... } }`

Resume Project Wording
- `GET /resume-projects?projectId=<id>`
  - Returns the active wording for a project.
- `GET /resume-projects?projectId=<id>&list=true`
  - Returns all wordings for a project.
- `GET /resume-projects?activeOnly=true`
  - Returns only active wordings (optionally filtered by `projectId`).
- `POST /resume-projects`
  - Creates or updates a wording record.
  - Body: `projectId`, `summary` required. Optional `variantName`, `audience`, `isActive`, `metadata`.
  - Validation: empty/too long summaries return 422.
  - If `isActive=true`, other wordings for the project become inactive.
- `POST /resume-projects/generate`
  - Auto-generates resume wording from project snapshots.
  - Body: `projectIds` array, optional `overwrite`.

Portfolio Showcase
- `GET /portfolio/{id}`
  - Returns the saved showcase summary for a project (variant: `portfolio_showcase`).
  - If no saved summary exists, returns an auto summary from the latest snapshot.
  - Optional: `user` to include `user_role` in response.
- `GET /portfolio/showcase?projectId=<id>`
  - Query alias for `GET /portfolio/{id}`.
- `GET /portfolio/{id}/export?format=json|markdown|pdf`
  - Demo export endpoint (enabled when no auth token is configured).
- `POST /portfolio/generate`
  - Auto-generates and saves showcase summaries for projects.
  - Body: `projectIds` array.
- `POST /portfolio/{id}/edit`
  - Updates (or creates) the showcase summary for a project.
  - Body: `summary` (string, required).
- `POST /portfolio/showcase/edit`
  - Body: `projectId`, `summary` (string, required).


Portfolio Showcase Examples
```json
POST /portfolio/generate
{
  "projectIds": ["demo-2", "project-xyz"]
}
```

```json
POST /portfolio/demo-2/edit
{
  "summary": "Built a web platform to automate QA workflows and reduce regression cycles."
}
```

Priority Rules (Resume Display)
- When rendering resume text: custom resume wording > auto-generated wording > resume entry body/summary.
- Preview items include `source`: `custom | generated | fallback`.

Status Codes
- `400 BadRequest`: missing/invalid required params (e.g., projectId).
- `401 Unauthorized`: missing/invalid bearer token.
- `404 NotFound`: requested project/entry does not exist.
- `422 UnprocessableEntity`: invalid content (empty/too long summary).

Skills API (`src/capstone/api/routes/skills.py`)
- `GET /projects/{project_id}/skills`
  - Returns skills detected for a project.
- `GET /skills`
  - Aggregates skills across uploaded projects.

Project Thumbnails
- `POST /projects/{id}/thumbnail`
  - Uploads an image to use as the project thumbnail.
- `GET /projects/{id}/thumbnail`
  - Returns the latest thumbnail image for a project.

Projects (Additional)
- `GET /projects/{id}/skills`
  - Returns skills detected from the latest uploaded ZIP for the project.
- `GET /skills`
  - Aggregates skills across uploaded projects.

Showcase Router Prefix (`/showcase`, additional mounted aliases)
- `GET /showcase/users`
- `GET /showcase/users/{user}/projects`
- `GET /showcase/portfolio/summary?user=<user>&limit=3`
- `GET /showcase/portfolios/latest?projectId=<id>&view=portfolio|resume`
- `GET /showcase/portfolios/evidence?projectId=<id>`
- `GET /showcase/portfolios?projectId=<id>&page=1&pageSize=20&sort=created_at:desc`
- `GET /showcase/portfolio/showcase?projectId=<id>`
- `GET /showcase/portfolio/{id}`
- `POST /showcase/portfolio/generate`
- `POST /showcase/portfolio/showcase/edit`
- `POST /showcase/portfolio/{id}/edit`

Legacy Aliases (compatibility routes)
- `GET /users`
  - Alias to showcase users listing.
- `GET /users/{user}/projects`
  - Alias to showcase user-project listing.
- `GET /portfolios/latest`
  - Alias to showcase latest portfolio/resume snapshot endpoint.
- `GET /portfolios/evidence`
  - Alias to showcase evidence endpoint.

Debug
- `GET /__debug/routers`
  - Lists mounted routes and optional import/mount errors for optional routers.
