# Candidate Portal Onboarding Manual

This manual is for onboarding existing and new candidates into the Think Success candidate portal.

## Production Links

- Candidate/admin portal: https://job-agent-frontend-production-c54d.up.railway.app/login
- Backend health check: https://job-agent-backend-production-a463.up.railway.app/health

## What Candidates Get

Candidates can use the portal to:

- Log in to a private candidate account.
- Maintain profile details such as location, work authorization, experience, salary preference, and phone.
- Upload or replace their resume.
- Set job preferences:
  - Target roles
  - Work mode
  - Preferred industries
  - Preferred locations
  - Must-have keywords
  - Avoid keywords
- View ranked job matches.
- Filter matches by all, high match, saved, pending, and applied.
- See compact job cards with match reasons and resume focus areas.
- Open a detailed application plan per job.
- Apply, save, request tailored resume, or mark a job as not interested.
- Track applications and saved jobs.
- See resume readiness and interview-prep guidance.

## Existing Candidate Onboarding

Use this process for candidates already in the admin system.

1. Confirm candidate record exists.
   - Log in as admin.
   - Go to `Admin Candidates`.
   - Search for the candidate by name or email.
   - Make sure the candidate has a valid email address.

2. Create or invite candidate portal user.
   - Go to `Admin Users`.
   - Use the candidate invitation flow if available.
   - Send the candidate invite to their email.
   - If SMTP is not configured, copy the preview invite link and send it manually.

3. Candidate registers or logs in.
   - Candidate opens the invite link.
   - Candidate creates a password.
   - Candidate logs into the portal.

4. Candidate completes profile.
   - Ask the candidate to add location, work authorization, experience, salary preference, and phone.
   - Ask the candidate to upload a resume.
   - Ask the candidate to set job profile preferences.

5. Run or wait for matching pipeline.
   - If jobs/matches already exist, the candidate should see ranked jobs immediately.
   - If they do not see matches, run the daily pipeline or wait for the scheduled run.

6. Candidate begins using the portal.
   - Review top matches.
   - Save jobs for review.
   - Request tailored resume where appropriate.
   - Apply to selected jobs.
   - Track progress in the tracker tab.

## New Candidate Onboarding

1. Create candidate record.
   - Admin goes to `Admin Candidates`.
   - Add candidate name, email, phone, location, work authorization, experience, and assigned employee if known.

2. Invite candidate.
   - Admin goes to `Admin Users`.
   - Send candidate registration invitation.

3. Candidate completes portal setup.
   - Profile
   - Resume
   - Job preferences

4. Internal team reviews.
   - Admin/employee checks candidate preferences.
   - Admin confirms resume is uploaded.
   - Team can use candidate portal metrics to watch login and progress.

## Admin Monitoring

Admin can monitor candidate engagement from the analytics page.

Metrics now include:

- Total candidate accounts
- Candidates who logged in
- Resume-ready candidates
- Candidate applications
- Saved jobs
- Per-candidate last login
- Resume status
- Matches
- High-fit matches
- Applied jobs
- Saved jobs
- Pending jobs
- Progress percentage

## Recommended Operating Workflow

Daily:

- Check candidate portal engagement.
- Review candidates with missing resumes.
- Review high-fit jobs and candidate requests.
- Prioritize tailored resume requests for stronger matches.

Weekly:

- Send candidates a progress summary.
- Ask inactive candidates to update preferences.
- Review saved jobs and application conversion.
- Follow up with candidates who have many pending matches but few applications.

## Cost-Control Notes

- Alerts are now email-first.
- WhatsApp should remain off unless explicitly needed.
- Candidate tailored resume requests are currently workflow signals, not automatic AI generation.
- Recommended next step is admin-approved generation for tailored resumes, so AI cost is controlled.

## Candidate Message Template

Hi {{Candidate Name}},

Your Think Success candidate portal is ready. Please log in, complete your profile, upload your latest resume, and select your target roles and locations.

Portal: https://job-agent-frontend-production-c54d.up.railway.app/login

Once your profile is complete, you will be able to review matched jobs, save opportunities, request tailored resume support, apply to jobs, and track your progress.

Thank you,
Think Success IT Consulting

