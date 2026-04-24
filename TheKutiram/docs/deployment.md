# Deployment Guide

## Build

```bash
cd TheKutiram
npm run lint
npm run seo:check
npm run build
```

Deploy the contents of `dist/` to any static hosting provider.

## Vercel

1. Import the repository into Vercel.
2. Set the project root directory to `TheKutiram`.
3. Use:

```text
Build Command: npm run build
Output Directory: dist
```

4. Add your custom domain after the first successful deploy.

## Netlify

1. Create a new site from Git.
2. Select this repository.
3. Set:

```text
Base directory: TheKutiram
Build command: npm run build
Publish directory: dist
```

4. Add domain, SSL, and form settings as needed.

## GitHub Pages

1. Build locally:

```bash
cd TheKutiram
npm run build
```

2. Publish the `dist/` folder through your preferred GitHub Pages workflow or Actions pipeline.

## Before going live

- Replace placeholder values from `.env.example` in your host platform settings or site configuration workflow
- Verify contact phone and form email
- Confirm the map embed points to the correct property
- Test mobile layout on a real device
- Validate that form submissions reach the intended inbox
- Add a domain and analytics only after the content is approved
