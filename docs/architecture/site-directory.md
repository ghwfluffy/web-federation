# Site Directory

The authenticated root page uses the shared `vendor/federated-banner` package at
the top and opens to the tabbed Federated Services workspace. The default tab is
Apps, which is the authenticated service directory.

The auth management workspace is exposed as `Federated Services`, not as the
public root site. It contains the auth-owned apps/android/users/registration/
account settings tabs. `?tab=apps` opens the service directory,
`?tab=android` opens the Android app download tab, and `?tab=account-settings`
opens the account settings tab. The shared banner's Federated Services app link
uses `?tab=apps`, while the banner Account Settings action uses
`?tab=account-settings`.

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

## Android App Download

When the deployment repo stages a debug Android APK, authenticated users see an
Android tab with an APK download action. The auth API serves metadata at
`/api/v1/mobile/android-app` and streams the APK from
`/api/v1/mobile/android-app/download`. These routes require the normal auth
session and read from a server-local artifact directory configured by
`ANDROID_APK_DIR`.

The APK is not copied into public static assets because deployment-specific
origin and route values are injected into the build. Missing artifacts leave the
Android tab visible with an empty-state message.
