# Site Directory

The authenticated landing page lists enabled `site_directory_entries` ordered by `display_order`.

Default entries are created lazily when the directory is first loaded. Missing
default entries are backfilled by slug, but existing rows are left alone so
operators can intentionally rename, hide, reorder, or customize launch links:

- Goal Tracker from `GOALS_BASE_URL`, default `/goals`
- Fluffynomics from `MONEY_PLANNER_BASE_URL`, default `/money-planner`
- AI Assistant from `AGENT_BASE_URL`, default `/agent`
- Apartment Gate from `APARTMENT_GATE_BASE_URL`, default `/gate`

Directory URLs are launch links only. Identity, password, registration-code, and profile-image management remains in the auth site. Consumer apps should link back to configured auth management URLs when they run in OAuth mode.
