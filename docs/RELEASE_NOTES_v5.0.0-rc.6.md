---
title: Marzban v5.0.0-rc.6 Release Notes
date: 2026-08-24
tags:
  - marzban
  - release-candidate
  - mysql
  - migration
status: prerelease
---

# Marzban v5.0.0-rc.6

`v5.0.0-rc.6` contains all Admin, Dashboard, permission and credit fixes from
`rc.5`, plus a MySQL 8.0 downgrade-safety correction.

## Migration correction

MySQL can use the new `(account_status_id, admin_id)` composite index as the
supporting index for the existing account-status foreign key. Dropping that index
directly then fails with error `1553`. The downgrade now restores a single-column
supporting index first and only then removes the composite index.

No data is rewritten. No foreign key is removed or recreated.

## Update

```bash
marzban update --version v5.0.0-rc.6
```

## Fresh installation

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.6/scripts/marzban.sh)" @ install --version v5.0.0-rc.6 --database mysql
```

This prerelease does not move `latest` and does not deploy automatically.
