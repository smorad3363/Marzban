---
title: Marzban v5.0.0-rc.8 Release Notes
date: 2026-08-25
tags:
  - marzban
  - release-candidate
  - updater
status: prerelease
---

# Marzban v5.0.0-rc.8

`v5.0.0-rc.8` keeps all application, Admin-management and Dashboard behavior from
`rc.7` and fixes immutable prerelease update parity.

## Update parity

- `marzban update --version v5.0.0-rc.8` selects the immutable `rc.8` container.
- The updater now also downloads the installed `marzban` script from the exact
  `v5.0.0-rc.8` tag.
- Stable version tags keep their existing behavior.
- No application API, UI, database schema, migration, dependency or Docker behavior
  changed.

## Update

```bash
marzban update --version v5.0.0-rc.8
```

## Fresh installation

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.8/scripts/marzban.sh)" @ install --version v5.0.0-rc.8 --database mysql
```

This prerelease does not move `latest` and does not deploy automatically.
