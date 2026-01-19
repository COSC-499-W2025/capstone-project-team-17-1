API Endpoints

Auth
- If `PORTFOLIO_API_TOKEN` or `--token` is set, pass `Authorization: Bearer <token>` for every request.

Portfolios
- `GET /portfolios/latest?projectId=<id>`: Latest snapshot for project.
- `GET /portfolios?projectId=<id>&page=1&pageSize=20&sort=created_at:desc`: Paginated snapshots.
- `GET /portfolios/evidence?projectId=<id>`: Simple evidence/metrics summary for project.

Resume Entries (28. Resume Item Customization)
- `GET /resume?format=preview|json&section=projects&keyword=...`: List resume entries or preview.
- `GET /resume/{id}`: Get a resume entry by id.
- `POST /resume`: Create a resume entry.
  - Body: `section`, `title`, `body` required. Optional `summary`, `status`, `metadata`, `projects`, `skills`, `created_at`.
- `POST /resume/{id}/edit`: Edit a resume entry.
  - Body: any subset of `section`, `title`, `summary`, `body`, `status`, `metadata`, `projects`, `skills`.

Resume Generation (28 + 30)
- `POST /resume/generate`: Export resume data.
  - Body: `format` = `json|markdown|pdf`, optional filters `sections`, `keywords`, `startDate`, `endDate`, `includeOutdated`, `limit`, `offset`.
  - Response: `payload` is JSON/markdown, or base64 for PDF.

Resume Project Wording (30. Résumé Textual Display)
- `GET /resume-projects?projectId=<id>`: Get active wording for project.
- `GET /resume-projects?projectId=<id>&list=true`: List all wordings for project.
- `GET /resume-projects?activeOnly=true`: Only active wordings.
- `POST /resume-projects`: Create or update wording.
  - Body: `projectId`, `summary` required. Optional `variantName`, `audience`, `isActive`, `metadata`.
  - Validation: empty/too long summaries return 422.
  - If `isActive=true`, other wordings for the project become inactive.
- `POST /resume-projects/generate`: Auto-generate resume wording from project snapshot.
  - Body: `projectIds` array, optional `overwrite`.

Priority Rules (Resume Display)
- When rendering resume text: custom resume wording > auto-generated wording > resume entry body/summary.
- Preview items include `source`: `custom | generated | fallback`.

Status Codes
- `400 BadRequest`: missing required params (e.g., projectId).
- `404 NotFound`: requested project/entry does not exist.
- `422 UnprocessableEntity`: invalid content (empty/too long summary).
