---
title: Marzban v5.0.0-rc.5 Release Notes
date: 2026-08-24
tags:
  - marzban
  - release-candidate
  - mysql
  - admin
status: prerelease
---

# Marzban v5.0.0-rc.5

`v5.0.0-rc.5` contains the Admin, Dashboard and permission fixes from `rc.4`
plus the MySQL credit-reconciliation correction found by the release gate.

## Credit behavior

- Owner remains unrestricted by credit ceilings.
- Finite traffic delegated by Owner is still recorded for exact reconciliation.
- Actual-usage parents do not pay upfront delegated traffic for allocated children;
  their account is charged from actual descendant traffic.
- Concurrent reclaim keeps one successful ledger transfer and cannot over-reclaim.

## Verification

- Local backend regression before the MySQL correction: `217 passed, 9 skipped`.
- Targeted release, credit, migration and branding tests: passed.
- GitHub MySQL 8.0 and latest remain the publication gate for this candidate.

## Update

```bash
marzban update --version v5.0.0-rc.5
```

## Fresh installation

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.5/scripts/marzban.sh)" @ install --version v5.0.0-rc.5 --database mysql
```

This prerelease does not move `latest` and does not deploy automatically.
