---
title: Marzban v5.0.0-rc.4 Release Notes
date: 2026-08-24
tags:
  - marzban
  - release-candidate
  - admin
  - dashboard
status: prerelease
---

# Marzban v5.0.0-rc.4

`v5.0.0-rc.4` is a regression-repair release candidate for the Admin hierarchy,
Admin management, user creation and Dashboard.

## Changes

- Owner remains unrestricted; child roles and permissions cannot exceed the parent.
- Super Admin creation limits and delegated Admin creation are configurable.
- Parents using actual-usage billing explicitly choose actual usage or allocated
  traffic for each child; no implicit billing-mode default is applied.
- New children default to Plan-only user creation, and raw custom-user creation is
  rejected unless explicitly delegated.
- Trial quota reset no longer creates an invalid zero-amount ledger transfer.
- Freezing an Admin requires a recorded reason.
- Admin lists, filters, bulk actions and device-limit stages are more compact.
- Audit descriptions are Persian and Dashboard mobile sections start collapsed.
- Black-gold theme, compact charts, quick access and per-Admin logo controls are
  included.

## Verification

- Backend: `217 passed, 9 skipped`.
- TypeScript, production Dashboard build and Admin UX contract: passed.
- Desktop and mobile Browser checks: no horizontal overflow.
- Live MySQL 8.x was unavailable locally; the release workflow remains the required
  MySQL/InnoDB publication gate.

## Staging update

```bash
marzban update --version v5.0.0-rc.4
```

## Fresh installation

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.4/scripts/marzban.sh)" @ install --version v5.0.0-rc.4 --database mysql
```

This prerelease does not move the stable `latest` image tag and does not deploy to
any server automatically.
