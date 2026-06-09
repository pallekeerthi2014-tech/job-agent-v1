# ThinkSuccess Gmail Forwarding Scanner

This is the real scanner for the admin `Gmail Analytics` page.

It runs inside `thinksuccess.ITconsulting@gmail.com` using Google Apps Script. It does not give the backend your Gmail password and it does not use the old candidate Gmail OAuth flow.

## Backend Secret

Set this production backend env var in Railway:

```text
GMAIL_FORWARDING_WEBHOOK_SECRET=<generate-a-long-random-secret>
```

Use the same value in Apps Script script properties.

## Apps Script Setup

1. Sign in as `thinksuccess.ITconsulting@gmail.com`.
2. Open [script.google.com](https://script.google.com).
3. Create a new Apps Script project named `ThinkSuccess Forwarding Scanner`.
4. Paste `thinksuccess-forwarding-scanner.gs`.
5. Edit `setupForwardingScannerProperties` and replace:

```text
PASTE_THE_SAME_SECRET_SET_IN_RAILWAY
```

6. Run `setupForwardingScannerProperties`.
7. Run `runThinkSuccessForwardingScanner` once and approve Gmail/URL Fetch permissions.
8. Run `installFifteenMinuteForwardingTrigger`.

## What It Scans

Every 15 minutes it:

1. Fetches saved candidate Gmail addresses from the backend.
2. Searches the central ThinkSuccess Gmail for each candidate Gmail address in forwarded message headers/body.
3. Sends only metadata back to the backend:
   - candidate Gmail
   - last forwarded email timestamp
   - latest subject/sender metadata
   - 7-day count

The admin website then displays `Last email from this Gmail` from the backend `last_email_scan_at` value.
