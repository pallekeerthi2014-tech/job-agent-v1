# Job Source Inventory

Updated: 2026-04-23

## Connected Now

### `generic_ats_json`
- Status: ready now
- Best for: direct JSON feeds, internal APIs, vendor ATS exports
- Freshness quality: high if feed exposes exact posted timestamps
- Maintenance: low

### `generic_html_careers`
- Status: ready now
- Best for: simple public careers pages with stable HTML markup
- Freshness quality: medium, depends on whether the page exposes explicit posted date text
- Maintenance: medium

### `configurable_template`
- Status: ready now
- Best for: custom adapters, testing, controlled feeds, manual mappings
- Freshness quality: depends on provided `posted_date` / `posted_text`
- Maintenance: low

### `greenhouse_board`
- Status: newly connected
- Best for: companies hosted on Greenhouse
- Endpoint pattern: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
- Freshness quality: high when `updated_at` is available
- Maintenance: low

### `lever_postings`
- Status: newly connected
- Best for: companies hosted on Lever
- Endpoint pattern: `https://api.lever.co/v0/postings/{company_handle}?mode=json`
- Freshness quality: medium to high depending on returned create/post timestamps
- Maintenance: low

## Good Next Targets

### Workday
- Status: not connected yet
- Notes: common but inconsistent between tenants; requires tenant-specific discovery
- Recommendation: add after Greenhouse/Lever
- Maintenance: medium to high

### SmartRecruiters
- Status: not connected yet
- Notes: often easier than Workday if public API/JSON is exposed
- Maintenance: medium

### Ashby
- Status: not connected yet
- Notes: often structured and automation-friendly
- Maintenance: low to medium

### Direct company JSON feeds
- Status: partially covered by `generic_ats_json`
- Notes: fast to onboard case by case
- Maintenance: low

## Higher-Risk / Higher-Maintenance Sources

### LinkedIn
- Status: not directly connected
- Notes: useful for discovery, but brittle for automated ingestion and freshness verification at scale
- Recommendation: use for lead discovery, not first-wave pipeline ingestion

### Indeed
- Status: not directly connected
- Notes: similar issue to LinkedIn; search is useful but durable ingestion is harder
- Recommendation: use later, carefully

### Dice
- Status: not directly connected
- Notes: can be useful for recruiter roles, but freshness and dedupe need extra care
- Recommendation: later

## Recommended Connection Order

1. Greenhouse boards
2. Lever postings
3. Selected company JSON/ATS feeds
4. Workday tenants for target employers
5. SmartRecruiters / Ashby
6. Search portals like LinkedIn / Indeed / Dice only after core pipeline is stable
