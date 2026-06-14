# Site Directory

The authenticated root page uses the shared `vendor/federated-banner` package at
the top and opens to Account Settings by default without the app switcher or app
directory. The root page should not expose connected apps unless the user
explicitly navigates to the Apps tab.

The auth management workspace is exposed as `Federated Services`, not as the
public root site. It contains the auth-owned apps/users/registration/account
settings tabs. `?tab=apps` opens the federated launcher, and
`?tab=account-settings` opens the account settings tab.

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
