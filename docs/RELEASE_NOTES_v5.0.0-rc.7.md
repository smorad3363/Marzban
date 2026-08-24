---
title: Marzban v5.0.0-rc.7 Release Notes
date: 2026-08-25
tags:
  - marzban
  - release-candidate
  - admin
  - dashboard
status: prerelease
---

# Marzban v5.0.0-rc.7

`v5.0.0-rc.7` contains the migration and accounting safety fixes from `rc.6`
plus the verified Admin-management and Dashboard usability slice.

## Admin management

- Preserves saved Plan-only creation mode and selected Plan categories when the
  Admin form is reopened.
- Keeps custom user creation blocked for Plan-only Admins in the backend.
- Restores mode-aware quick credit actions, freeze/resume, unfreeze and activation.
- Handles exhausted zero-credit accounts without division-by-zero list failures.
- Uses a compact responsive Admin list with permission-aware actions.

## Dashboard

- Adds a compact black-and-gold, data-driven layout using existing scoped account,
  user, activity and system endpoints.
- Avoids duplicate summaries and keeps mobile analytics collapsed by default.
- Shows inline permission-aware Admin and Plan creation actions without navigation.

No dependency, installer, update-script or database-schema change is introduced by
this candidate.

## Update

```bash
marzban update --version v5.0.0-rc.7
```

## Fresh installation

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.7/scripts/marzban.sh)" @ install --version v5.0.0-rc.7 --database mysql
```

This prerelease does not move `latest` and does not deploy automatically.
