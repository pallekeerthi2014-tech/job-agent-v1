# Google Cloud Deployment: Gmail Candidate Analytics

This deployment removes the local-machine dependency. Google Cloud runs the API, the scheduled Gmail/Calendar scanner, the database, secrets, and logs.

## Target Architecture

- Cloud Run service: FastAPI backend for OAuth callbacks and admin endpoints.
- Cloud Run Job: executes `scripts/run_gmail_analytics.py`.
- Cloud Scheduler: triggers the Cloud Run Job every 15-30 minutes.
- Cloud SQL for PostgreSQL: stores candidates, encrypted OAuth tokens, scan state, email events, calendar events, and metrics.
- Secret Manager: stores credentials and secrets.
- Google Sheets: reporting surface owned by `Thinksuccess.ITConsultants@gmail.com`.

## One-Time Google Setup

1. Sign in to Google Cloud as `Thinksuccess.ITConsultants@gmail.com`.
2. Create a Google Cloud project.
3. Enable these APIs:
   - Gmail API
   - Google Calendar API
   - Google Sheets API
   - Cloud Run API
   - Cloud Scheduler API
   - Cloud SQL Admin API
   - Secret Manager API
   - Artifact Registry API
4. Create a Cloud SQL PostgreSQL instance and database.
5. Create a Google Sheet for the report.
6. Create a service account for Sheet publishing and share the Google Sheet with that service account as Editor.
7. Configure OAuth consent and create an OAuth web client.
8. Set the OAuth redirect URI to:
   `https://BACKEND_CLOUD_RUN_URL/api/v1/admin/gmail/oauth/callback`

## Secrets

Store these in Secret Manager:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_TOKEN_ENCRYPTION_KEY`
- `GOOGLE_SHEETS_REPORT_ID`
- `SUPER_ADMIN_EMAIL`
- `SUPER_ADMIN_PASSWORD`
- `EMPLOYEE_DEFAULT_PASSWORD`

Generate the token encryption key from the backend image or locally:

```bash
cd apps/backend
python scripts/generate_google_token_key.py
```

## Deploy Backend Service

Build and deploy the backend container to Cloud Run. The existing `apps/backend/Dockerfile` starts the FastAPI service and runs Alembic migrations at boot.

Recommended runtime env:

```text
API_HOST=0.0.0.0
API_PORT=8000
SCHEDULER_ENABLED=false
GMAIL_ANALYTICS_ENABLED=false
ALLOWED_ORIGINS=https://YOUR_FRONTEND_DOMAIN
PUBLIC_APP_URL=https://YOUR_FRONTEND_DOMAIN
GOOGLE_OAUTH_REDIRECT_URI=https://BACKEND_CLOUD_RUN_URL/api/v1/admin/gmail/oauth/callback
```

Keep `SCHEDULER_ENABLED=false` on Cloud Run service. Cloud Scheduler and Cloud Run Job handle recurring work.

## Deploy Gmail Analytics Job

Use the same backend container image, but override the command to:

```bash
scripts/cloud_run_gmail_job.sh
```

Recommended job env:

```text
SCHEDULER_ENABLED=false
GMAIL_ANALYTICS_ENABLED=true
GOOGLE_OAUTH_REDIRECT_URI=https://BACKEND_CLOUD_RUN_URL/api/v1/admin/gmail/oauth/callback
```

The job runs migrations, scans connected candidate Gmail/Calendar accounts, rebuilds metrics, and publishes the Google Sheet.

## Schedule the Job

Create a Cloud Scheduler job that triggers the Cloud Run Job every 30 minutes.

Recommended schedule:

```text
*/30 * * * *
```

Use an authenticated scheduler service account with permission to run the Cloud Run Job.

## Candidate Onboarding

1. Add or confirm the candidate in the operations dashboard.
2. As super admin, call:
   `GET /api/v1/admin/gmail/oauth-url?candidate_id=ID`
3. Open the returned URL.
4. Sign in with the candidate Gmail.
5. Approve Gmail read-only and Calendar read-only access.
6. Confirm the candidate appears in:
   `GET /api/v1/admin/gmail/mailboxes`

## Operating Notes

- Do not use or store Gmail passwords.
- The backend API service handles OAuth; the Cloud Run Job handles recurring scans.
- Google Sheet tabs are recreated/updated by the job:
  - `Daily Summary`
  - `Candidate Detail`
  - `Upcoming Interviews`
  - `Mailbox Health`
- If a candidate revokes Google access, the next job marks that mailbox as `error` and writes the reason in `Mailbox Health`.

## Cost Control

- Set Cloud Run service minimum instances to `0`.
- Run the scanner every 30 minutes to start.
- Use the smallest Cloud SQL instance that meets reliability needs.
- Add Cloud SQL backups, but keep retention modest.
- Avoid AI classification until the rule-based workflow proves the volume and categories.
