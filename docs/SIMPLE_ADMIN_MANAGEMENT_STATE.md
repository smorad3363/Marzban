# Simple Admin Management State

Use this compact state in a fresh Codex chat together with `AGENTS.override.md`.

## Repository

- Repository: `smorad3363/Marzban`
- Active branch: `feature/simple-admin-management`
- Starting commit: `e03887ea2152ad6f937597f7d2cc4d8bbc2e22f4`
- Application version: `0.8.4`
- Current Alembic head: `b4c2d8e6f1a3`
- Database policy: new work targets MySQL 8.0/InnoDB only
- SQLAlchemy and Alembic remain in use
- Historical migrations are immutable

## Existing baseline

- Security and backend test coverage already exists.
- Environment `SUDOERS` authentication compatibility exists.
- Database admins retain `is_sudo`.
- Phase 2 ownership foundation exists through `owner_admin_id`, `created_by_admin_id`, compatibility behavior, migration coverage, and unit tests.

## Progress

- Current active milestone: Milestone 1 — Admin identity foundation
- Completed milestones: Milestone 0 and Milestone 1
- Next milestone: Milestone 2 — User read isolation
- Focused tests: 28 passed; 5 conditional MySQL tests skipped because `PHASE2_MYSQL_URL` was unavailable
- Backend regression: 57 passed; 5 conditional MySQL tests skipped
- Last successful tests: focused and backend regression suites passed
- Last commit: pending in this commit

## Explicit exclusions

- Wallet, billing, financial ledger, traffic charging, and reconciliation
- Distributed worker architecture
- Recursive reseller hierarchy
- Support and viewer roles
- Generic policy and complex append-only audit frameworks
- Scope-assignment tables and template versioning
- Large capacity benchmark programs
- CLI and Telegram authorization overhauls
- Version changes and production releases
