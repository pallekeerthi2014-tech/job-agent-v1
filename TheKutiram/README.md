# The Kutiram Website

Premium static website for The Kutiram, a family-focused orchard learning farm stay.

## What is included

- Responsive marketing site in plain HTML, CSS, and JavaScript
- Real farm photography and orchard storytelling
- Contact form wired for email submission
- Google Maps location embed
- Zero-dependency local lint/build tooling

## Project structure

```text
TheKutiram/
├── assets/
│   ├── images/
│   └── photos/
├── docs/
│   ├── deployment.md
│   └── seo-checklist.md
├── tooling/
│   ├── build.js
│   ├── check-secrets.js
│   ├── lint.js
│   └── seo-check.js
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── script.js
└── styles.css
```

## Local usage

From the repo root:

```bash
cd TheKutiram
npm run lint
npm run seo:check
npm run build
```

The build output is written to `TheKutiram/dist/`.

## Deployment

Deployment steps are documented in [docs/deployment.md](/Users/keerthiprakash/Documents/Codex/2026-04-22-create-a-production-ready-phase-1/job-agent-v1/TheKutiram/docs/deployment.md).

The site is static, so it can be hosted on:

- Vercel
- Netlify
- GitHub Pages
- Render static hosting
- Any CDN or object storage static site host

## Environment notes

This project does not require secrets to render locally. The included [.env.example](/Users/keerthiprakash/Documents/Codex/2026-04-22-create-a-production-ready-phase-1/job-agent-v1/TheKutiram/.env.example) is only for future deployment wiring such as:

- public site URL
- form routing email
- phone/contact values
- map embed URL

Do not commit a real `.env` file.

## Quality checks

- `npm run lint`: validates required site files and checks for obvious structural issues
- `npm run seo:check`: verifies important SEO tags are present
- `npm run build`: creates a clean static output in `dist/`

## SEO checklist

The basic SEO checklist for this site is documented in [docs/seo-checklist.md](/Users/keerthiprakash/Documents/Codex/2026-04-22-create-a-production-ready-phase-1/job-agent-v1/TheKutiram/docs/seo-checklist.md).

## Secrets policy

- Keep `.env` local only
- Do not add API keys, SMTP passwords, or platform tokens into HTML, CSS, or JavaScript
- If a real form provider token is needed later, inject it through the host platform instead of committing it
