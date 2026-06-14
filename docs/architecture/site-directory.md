# Site Directory

The authenticated landing page is the federated launcher. It uses the shared
`vendor/federated-banner` package at the top and lists enabled
`site_directory_entries` as large launch buttons ordered by `display_order`.

The auth management workspace is exposed as `Federated Services`, not as the
public root site. It contains the auth-owned apps/users/registration/account
settings tabs.

Default entries are created lazily when the directory is first loaded. Missing
default entries are backfilled by slug, but existing rows are left alone so
operators can intentionally rename, hide, reorder, or customize launch links:

- Goal Tracker from `GOALS_BASE_URL`, default `/goals`
- Fluffynomics from `MONEY_PLANNER_BASE_URL`, default `/money-planner`
- AI Assistant from `AGENT_BASE_URL`, default `/agent`
- Apartment Gate from `APARTMENT_GATE_BASE_URL`, default `/gate`
- File Share from `FILE_SHARE_BASE_URL`, default `/filewiz`

Directory URLs are launch links only. Identity, email, phone, timezone,
password, registration-code, and profile-image management remains in the auth
site. Consumer apps should link back to configured auth management URLs when
they run in OAuth mode.
