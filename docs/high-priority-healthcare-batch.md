# High Priority Healthcare Batch

Updated: 2026-04-23

These companies have now been added to the source registry as initial onboarding entries:

- UnitedHealth Group / Optum / UnitedHealthcare
- The Cigna Group / Evernorth
- CVS Health / Aetna
- Humana
- Cardinal Health
- McKesson
- Cencora

## Current State

Each source is:
- present in `seed-data/job_sources.json`
- disabled by default
- assigned an initial adapter choice
- annotated with validation notes

## Coverage Meaning

These companies are now `partially_covered` because:
- they are registered in the platform source catalog
- they can be validated and enabled one by one
- they still need live portal inspection before production ingestion

## Suggested Validation Order

1. UnitedHealth Group / Optum
2. The Cigna Group / Evernorth
3. CVS Health / Aetna
4. Humana
5. Cardinal Health
6. McKesson
7. Cencora
