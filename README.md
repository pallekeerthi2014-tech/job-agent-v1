# Job Matching Operations Dashboard - Phase 1

Production-ready starter for a job-matching operations dashboard with:

- FastAPI backend
- PostgreSQL with SQLAlchemy and Alembic
- Optional Redis wiring
- APScheduler for daily ingestion and scoring jobs
- React + Vite frontend
- Docker Compose local development stack
- Employee login and super-admin user management
- Forgot/reset-password flow

## Phase 1 capabilities

- Candidate profile storage
- Configurable job source storage
- Job ingestion from local JSON or remote JSON feeds
- Job normalization into structured attributes
- Candidate-job match scoring
- Employee work queue for review
- Manual `mark applied` workflow

## Folder structure

```text
job-agent-v1/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   ├── models/
│   │   │   ├── parsers/
│   │   │   ├── schemas/
│   │   │   ├── scoring/
│   │   │   ├── services/
│   │   │   └── workers/
│   │   ├── tests/
│   │   ├── alembic/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/
│       ├── src/
│       │   ├── api/
│       │   ├── components/
│       │   └── pages/
│       ├── Dockerfile
│       └── package.json
├── infra/
├── seed-data/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Quick start

1. Copy the environment template.

```bash
cd job-agent-v1
cp .env.example .env
```

2. Start the full local stack.

```bash
docker compose up --build
```

3. Open the apps.

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)

4. Seed sample data after the stack is up.

```bash
docker compose exec backend python scripts/seed.py
```

5. Sign in locally.

- Frontend: [http://localhost:5173](http://localhost:5173)
- Super admin email: `admin@thinksuccessitconsulting.com`
- Super admin password: `ChangeMe123!`
- Default employee password: `ThinkSuccess123!`

## Local services

- `postgres`: PostgreSQL 16
- `backend`: FastAPI app with Alembic migrations on boot
- `frontend`: Vite dev server

## Backend notes

The backend organizes Phase 1 logic into services:

- `ingestion.py`: fetches jobs from configured sources
- `parsers/normalizer.py`: turns raw job content into normalized attributes
- `scoring/engine.py`: computes candidate-job scores
- `queue.py`: builds and updates employee work queue items
- `workers/scheduler.py`: runs daily pipeline jobs

## Environment variables

The monorepo uses environment variables across Compose, backend, and frontend.

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `API_HOST`, `BACKEND_PORT`
- `FRONTEND_PORT`, `VITE_API_BASE_URL`
- `ALLOWED_ORIGINS`
- `SCHEDULER_ENABLED`, `SCHEDULER_TIMEZONE`, `DAILY_JOB_HOUR`, `DAILY_JOB_MINUTE`
- `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `RESET_TOKEN_EXPIRE_MINUTES`
- `PUBLIC_APP_URL`
- `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`, `EMPLOYEE_DEFAULT_PASSWORD`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS`
- `SEED_SAMPLE_CANDIDATES`

## Auth overview

- `POST /api/v1/auth/login`: employee or super-admin sign-in
- `GET /api/v1/auth/me`: current logged-in user
- `POST /api/v1/auth/forgot-password`: sends email if SMTP is configured, otherwise returns a preview reset token locally
- `POST /api/v1/auth/reset-password`: resets the password from the token
- `GET /api/v1/admin/users`: super-admin user list
- `POST /api/v1/admin/users`: create employee or super-admin logins
- `PUT /api/v1/admin/users/{id}`: activate/deactivate or reset passwords

Employees only see their own candidates, matches, applications, and work queue. Super admins can see and manage everything.

## Deployment

This repo now includes `render.yaml` for a public deployment with:

- Render Postgres
- Render Docker web service for the FastAPI backend
- Render static site for the React frontend

Setup steps:

1. Push the latest repo to GitHub.
2. In Render, create a new Blueprint and point it to this repo.
3. During setup, provide secret values for:
   - `SUPER_ADMIN_EMAIL`
   - `SUPER_ADMIN_PASSWORD`
   - `EMPLOYEE_DEFAULT_PASSWORD`
   - `PUBLIC_APP_URL`
   - `VITE_API_BASE_URL`
   - `ALLOWED_ORIGINS`
   - SMTP settings if you want reset emails to be sent automatically
4. After the first backend deploy, run:

```bash
python scripts/seed.py
```

5. Add your custom domain in Render once the default `onrender.com` URLs are working.

### Supported source configuration

The sample app supports two source styles:

1. `json_file`
   - Reads a local JSON file path from source config.
2. `json_api`
   - Fetches JSON from a remote URL.

Example source config:

```json
{
  "path": "/seed-data/job_feed.json"
}
```

## API overview

- `GET /health`
- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `GET /api/v1/job-sources`
- `POST /api/v1/job-sources`
- `GET /api/v1/jobs`
- `POST /api/v1/jobs/ingest`
- `POST /api/v1/jobs/normalize`
- `POST /api/v1/matches/score`
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/work-queue`
- `POST /api/v1/dashboard/work-queue/{queue_item_id}/mark-applied`

## Useful commands

Run backend locally outside Docker:

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run frontend locally outside Docker:

```bash
cd apps/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Seed data

Seed files live under `seed-data/` and include:

- sample candidates
- sample job sources
- sample job feed payload

The seed script:

- inserts candidates and sources
- ingests jobs
- normalizes jobs
- computes scores
- generates work queue items

## Notes

- `scripts/seed.py` now cleans up legacy demo employees and candidates before seeding the current team accounts.
- Sample healthcare candidates are no longer seeded by default. Set `SEED_SAMPLE_CANDIDATES=true` only if you want demo candidate data in a fresh environment.
