---
title: Marzban v5.0.0-rc.2 Release Notes
date: 2026-08-23
tags:
  - marzban
  - release-candidate
  - ci
status: prerelease
---

# Marzban v5.0.0-rc.2

`v5.0.0-rc.2` is a CI-fix release candidate. Application behavior and the v5
feature scope are unchanged from `v5.0.0-rc.1`.

## Correction

The generic MySQL regression jobs no longer execute dedicated Stage 8–11 tests
against shared `marzban_test`. Those tests remain enabled and run sequentially
on MySQL 8.0/InnoDB using isolated databases matching their safety contracts:

- `stage8_*_test`
- `stage9_*_test`
- `stage10_*_test`
- `stage11_*_test`

No meaningful coverage was removed. `v5.0.0-rc.1` remains immutable.

## Staging update

```bash
marzban update --version v5.0.0-rc.2
```

This prerelease does not deploy automatically and does not create final
`v5.0.0`.
