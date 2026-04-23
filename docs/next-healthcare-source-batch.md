# Next Healthcare Source Batch

Updated: 2026-04-23

These company sources have now been added to the source registry as initial onboarding entries in `seed-data/job_sources.json`.

## Added In This Batch

- Elevance Health
- Centene
- Molina Healthcare
- Kaiser Permanente
- HCA Healthcare
- Tenet Healthcare

## Current State

Each source is:
- present in the seed registry
- assigned an initial adapter choice
- disabled by default
- annotated with validation notes in `config`

## Why Disabled By Default

These companies still need live portal validation for:
- search/result page endpoint
- stable selectors or JSON response shape
- posted-date extraction quality
- freshness verification quality

## Expected Validation Outcome

- Some will stay on `generic_html_careers`
- Some may move to `generic_ats_json`
- Some may need a dedicated company-specific adapter later

## Suggested Validation Order

1. Centene
2. Molina Healthcare
3. Kaiser Permanente
4. Elevance Health
5. Tenet Healthcare
6. HCA Healthcare
