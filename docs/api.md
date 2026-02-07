API Endpoints

Overview
- The API is served by `capstone.api.server.create_app` (FastAPI).
- All endpoints are JSON and return `{ data, error, meta? }`.
- Base URL defaults to `http://127.0.0.1:<port>` when launched via the CLI.

Auth
- If `PORTFOLIO_API_TOKEN` or `--token` is set, pass `Authorization: Bearer <token>` for every request.

Portfolios
- `GET /portfolios/latest?projectId=<id>&view=portfolio|resume`
  - Returns the latest snapshot for a project (`view=portfolio`, default) or the active resume wording (`view=resume`).
  - Query: `projectId` (required), `view` (optional).
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

Resume Generation
- `POST /resume/generate`
  - Exports resume data.
  - Body: `format` = `json|markdown|pdf`, optional filters `sections`, `keywords`, `startDate`,
    `endDate`, `includeOutdated`, `limit`, `offset`.
  - Response: `data.payload` is JSON/markdown, or base64 for PDF.

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
- `GET /portfolio/showcase?projectId=<id>`
  - Query alias for `GET /portfolio/{id}`.
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
