API Endpoints

Overview
- The API is served by `capstone.portfolio_retrieval.create_app` (Flask).
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
- `POST /resume/{id}/edit`
  - Updates a resume entry.
  - Alias: `POST /resume/<entry_id>/edit`.
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

Priority Rules (Resume Display)
- When rendering resume text: custom resume wording > auto-generated wording > resume entry body/summary.
- Preview items include `source`: `custom | generated | fallback`.

Status Codes
- `400 BadRequest`: missing/invalid required params (e.g., projectId).
- `401 Unauthorized`: missing/invalid bearer token.
- `404 NotFound`: requested project/entry does not exist.
- `422 UnprocessableEntity`: invalid content (empty/too long summary).
