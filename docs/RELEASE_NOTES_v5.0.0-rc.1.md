---
title: Marzban v5.0.0-rc.1 Release Notes
date: 2026-08-23
tags:
  - marzban
  - release-candidate
  - v5
status: prerelease
---

# Marzban v5.0.0-rc.1

`v5.0.0-rc.1` is a staging release candidate, not the final `v5.0.0` release.
It does not deploy to any server automatically and does not move the container
`latest` tag.

## Included scope

- Admin, Sub-admin and Owner hierarchy with scoped authorization.
- `LEGACY_COMPAT`, `SEAT_CREDIT`, `USED_TRAFFIC` and `ALLOCATED_TRAFFIC` billing.
- Immutable accounting ledger, grants, reclaims and approval-only refunds.
- Plans with explicit Inbound and Host scope enforcement.
- Customer username namespaces, trial quotas and cleanup.
- Referral attribution and reversible subtree freeze.
- Persistent chunked bulk jobs with per-target idempotency and audit.
- Scope-aware dashboard, localization and `10/25/50` pagination.
- Telegram operational outbox, alerts and encrypted backup workflow.
- Pinned Stage 12 Marzban-scripts fork integration.

## Verification

Stage 13 local and disposable-environment evidence recorded:

- Backend: `212 passed, 9 skipped`.
- Frontend production build: `PASS`, `1751 modules` transformed.
- MySQL 8.0.43/InnoDB: six dedicated migration, accounting, hierarchy, bulk,
  dashboard, pagination, outbox and restore test groups passed.
- Release contract, Python compilation and `git diff --check`: `PASS`.

Browser, live Core/Node/Tunnel, live Telegram delivery and native deployment
`mysqldump` smoke tests were not executed in the available environment. See
[[MARZBAN_CODEX_MASTER_RUNBOOK#Stage 13 — Final Verification Gate]] for full
evidence and remaining uncertainty.

## Staging update

```bash
marzban update --version v5.0.0-rc.1
```

Take and verify a backup before updating. No final `v5.0.0` tag is part of this
candidate.
