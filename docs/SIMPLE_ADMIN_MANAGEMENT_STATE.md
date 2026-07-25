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
- Existing non-sudo user ownership/read isolation is inherited and must be reused.
- Existing Admin create/list/update/delete API is inherited and must be adapted.

## Progress

- Current active milestone: User mutation permission enforcement completed
- Completed milestones: Milestone 0, Milestone 1, Admin authentication integration with minimal dashboard management, and user mutation permission enforcement
- Next milestone: Simple admin limits
- Focused user mutation permission tests: 17 passed
- Related security and ownership tests: 47 passed
- Backend regression: 87 passed; 5 conditional MySQL tests skipped because `PHASE2_MYSQL_URL` was unavailable
- Dashboard production build: not rerun because this milestone made no frontend changes; the previous build passed
- Migration: none created; Alembic head remains `b4c2d8e6f1a3`
- Last successful tests: focused, related security, and full backend regression suites passed
- Milestone base commit: `511ea178700e656efa4349492fbc96c1f5cc0e4a`
- Permission toggles are not visible yet; frontend permission controls were outside this milestone.
- Simple admin limits are the next milestone.

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
