# Simple Admin Management Instructions

## Authority

- Active roadmap: `docs/SIMPLE_ADMIN_MANAGEMENT_ROADMAP.md`.
- Current compact state: `docs/SIMPLE_ADMIN_MANAGEMENT_STATE.md`.
- The old large admin-management roadmap is historical and deferred.
- Old Windows/Codex execution prompts are not authoritative.
- Active branch: `feature/simple-admin-management`.

## Technical baseline

- New work targets MySQL 8.0 with InnoDB.
- SQLite compatibility is not required for new work.
- SQLAlchemy and Alembic remain the persistence and migration tools.
- Historical migrations must never be edited.
- Initial roles are only `owner` and `reseller`.
- Keep implementations minimal.

## Execution rules

- Complete one milestone per execution task.
- Use focused repository searches.
- Run focused tests before regression tests.
- Stop on migration, security, or test failure.
- Never begin the next milestone automatically.
- Never push to `upstream`.
- Never modify, read, stage, move, delete, or ignore:
  - `docs/New Text Document.txt`
  - `scripts/_upstream_marzban.sh`
  - `scripts/build_fork_scripts.py`

## Explicit exclusions

- Wallet
- Billing
- Financial ledger
- Traffic charging
- Reconciliation
- Distributed worker architecture
- Recursive reseller hierarchy
- Support role
- Viewer role
- Generic policy framework
- Complex append-only audit framework
- Scope-assignment tables
- Template versioning
- Large capacity benchmark programs
- CLI authorization overhaul
- Telegram authorization overhaul
- Version changes
- Production releases
