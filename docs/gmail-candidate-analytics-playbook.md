# Gmail Candidate Analytics Playbook

This workflow gives ThinkSuccess one daily Google Sheet view of candidate job-application activity, recruiter communication, upcoming interviews, and mailbox health.

## Company Setup

For cloud deployment, use [google-cloud-gmail-analytics-deployment.md](google-cloud-gmail-analytics-deployment.md). The steps below describe the application-level setup after the cloud services exist.

1. Sign in as `Thinksuccess.ITConsultants@gmail.com`.
2. Create a Google Cloud project for candidate email analytics.
3. Enable Gmail API, Google Calendar API, and Google Sheets API.
4. Configure the OAuth consent screen.
5. Create an OAuth web client and set the redirect URL to:
   `https://YOUR_BACKEND_DOMAIN/api/v1/admin/gmail/oauth/callback`
6. Create a Google Sheet owned by `Thinksuccess.ITConsultants@gmail.com`.
7. Create a service account, share the Google Sheet with the service account email as Editor, and store either the service account JSON string or a readable JSON file path in `GOOGLE_SERVICE_ACCOUNT_JSON`.
8. Generate a token encryption key:
   `python scripts/generate_google_token_key.py`
9. Set these backend environment variables:
   - `GMAIL_ANALYTICS_ENABLED=true`
   - `GOOGLE_CLIENT_ID=...`
   - `GOOGLE_CLIENT_SECRET=...`
   - `GOOGLE_OAUTH_REDIRECT_URI=https://YOUR_BACKEND_DOMAIN/api/v1/admin/gmail/oauth/callback`
   - `GOOGLE_TOKEN_ENCRYPTION_KEY=...`
   - `GOOGLE_SHEETS_REPORT_ID=...`
   - `GOOGLE_SERVICE_ACCOUNT_JSON=...`

## Candidate Connection

For every candidate:

1. Confirm the candidate exists in the operations dashboard and has the correct Gmail address.
2. As a super admin, call:
   `GET /api/v1/admin/gmail/oauth-url?candidate_id=ID`
3. Open the returned authorization URL.
4. Sign in using the candidate Gmail.
5. Approve read-only Gmail and Calendar permissions.
6. Confirm the callback says the candidate Gmail and Calendar connected successfully.
7. Confirm the candidate appears in:
   `GET /api/v1/admin/gmail/mailboxes`

## Employee Rules

1. Use only the candidate Gmail for job applications.
2. Do not apply using employee Gmail or the company Gmail.
3. Never delete recruiter emails, application confirmations, assessments, rejections, or calendar invites.
4. If a recruiter schedules manually, add the event to the candidate Gmail calendar.
5. Keep interview and follow-up emails in the inbox until the daily report captures them.
6. Review the Google Sheet every morning for follow-ups and interviews.

## Daily Report Tabs

- `Daily Summary`: candidate-wise counts for applications, replies, interviews, assessments, rejections, and follow-ups.
- `Candidate Detail`: recent classified email events with sender, subject, category, and Gmail link.
- `Upcoming Interviews`: upcoming interview-like calendar events.
- `Mailbox Health`: connection and scan status for every candidate.

## Manual Run

To scan immediately and publish the sheet:

```bash
cd apps/backend
python scripts/run_gmail_analytics.py
```

Or call:

```http
POST /api/v1/admin/gmail/run?publish_sheets=true
```

## Troubleshooting

- `not_connected`: candidate has not completed OAuth yet.
- `error`: open mailbox health to see the last error.
- `invalid_grant`: candidate revoked access or Google invalidated the refresh token; reconnect that Gmail.
- Sheet not updating: confirm `GOOGLE_SHEETS_REPORT_ID` is correct and the service account email has Editor access to the Sheet.
