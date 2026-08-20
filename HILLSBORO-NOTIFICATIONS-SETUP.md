# Hillsboro North Yard Notifications

This adds email notifications without changing the existing sign-in pages.

## Current recipient rules

- Test/Gmail: `calstage1@gmail.com` — ON
- Day Crystal Sugar: `KKyllo@crystalsugar.com` — OFF until a one-time test is requested, then ON automatically starting 2026-10-01
- Night Crystal Sugar: `mdoeden@crystalsugar.com` — OFF until 2026-10-01
- Scheduled Day report: 9:00 AM America/Chicago
- Scheduled Night report: 9:00 PM America/Chicago
- Changes to `data.json`: immediate notification

## IMPORTANT: Gmail setup

GitHub Actions cannot safely use your Gmail password. Use a Gmail App Password.

In the repository:
Settings -> Secrets and variables -> Actions -> New repository secret

Create:

- `SMTP_USER` = the Gmail address that will send the notifications
- `SMTP_APP_PASSWORD` = the 16-character Google App Password for that sender account

Never put the password in `notification-config.json`.

## First test

The initial configuration sends only to `calstage1@gmail.com`.

In Actions, run **Hillsboro Yard Notifications** -> **Run workflow** -> `test` -> `day`.

## One-time Day Crystal Sugar test

Edit `notification-config.json` and change:

`"day_test_once": false`

to:

`"day_test_once": true`

Commit that change. Then manually run the workflow with `test` / `day`.

After the one-time Day test is sent, the script automatically changes `day_test_once` back to `false`.

## October 1, 2026

On October 1, 2026, the script automatically allows both Crystal Sugar recipient groups. Gmail remains enabled.

## Changing switches

- `test_enabled`: turns Gmail testing on/off.
- `day_enabled` and `night_enabled`: master switches for Crystal Sugar after the automatic start date.
- `day_test_once`: one-time Day supervisor test.
- `crystal_sugar_enabled_from`: automatic start date.

## Note about immediate alerts

Immediate alerts are triggered when `data.json` is committed/changed in GitHub. This matches the repository's documented process: the latest exported roster is uploaded as `data.json`.

The existing sign-in pages are not modified.
