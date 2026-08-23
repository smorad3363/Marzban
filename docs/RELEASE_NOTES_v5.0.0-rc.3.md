---
title: Marzban v5.0.0-rc.3 Release Notes
date: 2026-08-23
tags:
  - marzban
  - release-candidate
  - admin
  - ux
status: prerelease
---

# Marzban v5.0.0-rc.3

`v5.0.0-rc.3` is an Admin usability release candidate. It keeps the backend
accounting rules from `rc.2` and makes their controls easier to find and use.

## Changes

- Persian copy on the Dashboard and Admin pages is shorter and clearer.
- Editing an Admin now has a separate **increase/decrease credit** section.
- The credit control shows the current balance, requires a reason, uses the existing
  transactional ledger endpoints and keeps a stable idempotency key for retries.
- Seat Credit uses device counts; traffic modes use GiB.
- Credit reclaim requires confirmation and both actions show success/error feedback.
- `marzban set-owner USERNAME` is added to the maintained Marzban-scripts fork.
- The UI also shows the full fallback command for servers with an older script:
  `marzban cli admin set-owner --username USERNAME`.

Pinned Marzban-scripts reference for this fix:
`smorad3363/Marzban-scripts@4830af3566022502159935eeb8636f1af3148502`.

## Staging update

```bash
marzban update --version v5.0.0-rc.3
```

This prerelease does not deploy automatically and does not create final
`v5.0.0`.
