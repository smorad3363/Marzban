# Secure Multi-Admin and Reseller Management Roadmap

## 0. Document status and guardrails

- Status: planning only.
- Repository inspected at branch `master`, commit `592cf27` (`feat: rebrand network control dashboard`).
- No application code, migration, dependency, runtime version, branch, tag, or release was changed while producing this document.
- Implementation may begin only after the explicit instruction `Start Phase X`.
- Initial roles are limited to `owner`, `reseller`, `support`, and `viewer`. There is no `manager` role and no recursive admin hierarchy.
- Billing complements classical quotas. It does not replace traffic, expiry, protocol, inbound, rate, or resource limits.

## 1. Current architecture assessment

### 1.1 Runtime and persistence

- The backend is a synchronous FastAPI application using SQLAlchemy sessions and Alembic migrations.
- The runtime version declared in `app/__init__.py` is `0.8.4`.
- The current migration graph appears to end at `63fbd07b9f14`; this must be confirmed with `alembic heads` in the project runtime before creating a migration.
- MySQL is authoritative for production behavior. SQLite remains supported for development, lightweight installations, and fast compatibility tests. Existing migrations use batch operations and contain database-specific compatibility work.
- CRUD functions in `app/db/crud.py` normally commit internally. This makes multi-step authorization, quota, ledger, and audit transactions difficult and should be changed incrementally through transaction-aware services, without a broad refactor.

### 1.2 Admin and authentication model

- `app/db/models.py::Admin` stores `username`, `hashed_password`, `is_sudo`, notification settings, and the aggregate `users_usage` counter.
- `config.SUDOERS` may authenticate environment-defined sudo accounts that have no database row.
- Admin JWTs contain `username`, `is_sudo`, and creation time. Database-backed admins are reloaded on each request, but environment sudo identities are synthesized.
- Authorization is binary: `Admin.get_current` authenticates and `Admin.check_sudo_admin` requires sudo.
- No roles, named permissions, per-admin overrides, suspension state, quota profile, wallet, or audit trail exist.

### 1.3 User ownership and operations

- `users.admin_id` is the current ownership link. It has no immutable creator field.
- `get_validated_user` allows sudo or the admin whose username matches `user.admin.username`.
- List and aggregate endpoints add admin filters at individual call sites. Ownership scope is therefore not structurally guaranteed.
- `/api/user/{username}/set-owner` and CLI `users set-owner` overwrite `admin_id`; there is no transfer history.
- User create, update, delete, reset, revoke, list, usage, expired-user bulk delete, next-plan activation, and owner transfer are implemented in `app/routers/user.py` and `app/db/crud.py`.
- Hard deletion is used. Relationships delete proxy, node-usage, reminder, and next-plan rows; user usage-reset logs and some foreign keys have no explicit preservation policy.
- `reset_user_data_usage` records a reset log but clears node usage. `reset_all_users_data_usage` also clears prior reset logs, which destroys lifetime history.
- The status enum combines classical state (`active`, `limited`, `expired`, `disabled`, `on_hold`) and has no separate billing suspension state.

### 1.4 Templates and classical controls

- Existing `UserTemplate` support includes name, traffic limit, expiry duration, username prefix/suffix, and inbound associations.
- Template create/update/delete requires sudo, but template read/list requires only authentication.
- Templates are not assigned to admins and the normal user-create endpoint accepts a complete free-form `UserCreate` payload.
- Existing templates do not snapshot versions and do not explicitly store initial status, on-hold policy, or allowed protocol policy independent of inbound mappings.
- There are no per-admin classical quotas, creation rate limits, credit limits, or atomic reservation logic.

### 1.5 Usage recording and nodes

- `app/jobs/record_usages.py` polls Xray with `reset=True`, aggregates values, increments `users.used_traffic` and `admins.users_usage`, and writes hourly `NodeUserUsage` rows.
- Node coefficients are stored as SQL `Float` and applied before persistence. Raw bytes and the exact coefficient snapshot are lost.
- The scheduler uses `max_instances=1` only inside one process. It does not provide a distributed lock across multiple application replicas.
- Hourly uniqueness helps aggregation but is not a billing idempotency key. A crash between Xray reset and durable persistence can lose usage; a retry or multi-worker deployment can also produce inconsistent results.
- `NodeUserUsage` rows are cascade-deleted with users and nodes, which is incompatible with durable financial history.

### 1.6 Other callers and integration surfaces

- `app/routers/admin.py` manages admins and bulk activation/disable operations.
- `app/routers/system.py`, `app/routers/core.py`, and `app/routers/node.py` expose counts, inbounds, core, node, logs, and usage paths with current/sudo checks.
- `app/routers/subscription.py` and `app/dependencies.py::get_validated_sub` expose token-based user subscription and usage data. This public token behavior must remain compatible while billing suspension is enforced safely.
- `cli/admin.py`, `cli/user.py`, and `cli/utils.py` directly call CRUD functions and can bypass future HTTP-only policy enforcement.
- `app/telegram/handlers/admin.py` has direct user CRUD, reset, revoke, status, and bulk-operation paths. `app/telegram/handlers/user.py` performs a username-based usage lookup and requires a separate privacy review.
- Background jobs review statuses, reset recurring usage, activate next plans, and auto-delete expired users.
- The React dashboard directly calls current user, usage, reset, revoke, node, and core endpoints. It currently sends free-form user configuration and has no admin-management, role, wallet, audit, or template-assignment screens.
- `app/utils/report.py` sends operational notifications, but these are not a durable audit log. Failed-login reporting currently passes the submitted password to notification functions, which is a critical secret-exposure risk to remove in the security baseline.
- No automated test files were found. The GitHub workflow builds and publishes images but does not run backend, migration, security, or frontend tests.

### 1.7 Production database and capacity objective

#### Production database authority

- The production database is MySQL.
- MySQL is authoritative for production transaction behavior, locking, connection pooling, concurrency, billing, quota enforcement, migration safety, and performance.
- SQLite remains supported only for development, lightweight installations, and fast compatibility tests. A passing SQLite test never substitutes for a required MySQL critical-path test.
- Critical migration, quota-concurrency, billing-idempotency, worker-concurrency, reconciliation, and performance tests must run on MySQL.
- Phase `1D` must inspect and document suitable SQLAlchemy pool settings, transaction isolation, required indexes, slow-query logging, connect/read/write timeouts, pool wait behavior, and deadlock detection/retry behavior.
- Do not optimize MySQL configuration without benchmark evidence. Pool sizes, indexes, isolation, and query changes must not be optimized speculatively; every optimization requires a production-like benchmark or query-plan result that identifies the bottleneck and a before/after measurement.

#### Capacity target and definitions

- Capacity objective: support at least **50,000 registered users on MySQL**.
- Support for 50,000 registered users must not be claimed until the complete production-like benchmark and Final Gate `GF` pass.
- `registered_users`, `active_users`, `concurrently_online_users`, and `users_processed_per_usage_job` are separate measurements and must be reported separately.
- The 50,000-user objective means 50,000 registered database users; it must never be interpreted or advertised as 50,000 concurrently online users.
- Capacity approval applies to the complete system, including APIs, Xray configuration/reload, usage jobs, nodes, audit, quotas, ledger, billing, reconciliation, background jobs, MySQL, and operational resources. Successful insertion of 50,000 rows alone is not capacity evidence.

#### Staged generated-data benchmarks

Use generated, non-production data at these mandatory stages:

1. 5,000 registered users.
2. 10,000 registered users.
3. 25,000 registered users.
4. 50,000 registered users.

At each applicable stage, test:

- User list, search, filtering, pagination, counts, and statistics.
- User creation, update, reset, disable, and soft deletion.
- Xray configuration generation and reload behavior.
- Usage collection and usage-recording jobs.
- Node usage aggregation.
- Audit-event growth.
- Quota checks and concurrent user creation.
- Wallet ledger and billing-event processing.
- Billing reconciliation.
- Background-job duration.
- MySQL query latency, lock waits, deadlocks, pool exhaustion, CPU, RAM, disk I/O, and database growth.

Indexes and query changes require `EXPLAIN`/query-plan evidence plus benchmark results. A change is accepted only when it improves the measured target without violating correctness, ownership, ledger, billing, or migration invariants.

#### Capacity acceptance report

Every staged benchmark report must record:

- Dataset size and data-generation profile.
- Number of nodes.
- Registered-user, active-user, concurrently-online-user, and per-usage-job user counts.
- Simulated concurrent requests and workload mix.
- Test hardware and operating environment.
- MySQL version and configuration, SQLAlchemy pool settings, and transaction isolation.
- P50, P95, and P99 latency by tested operation.
- Background-job and Xray configuration/reload completion duration.
- Throughput.
- Error and timeout rate.
- Database size and growth.
- Slow queries and relevant query plans.
- MySQL lock waits, deadlocks, and pool-exhaustion events.
- Application/MySQL CPU, RAM, and disk I/O.
- Identified bottlenecks, tested changes, before/after evidence, and unresolved limitations.

Capacity acceptance requires correct results, stable resource behavior, no unexplained billing discrepancy, no ownership/permission leak, and no unresolved data-integrity failure at the target workload.

## 2. Existing functionality to reuse

- Reuse the `Admin`, `User`, `UserTemplate`, `NodeUserUsage`, `NodeUsage`, and reset-log concepts, extending their schemas rather than creating parallel identity or template systems.
- Reuse FastAPI dependencies as the integration point, but move authorization decisions into a central policy service callable from REST, CLI, Telegram, and jobs.
- Reuse template inbound associations and current server-side proxy/inbound derivation.
- Reuse Xray polling and hourly usage collection as an input adapter; do not use its coefficient-adjusted rows as the financial source of truth.
- Reuse `request` data available in FastAPI for request ID, IP address, and user agent audit context.
- Reuse current user response and subscription behavior through additive fields and compatibility endpoints.
- Reuse Alembic and the current SQLite/MySQL compatibility conventions.
- Reuse React context, request wrapper, localization, and modal patterns for later UI phases.
- Reuse report notifications only as downstream notifications after a durable audit/ledger transaction succeeds.

## 3. Missing functionality

- Stable database identity for environment sudo accounts.
- Explicit roles and deny-by-default named permission evaluation.
- Per-admin allow/deny overrides and scoped support/viewer access.
- Immutable `created_by_admin_id`, mutable `owner_admin_id`, and transfer history.
- Central, mandatory ownership scoping for every access path.
- Append-only audit records with safe redaction and required reasons.
- Template assignment, versioning/snapshots, server-side application, and custom-create separation.
- Classical quota definitions, effective quota resolution, atomic reservations, and rate limiting.
- Exact-money wallet accounts, append-only ledger entries, cached balance reconciliation, and adjustments.
- Raw usage events, coefficient and pricing snapshots, charge records, billing periods, idempotency, distributed worker locking, and reconciliation.
- Shadow mode, warning thresholds, creation blocking, billing suspension, grace/credit-limit behavior, and safe restoration.
- Soft deletion and historical retention for users/admins/nodes referenced by billing and audit data.
- Admin-management APIs and UI for roles, permissions, quotas, templates, balances, billing, and audit.
- Automated tests and CI quality gates.

## 4. Security risks

1. Ownership checks are caller-dependent, making missed filters and IDOR regressions likely.
2. CLI, Telegram, background jobs, bulk endpoints, exports added later, and dashboard APIs can bypass route-only authorization.
3. Hard deletion and cascades can destroy evidence and financial usage history.
4. Bulk reset currently erases reset history and node usage, preventing correct reconciliation.
5. Failed-login notifications may transmit plaintext submitted passwords.
6. Direct CRUD commits prevent atomic permission/quota/action/audit/ledger transactions.
7. `Float` coefficients are unsuitable for historical financial computation.
8. There is no durable actor record for environment sudo identities.
9. Current admin deletion can orphan users or erase identity context unless foreign-key behavior is explicitly constrained.
10. Template values supplied through free-form creation can bypass future reseller limits unless ignored server-side.
11. Scheduler single-instance settings do not prevent duplicate processing across replicas.
12. Audit/report payloads may contain subscription URLs, proxy credentials, webhook values, or other secrets unless field-level redaction is centralized.
13. Ownership transfer without immutable creator and transfer history weakens accountability.
14. Automatic activation logic can reactivate users disabled for a different reason unless billing suspension is modeled separately.

## 5. Compatibility risks

- Renaming or immediately removing `admin_id` would break ORM relationships, CLI commands, reports, dashboard filters, and integrations.
- Making ownership columns non-null before backfill would fail for legacy unowned users and environment sudo owners.
- Changing hard delete to soft delete affects username uniqueness, list counts, Xray configuration, auto-delete jobs, and subscription-token behavior.
- Splitting status behavior can change current `active`, `disabled`, `limited`, `expired`, and `on_hold` transitions.
- Moving coefficient application changes displayed usage unless raw and billable usage are separated clearly.
- Tightening template creation can break existing API clients that send `UserCreate` directly.
- Adding database locks must account for SQLite limitations and MySQL transaction semantics.
- Admin response schema changes can break the dashboard and third-party API clients.
- The latest repository tags are `v1`, `v2`, and `v3`, while runtime/API version remains `0.8.4`; release numbering must be resolved before the first stable checkpoint.

## 6. Proposed role and permission model

### 6.1 Roles

- `owner`: system-wide control, ownership transfer, role/permission/quota changes, ledger adjustments, billing policy, audit access, and node management.
- `reseller`: operates only owned users, uses assigned templates, views own quota/wallet/billing data, and has no ownership transfer or admin-policy authority by default.
- `support`: scoped operational access, normally read/update/status/reset/revoke without create/delete/export/billing-adjust permissions.
- `viewer`: scoped read-only access.

### 6.2 Permission catalog

Initial permissions:

- `user.read`
- `user.create_from_template`
- `user.create_custom`
- `user.update`
- `user.delete`
- `user.reset_usage`
- `user.change_status`
- `user.revoke_subscription`
- `user.transfer_ownership`
- `user.export`
- `user.bulk_update`
- `admin.read`
- `admin.create`
- `admin.update`
- `admin.suspend`
- `admin.adjust_balance`
- `billing.read`
- `billing.manage_policy`
- `audit.read`
- `template.read`
- `template.manage`
- `quota.read`
- `quota.manage`
- `node.read`
- `node.manage`

Role defaults are data-driven or code-versioned constants. Per-admin overrides use named rows with effect `allow` or `deny`; an explicit deny wins. Unknown permissions, missing roles, inactive admins, and evaluation errors deny access. Permission answers whether an operation is allowed; quota answers how much is allowed. Ownership/scope is evaluated after permission and cannot be overridden by a broad UI filter.

## 7. Proposed ownership model

- Add `users.created_by_admin_id`: immutable, nullable only during compatibility backfill, then required for new users.
- Add `users.owner_admin_id`: current owner, indexed, required for new users.
- Keep `users.admin_id` temporarily as a compatibility alias/source during expand-and-contract migration. Dual-write and consistency checks precede any later deprecation.
- Add `admin_scope_assignments` for owner-granted support/viewer scope. Initial scope types should be `all_owner_users`, selected owner admins, or selected users; do not add parent-child recursion.
- Add append-only `user_ownership_transfers` with user snapshot/reference, previous owner, new owner, actor, reason, request ID, and timestamp.
- Only `owner` with `user.transfer_ownership` may transfer ownership. Transfers lock the user and both relevant quota/wallet contexts, validate destination quotas, update owner atomically, preserve creator, and write audit/transfer records.
- Every repository query that returns protected users accepts an `AccessContext` and applies scope server-side. Direct unscoped query helpers are restricted to explicitly named system-job repositories.
- A lookup outside scope returns `404` where existence concealment is appropriate; forbidden operations on known scoped resources return `403` consistently.

## 8. Proposed database schema changes

Names are proposed and should be finalized in Phase 1 architecture decisions.

### 8.1 Identity and authorization

- `admins`: add `role`, `status`, `suspended_at`, `suspended_by_admin_id`, `deleted_at`, and optional stable record support for environment sudo identities.
- `admin_permission_overrides`: `id`, `admin_id`, `permission`, `effect`, `created_by_admin_id`, `reason`, timestamps; unique on `(admin_id, permission)`.
- `admin_scope_assignments`: `id`, `admin_id`, `scope_type`, `owner_admin_id`, optional `user_id`, actor, timestamps, uniqueness constraints.
- `users`: add `created_by_admin_id`, `owner_admin_id`, `deleted_at`, `deleted_by_admin_id`, `delete_reason`, and billing suspension fields or a separate suspension table.
- `user_ownership_transfers`: append-only transfer history.

### 8.2 Templates and quotas

- Extend `user_templates` with `version`, `status`, `initial_user_status`, `on_hold_*`, allowed protocol configuration, and timestamps.
- Prefer immutable `user_template_versions` containing the full validated configuration JSON plus searchable columns; editing creates a new version.
- `admin_template_assignments`: `admin_id`, `template_id`, optional allowed version range/current version, actor, timestamps.
- `user_creation_snapshots`: `user_id`, template/version IDs, normalized applied configuration, creator, timestamp. Secrets and generated credentials are excluded.
- `admin_quota_profiles`: exact quota limits, credit limit in integer units, grace/rate settings, timestamps and actor.
- `quota_reservations` only if required for workflows spanning transactions; synchronous creation should prefer row locks and transactional counters.

### 8.3 Audit and finance

- `audit_events`: append-only actor, action, target, safe before/after JSON, reason, request ID, IP, user agent, source (`api`, `cli`, `telegram`, `job`), timestamp, integrity metadata.
- `wallet_accounts`: one per billable admin, currency/credit-unit definition, cached balance integer, lock/version field, timestamps.
- `wallet_ledger_entries`: signed integer amount, entry type, idempotency key, reference type/ID, actor, reason, metadata, timestamp; unique idempotency key and no update/delete application path.
- `pricing_versions`: immutable unit price and rounding rules using integer credit units or exact `Decimal`/`NUMERIC`, effective period, actor.
- `usage_events`: raw bytes, user snapshot/reference, owner snapshot/reference, node snapshot/reference, period, source cursor/event key, timestamps, unique idempotency key.
- `usage_charges`: raw bytes, exact coefficient snapshot, pricing version, charged amount, owner, user, node, period, ledger reference, idempotency key, mode (`shadow`/`enforced`), timestamps.
- `billing_periods` and `billing_reconciliation_runs`: closure status, totals, discrepancies, actor/job identity, timestamps.
- Historical tables use restrictive or nullable foreign keys plus immutable text/ID snapshots. Deleting users, admins, or nodes must never cascade into audit, usage, charge, reconciliation, or ledger tables.

### 8.4 Exact numeric rules

- Raw usage is integer bytes.
- Wallet amount is a signed `BigInteger` in a documented smallest credit unit unless maximum-volume analysis requires `NUMERIC`.
- Coefficients and prices use `NUMERIC(p,s)`/Python `Decimal`; never binary floating point.
- A single documented rounding rule is applied once per charge aggregation boundary and stored with the pricing version.

## 9. Proposed API changes

### 9.1 Additive endpoints

- `POST /api/users/from-template` with only `username` and `template_id` for normal reseller use.
- `POST /api/users/custom` for callers with `user.create_custom`.
- `POST /api/users/{username}/transfer-owner` with destination and required reason.
- `GET/POST/PATCH /api/admins...` for role, status, permissions, scopes, quotas, and template assignments.
- `GET /api/me/capabilities`, `/api/me/quota`, `/api/me/wallet`, and `/api/me/templates`.
- `GET /api/audit-events` with owner-only or explicitly scoped access.
- `GET /api/billing/charges`, `/api/billing/periods`, and `/api/billing/reconciliation`.
- `POST /api/admins/{id}/wallet-adjustments` requiring signed amount, typed reason, idempotency key, and owner permission.

### 9.2 Existing endpoint transition

- Preserve current `/api/user` during a deprecation window. Owners with `user.create_custom` retain compatible behavior; resellers are routed to server-side template creation after enforcement is enabled.
- Add permission and ownership policy checks to every current user/admin/node/system/core endpoint before changing response shapes.
- Bulk operations accept explicit selection/filter plus reason, resolve scope server-side, lock affected rows deterministically, enforce a maximum batch size, return per-item outcomes, and emit a parent audit event plus item events.
- Export and usage endpoints use the same scoped repository as list/read operations.
- Subscription endpoints continue token validation but suppress service when the user is manually/classically ineligible or billing-suspended, according to a documented compatibility matrix.
- Use stable machine-readable error codes such as `permission_denied`, `ownership_denied`, `quota_exceeded`, `template_not_assigned`, `insufficient_balance`, and `billing_suspended`.

## 10. Proposed audit architecture

- Create an `AuditContext` at each entry point with actor ID, source, request ID, IP, user agent, and reason.
- REST middleware accepts/creates a request ID. CLI creates an invocation ID. Telegram records the mapped admin and update/chat identifiers without message secrets. Jobs use a durable system actor and run ID.
- Services capture safe before/after values inside the same database transaction as the sensitive action.
- Required reasons: ownership transfer, permission/role changes, quota changes, manual balance adjustments, refunds/corrections, usage reset, admin suspension, and bulk delete/status actions.
- Central allowlist/redaction excludes passwords, password hashes, JWTs, subscription tokens/URLs, proxy credentials/settings secrets, private keys, TLS material, webhook secrets, and authorization headers.
- Audit tables expose insert-only repository methods. Database grants/triggers should be considered in production to reject updates/deletes.
- Operational notifications occur after commit and reference the audit event ID; notification failure does not roll back the committed action.

## 11. Proposed quota architecture

Effective quotas cover maximum total users, active users, allocated traffic, traffic per user, expiration duration, unlimited users, assigned templates, protocols, inbounds, creation rate, and negative-balance credit limit.

- Resolve the effective quota once from owner defaults and admin overrides. A missing limit is deny or unlimited only according to an explicit field definition; never infer from zero inconsistently.
- Normalize user/template configuration before checking limits.
- Execute quota validation and mutation in one transaction. Lock the admin quota/account row with `SELECT ... FOR UPDATE` on MySQL and use a safe serialized transaction strategy for SQLite.
- Maintain transactional counters only if measured query cost requires them. Counters must be reconcilable from canonical rows.
- Acquire locks in a fixed order: owner/admin, wallet, template assignment, user rows. This prevents deadlocks in bulk and transfer operations.
- For creation rate limits, store durable bucket/counter rows or use a transactional database-backed limiter; an in-process cache is not authoritative.
- Return the violated quota name, current value, requested delta, and limit without leaking other owners' data.

## 12. Proposed template architecture

- Extend the existing `UserTemplate`; do not create a duplicate template subsystem.
- Template versions control data limit, expiry duration, allowed protocols, allowed inbounds, initial status, on-hold behavior, and username prefix/suffix.
- Assign templates explicitly to admins. Owners may assign; resellers may list/read only assigned active versions.
- Normal reseller input is exactly `username` and `template_id`. The service loads the assigned active version, builds the effective username, creates/generates protocol settings server-side, validates quotas, and persists the applied snapshot.
- Reject or ignore any client-supplied template fields; prefer strict request models with `extra="forbid"`.
- Free-form create is a separate endpoint/service action requiring `user.create_custom`, plus all quota/protocol/inbound checks.
- Later edits to a template create a new version and do not alter existing users. An explicit migration operation may apply a newer version to selected users with preview, permission, quota validation, and audit.

## 13. Proposed wallet and billing architecture

### 13.1 Ledger

- Every balance mutation inserts one append-only ledger entry of type `manual_credit`, `manual_debit`, `traffic_charge`, `refund`, or `correction`.
- The cached balance is updated atomically with the ledger insert while holding the wallet row lock.
- Idempotency keys are mandatory and unique. Manual actions accept a caller key; traffic charges derive it from the immutable usage event/period/pricing version.
- Refunds/corrections create compensating entries and reference the original entry. No historical row is edited.
- Reconciliation compares cached balance with the ledger sum and never silently repairs differences; a correction requires owner approval and audit.

### 13.2 Usage and charging

- Persist raw per-node usage before coefficient application. Keep operational adjusted totals separate from financial raw events.
- A durable event contains raw bytes, node, user, owner at event time, period boundaries, source cursor/key, and ingestion ID.
- The charge worker claims uncharged events using row locks/skip-locked or an equivalent lease, snapshots exact coefficient and pricing, calculates once, and atomically writes charge, ledger entry, and event state.
- Ownership transfer takes effect at a defined timestamp/usage boundary; already-ingested periods remain charged to their stored owner snapshot.
- Unlimited users are charged normally because billing uses actual raw usage, not `data_limit`.
- Distributed locking/claiming is required even though the local scheduler uses `max_instances=1`.
- Billing periods close only after late-event policy and reconciliation checks pass.

### 13.3 Shadow mode and enforcement

- Shadow mode records expected charges and balance projections but creates no enforceable debit, blocks no creation, and suspends no user.
- Compare shadow totals with raw usage and current operational totals for at least one representative billing cycle.
- Enforcement is gated by idempotency, concurrent-worker, restart/retry, reconciliation, coefficient snapshot, migration, and rollback tests.
- Policies are separate flags: warnings, creation blocking, grace period, negative credit limit, and suspension.
- Alert thresholds are idempotent per wallet/threshold/billing episode.

## 14. Usage-reset and deletion behavior

### 14.1 Usage reset

- Reset creates an immutable reset/checkpoint event containing cumulative raw usage and the last billed event/cursor.
- It resets only the classical visible quota counter and relevant Xray counter state.
- It does not delete raw usage, node usage, prior reset logs, charges, ledger entries, or audit records.
- It does not refund, duplicate, subtract, or make previously billed traffic negative.
- Billing continues from the new checkpoint using source-event idempotency, independent of `users.used_traffic`.
- Manual and bulk resets require `user.reset_usage`, ownership scope, reason, audit, and per-user results.

### 14.2 Deletion

- User deletion becomes soft deletion: set `deleted_at`, actor, and reason; remove service access and Xray presence; preserve username/history.
- Deleted users are excluded from normal queries and counts through explicit repository defaults, not ad hoc UI filtering.
- Subscription tokens for deleted users return the existing non-disclosing not-found behavior.
- Admin deletion/suspension does not cascade. Owned users must first be transferred, frozen by policy, or left under a documented owner-owned holding state.
- Physical purge is a separately approved retention process and can never purge ledger, audit, billing, or historical usage references.

## 15. Migration strategy

1. Establish test fixtures for SQLite and MySQL and confirm the single Alembic head.
2. Use expand-and-contract migrations: add nullable columns/tables/indexes first, deploy compatible dual-read/dual-write code, backfill in bounded batches, validate, then add constraints.
3. Materialize database rows for environment sudo identities or map them to a reserved owner identity before ownership backfill.
4. Backfill `owner_admin_id` from `admin_id`; define an owner-controlled holding owner for null legacy rows. Backfill `created_by_admin_id` from the best available owner and mark provenance as inferred in an audit/migration report.
5. Preserve `admin_id` during the compatibility window and run consistency queries.
6. Convert future coefficient snapshots to exact decimals without rewriting historical operational usage. Legacy periods are marked `legacy_unpriced` unless an approved deterministic reconstruction exists.
7. Add ledger balances as zero/opening entries according to an owner-approved import policy; never infer money from `admins.users_usage`.
8. Backfill template version 1 and assignments explicitly; do not grant all resellers all templates without approval.
9. Add indexes online where supported and size long-running operations using production-like data.
10. Record row counts, checksums, null counts, orphan checks, and duration for every migration stage.

## 16. Rollback strategy

- Each phase is additive until verified. Feature flags default off for new authorization enforcement, template enforcement, billing shadow, and billing enforcement.
- Code rollback must remain compatible with newly added nullable tables/columns through stable checkpoints.
- Before constraint/backfill phases, take and verify a database backup and rehearse restore.
- Do not downgrade by deleting financial/audit tables after they contain records. Roll back behavior with feature flags and forward-fix schema.
- Billing enforcement rollback disables new debits/blocks/suspensions, leaves append-only history intact, and runs reconciliation. Compensating ledger entries require approval; rows are never deleted.
- Suspension rollback restores only users with an active billing-suspension record and only if their manual/classical state remains eligible.
- Every phase below identifies its own narrow rollback.

## 17. Backward-compatibility strategy

- Maintain current user endpoints and response fields during a documented deprecation window.
- Treat current sudo users as `owner` in compatibility mode, while recording how the identity maps to a database actor.
- Treat current non-sudo admins as `reseller` with equivalent owned-user permissions initially, except features explicitly gated for safety.
- Keep `admin_id` synchronized with `owner_admin_id` until all internal and external callers migrate.
- Preserve all current classical status transitions and add billing eligibility as an orthogonal state.
- Preserve operational usage displays; add separate `raw_usage`, `billable_usage`, and `charged_amount` reporting rather than redefining existing values silently.
- Provide feature flags and API capability discovery so the existing dashboard can function before the new UI ships.
- Publish deprecation warnings, compatibility matrix, migration guide, and rollback instructions before removing any legacy path.

## 18. Test strategy overview

- Introduce `pytest`, FastAPI test client/httpx support, factories, deterministic clock, and database fixtures only in an approved implementation phase.
- Run unit tests on every commit and SQLite compatibility tests where useful. Run every critical migration, transaction, locking, quota-concurrency, billing-idempotency, worker-concurrency, reconciliation, and performance test on MySQL.
- Use generated non-production datasets and progress through 5,000, 10,000, 25,000, and 50,000 registered users. A phase gate may stop at the stage appropriate to that phase, but Gate `G39` and Final Gate `GF` must complete the 50,000-user stage.
- Include positive and negative authorization tests for every sensitive operation.
- Property/invariant tests cover ledger sums, no duplicate charge, monotonic usage event processing, ownership isolation, and restoration eligibility.
- Use fault injection at commit boundaries, worker restarts, duplicate delivery, stale locks, and Xray reset/persist failure boundaries.
- Performance tests cover the complete workload catalog in Section 1.7, including scoped user operations, Xray generation/reload, usage jobs, node aggregation, quota locking, audit growth, ledger/billing/reconciliation, background jobs, MySQL latency/locks/deadlocks/pool behavior, and host/database resources.
- Every capacity result uses the acceptance-report schema in Section 1.7. Index and query changes require query plans and measured before/after evidence.

## 19. Versioning strategy

- `0.8.4` is the current authoritative runtime and product version unless the owner explicitly approves a different scheme.
- Custom repository tags `v1`, `v2`, and `v3` are treated as non-authoritative deployment/history labels for this roadmap. They do not block early security, test, ownership, or authorization phases.
- Proposed stable checkpoints:
  - `0.8.5`: secret remediation, test/CI baseline, ownership, centralized authorization, roles, audit, scoped user operations, soft deletion, and cross-entry-point parity.
  - `0.8.6`: template assignment/server-side creation, classical quotas, atomic quota enforcement, secured backend admin APIs, and their regression coverage.
  - `0.8.7`: wallet/ledger, raw usage, pricing snapshots, idempotent billing, shadow mode, reconciliation, and read-only operational views; enforcement remains off by default.
  - `0.8.8`: approved billing enforcement, safe suspension/restoration, complete UI groups, operational hardening, and final release validation.
- Small phases and commits do not receive individual version changes. A patch version is changed only when the corresponding checkpoint is complete, tested, usable, and explicitly approved.
- Any future move to `3.x.y` is a later release-governance decision and must align `app.__version__`, image tags, documentation, and Git tags in its own approved phase.

## 20. Git branching, commit, and push strategy

- Create one dedicated branch after approval, suggested `feature/secure-admin-reseller-management`.
- Keep one focused commit or a small coherent commit group per phase.
- Run the phase test gate before committing. Push only after the user approves and the phase is complete.
- Never force-push. Do not mix rebranding, dependency cleanup, formatting sweeps, or unrelated fixes.
- Tag/release only the stable checkpoints in Section 19.
- Preserve migration and feature-flag checkpoints as clear rollback points.
- Existing untracked files `scripts/_upstream_marzban.sh` and `scripts/build_fork_scripts.py` are outside this roadmap and must not be included accidentally.
- Suggested pull request mode: draft until a stable checkpoint passes its testing phase; require security and migration review before enforcement.

## 21. Refined implementation phases

This section supersedes Appendix A. It contains **43 independently executable implementation phases**: `1A` through `1D`, followed by `2` through `40`.

### 21.1 Mandatory execution rule for every phase

Every phase below includes and is governed by this complete rule:

1. Implement only the requested phase.
2. Run only the relevant phase tests plus required regression tests.
3. Report changed files, tests, risks, and limitations.
4. Do not commit or push until the owner explicitly approves.
5. After approval, commit and push that phase separately.
6. Stop and wait for the next explicit `Start Phase X` instruction.

### Phase 1A — Remove password/secret exposure and add centralized redaction

- Objective: close the known credential-reporting exposure first.
- Exact scope: stop forwarding submitted passwords; add reusable redaction for logs and notifications.
- Explicit exclusions: tests/CI setup, authorization redesign, database work.
- Expected files: `app/utils/report.py`, notification adapters, new redaction utility, focused tests.
- Database changes: none.
- API behavior: unchanged.
- Security checks: redact passwords, hashes, tokens, subscription URLs, proxy credentials, private keys, webhooks, and authorization headers.
- Tests required: Gate `G1A`.
- Definition of done: known and representative secret values never leave the process through reporting/logging.
- Rollback method: revert the focused reporting/redaction change; no data rollback.
- Dependencies: none.
- Decisions required before starting: none.
- Suggested commit message: `security: remove credential reporting and centralize redaction`.
- Stable version checkpoint: contributes to `0.8.5`; no phase-local bump.
- Execution rule: all six steps in Section 21.1 apply.

### Phase 1B — Add the minimal backend test harness and CI baseline

- Objective: make later security work independently verifiable.
- Exact scope: minimal `pytest` fixtures, API smoke tests, isolated test database, and non-publishing CI test job.
- Explicit exclusions: application refactors, full coverage, frontend tests, dependency upgrades beyond approved test-only requirements.
- Expected files: `tests/`, test configuration, test-only dependency declaration, `.github/workflows/`.
- Database changes: none outside disposable fixtures.
- API behavior: unchanged.
- Security checks: test secrets are synthetic; CI has read-only/minimal permissions and does not publish images.
- Tests required: Gate `G1B`.
- Definition of done: clean local and CI baseline runs deterministically.
- Rollback method: revert test/CI files.
- Dependencies: Phase `1A`.
- Decisions required before starting: approval of the minimal test runner/dependency mechanism; stop only if unavailable.
- Suggested commit message: `test: add minimal backend harness and CI baseline`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: all six steps in Section 21.1 apply.

### Phase 1C — Inventory authorization entry points and bypass risks

- Objective: establish a complete caller/control matrix.
- Exact scope: REST, subscription, CLI, Telegram, jobs, dashboard, exports, bulk paths, direct CRUD, and system actors.
- Explicit exclusions: enforcement or code-path changes.
- Expected files: security inventory documentation and optional architecture-test manifest.
- Database changes: none.
- API behavior: unchanged.
- Security checks: identify every unscoped read/mutation and trusted bypass.
- Tests required: Gate `G1C`.
- Definition of done: every protected operation has caller, current guard, risk, target permission, ownership rule, and future test owner.
- Rollback method: revert documentation/manifest only.
- Dependencies: Phase `1B`.
- Decisions required before starting: none.
- Suggested commit message: `docs: inventory authorization entry points and bypass risks`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: all six steps in Section 21.1 apply.

### Phase 1D — Confirm migration, database, sudo identity, and version baselines

- Objective: resolve only the decisions needed before schema work.
- Exact scope: confirm the Alembic head; record MySQL as the authoritative production database; retain SQLite only for development/lightweight/fast compatibility use; document production topology, environment sudo identity strategy, and `0.8.4` authority; inspect candidate SQLAlchemy pool settings, transaction isolation, indexes, slow-query logging, connection/pool timeouts, and deadlock retry behavior.
- Explicit exclusions: migrations, identity implementation, branches, tags, version changes, and any MySQL/pool/index optimization without benchmark evidence.
- Expected files: roadmap/architecture decision records only.
- Database changes: none.
- API behavior: unchanged.
- Security checks: environment sudo actors must map to durable accountability before audited mutations; production transaction/locking assumptions must be MySQL-specific and explicit.
- Tests required: Gate `G1D`.
- Definition of done: the MySQL/SQLite authority boundary, Alembic head, production topology, pool/isolation/timeout/slow-query/deadlock-retry candidates, sudo identity strategy, and evidence-only optimization rule are recorded.
- Rollback method: revise the decision record.
- Dependencies: Phase `1C`.
- Decisions required before starting: production topology and environment sudo identity strategy; MySQL authority and continued limited SQLite support are already established requirements.
- Suggested commit message: `docs: confirm persistence identity and version baselines`.
- Stable version checkpoint: none.
- Execution rule: all six steps in Section 21.1 apply.

### Phase 2 — Ownership schema foundation

- Objective: add immutable creator and mutable owner compatibly.
- Exact scope: additive ownership columns, backfill, dual-write, validation.
- Explicit exclusions: transfer API and general authorization enforcement.
- Expected files: database models, one migration, user schemas/repository, migration tests.
- Database changes: `created_by_admin_id`, `owner_admin_id`, indexes/FKs; retain `admin_id`.
- API behavior: additive owner data only where already authorized.
- Security checks: creator immutability, non-cascading admin references, explicit legacy-null handling.
- Tests required: Gate `G2`.
- Definition of done: all rows validate and new writes keep legacy/current owner fields consistent.
- Rollback method: disable dual-write; retain additive schema until forward cleanup.
- Dependencies: Phase `1D`.
- Decisions required before starting: legacy null-owner destination and inferred-creator policy; stop if unapproved.
- Suggested commit message: `feat: add compatible user ownership fields`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 3 — Central authorization context and policy service

- Objective: create one deny-by-default authorization interface.
- Exact scope: `AccessContext`, scoped repository contract, policy result/error model, explicit system context.
- Explicit exclusions: broad caller migration and role storage.
- Expected files: new security/service/repository modules and focused dependency integration.
- Database changes: none.
- API behavior: pilot paths gain consistent concealed `404`/`403` codes.
- Security checks: missing context denies; system bypass is named and constrained.
- Tests required: Gate `G3`.
- Definition of done: pilot read path cannot execute unscoped.
- Rollback method: disable pilot enforcement; retain context plumbing.
- Dependencies: Phase `2`.
- Decisions required before starting: concealed-not-found policy; recommended default is `404` for out-of-scope objects; non-blocking unless rejected.
- Suggested commit message: `feat: centralize access context and policy decisions`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 4 — Role defaults and permission overrides

- Objective: implement `owner`, `reseller`, `support`, and `viewer`.
- Exact scope: catalog, role defaults, explicit allow/deny overrides, capability resolution, admin suspension check.
- Explicit exclusions: management UI and operation-by-operation rollout.
- Expected files: admin model/migration, permission service, capability endpoint, tests.
- Database changes: role/status fields and `admin_permission_overrides`.
- API behavior: additive `/api/me/capabilities`.
- Security checks: explicit deny wins; unknown/missing/suspended denies; prevent last-owner lockout.
- Tests required: Gate `G4`.
- Definition of done: deterministic permission matrix passes.
- Rollback method: compatibility mapping to sudo/non-sudo; retain rows.
- Dependencies: Phases `2`–`3`.
- Decisions required before starting: support/viewer defaults and scope shapes; stop if unapproved.
- Suggested commit message: `feat: add roles and permission overrides`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 5 — Append-only audit foundation

- Objective: persist safe actor/action evidence.
- Exact scope: audit context, insert-only repository, reason validation, redaction, one pilot action.
- Explicit exclusions: audit UI and complete caller adoption.
- Expected files: audit model/migration, middleware/adapters, pilot service, tests.
- Database changes: `audit_events`.
- API behavior: no public audit list yet.
- Security checks: safe allowlist, source/request identity, no update/delete path.
- Tests required: Gate `G5`.
- Definition of done: pilot success/failure events are atomic, attributable, and redacted.
- Rollback method: disable writer/read integration; retain recorded events.
- Dependencies: Phases `1A`, `3`, `4`.
- Decisions required before starting: audit retention minimum; recommended default is retain indefinitely until Phase `38`; non-blocking.
- Suggested commit message: `feat: add append-only audit foundation`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 6 — User read/list/statistics ownership controls

- Objective: prevent cross-owner disclosure.
- Exact scope: single-user reads, lists, counts, usage/statistics, expired lists, exports if present.
- Explicit exclusions: mutations and subscription-token redesign.
- Expected files: user/system routers, scoped repositories/services, tests.
- Database changes: none.
- API behavior: server-filtered results and non-leaking errors.
- Security checks: IDOR, pagination totals, filters, aggregates, and exports share scope.
- Tests required: Gate `G6`.
- Definition of done: no read/aggregate path leaks another owner's users.
- Rollback method: feature-flag new policy while preserving query code.
- Dependencies: Phases `3`–`5`.
- Decisions required before starting: none beyond Phase `4` defaults.
- Suggested commit message: `security: scope user reads lists and statistics`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 7 — User creation and update controls

- Objective: secure current free-form create/edit paths before template enforcement.
- Exact scope: permissions, ownership, limit/expiry/unlimited/protocol/inbound validation, audit.
- Explicit exclusions: template-only reseller creation and atomic quotas.
- Expected files: user router/service/models, Xray adapter, tests.
- Database changes: none.
- API behavior: stable legacy payload for authorized callers; machine-readable denial.
- Security checks: owner assignment server-side; no cross-owner edit; sensitive before/after redaction.
- Tests required: Gate `G7`.
- Definition of done: current create/update paths use one secured service.
- Rollback method: disable enforcement flag; retain audit.
- Dependencies: Phases `4`–`6`.
- Decisions required before starting: legacy `/api/user` deprecation window; recommended default is keep for owners through `0.8.6`; non-blocking.
- Suggested commit message: `security: control user creation and updates`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 8 — User status and subscription revocation controls

- Objective: secure status transitions and revocation independently.
- Exact scope: manual activate/deactivate/on-hold and subscription revocation with reason/audit.
- Explicit exclusions: billing suspension/restoration and bulk actions.
- Expected files: user service/router, subscription/Xray adapters, tests.
- Database changes: none.
- API behavior: current endpoints preserved with permission/state errors.
- Security checks: manual state remains distinct from future billing state; ownership enforced.
- Tests required: Gate `G8`.
- Definition of done: all single-user status/revoke transitions follow one state matrix.
- Rollback method: revert service routing; retain audit events.
- Dependencies: Phases `5`–`7`.
- Decisions required before starting: none.
- Suggested commit message: `security: control user status and subscription revocation`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 9 — Usage reset and billing checkpoint controls

- Objective: preserve history and make resets future-billing-safe.
- Exact scope: single/recurring reset checkpoint; stop deleting prior reset/node usage history.
- Explicit exclusions: bulk reset, pricing, and charging.
- Expected files: reset service/job, models/migration if checkpoint rows are separate, tests.
- Database changes: append-only reset checkpoint metadata as required.
- API behavior: reset requires permission/reason and keeps current visible counter semantics.
- Security checks: no refund, negative usage, duplicate billing, or state over-activation.
- Tests required: Gate `G9`.
- Definition of done: reset changes only classical counters and creates an immutable checkpoint.
- Rollback method: disable new reset path; retain checkpoints/history.
- Dependencies: Phases `5`, `8`.
- Decisions required before starting: checkpoint storage shape; recommended separate append-only record; non-blocking if accepted.
- Suggested commit message: `feat: preserve usage history across reset checkpoints`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 10 — Delete and soft-delete controls

- Objective: preserve user/admin historical references.
- Exact scope: user soft delete, subscription/Xray removal, default query exclusion, admin-delete preconditions, auto-delete adaptation.
- Explicit exclusions: physical purge and ownership transfer.
- Expected files: models/migration, delete service, jobs, subscription dependency, tests.
- Database changes: deletion actor/time/reason; remove destructive historical cascades.
- API behavior: delete becomes idempotent soft delete.
- Security checks: deleted users cannot subscribe or reappear; history survives.
- Tests required: Gate `G10`.
- Definition of done: supported delete paths never destroy protected history.
- Rollback method: disable visibility behavior; never purge new soft-deleted rows.
- Dependencies: Phases `5`, `6`, `9`.
- Decisions required before starting: username reuse policy; recommended default is no reuse in initial release; stop if rejected without alternative.
- Suggested commit message: `feat: soft delete users and preserve history`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 11 — Ownership-transfer controls

- Objective: transfer current ownership without changing creator/history.
- Exact scope: owner-only single-user transfer, row locks, destination validation, transfer event/audit.
- Explicit exclusions: bulk transfer and quota enforcement beyond current invariants.
- Expected files: transfer model/migration, service/router, tests.
- Database changes: `user_ownership_transfers`.
- API behavior: new reason-required transfer endpoint; legacy endpoint deprecated.
- Security checks: only owner permission; immutable creator; deterministic locks.
- Tests required: Gate `G11`.
- Definition of done: transfer is atomic and fully attributable.
- Rollback method: disable endpoint; correct only with a compensating transfer.
- Dependencies: Phases `2`, `5`, `7`.
- Decisions required before starting: destination behavior when near future quotas; recommended deny if known limits fail; non-blocking.
- Suggested commit message: `feat: add audited user ownership transfer`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 12 — Bulk-operation controls

- Objective: secure bulk status, reset, delete, and transfer independently.
- Exact scope: batch limit, deterministic selection/locking, parent/item audits, explicit partial-failure contract.
- Explicit exclusions: new bulk operation types and UI.
- Expected files: bulk service/router/schemas, tests.
- Database changes: none beyond prior records.
- API behavior: bounded result-per-item schema and required reason.
- Security checks: scope every item; reject filter tampering; no unbounded job.
- Tests required: Gate `G12`.
- Definition of done: supported bulk operations are bounded, atomic where specified, and auditable.
- Rollback method: disable bulk endpoints; single-item paths remain.
- Dependencies: Phases `8`–`11`.
- Decisions required before starting: atomic-all versus per-item semantics; recommended per-item with explicit outcomes except transfer batches; stop if unapproved.
- Suggested commit message: `security: enforce scoped bulk user operations`.
- Stable version checkpoint: contributes to `0.8.5`.
- Execution rule: Section 21.1.

### Phase 13 — CLI, Telegram, and background-job authorization parity

- Objective: eliminate non-REST bypasses.
- Exact scope: route protected CLI/Telegram/jobs through secured services and explicit actor contexts.
- Explicit exclusions: UI changes and new bot features.
- Expected files: `cli/`, Telegram handlers/filters, jobs, service adapters, tests.
- Database changes: none.
- API behavior: REST unchanged; CLI/bot errors become consistent.
- Security checks: no direct protected CRUD; system actor is least privilege; Telegram identity maps to admin.
- Tests required: Gate `G13`.
- Definition of done: inventory shows no unapproved bypass.
- Rollback method: disable affected command/handler rather than restore unsafe direct CRUD.
- Dependencies: Phases `1C`, `5`–`12`.
- Decisions required before starting: system actor and Telegram mapping from Phase `1D`; stop if unresolved.
- Suggested commit message: `security: align cli telegram and jobs with authorization`.
- Stable version checkpoint: `0.8.5` after Gates `G1A`–`G13` and checkpoint regression pass.
- Execution rule: Section 21.1.

### Phase 14 — Template versioning and assignment backend

- Objective: extend the existing template system safely.
- Exact scope: immutable versions, added policy fields, assignments, version-1 backfill, secured backend reads/writes.
- Explicit exclusions: user creation application and frontend UI.
- Expected files: models/migration, template service/router/schemas, tests.
- Database changes: template versions/assignments.
- API behavior: assigned reads; owner-only version/assignment APIs.
- Security checks: assignment isolation and immutable applied versions.
- Tests required: Gate `G14`.
- Definition of done: existing templates have validated version 1 and scoped assignment APIs.
- Rollback method: disable assignment enforcement; retain versions.
- Dependencies: Phases `4`, `5`, `13`.
- Decisions required before starting: default assignment for legacy templates; recommended owner-only until explicit assignment; stop if unapproved.
- Suggested commit message: `feat: version and assign user templates`.
- Stable version checkpoint: contributes to `0.8.6`.
- Execution rule: Section 21.1.

### Phase 15 — Server-side template user creation

- Objective: accept only `username` and `template_id` for normal resellers.
- Exact scope: strict payload, server application, generated settings, applied snapshot, separate custom-create permission.
- Explicit exclusions: quotas and frontend.
- Expected files: user/template services, schemas/router, snapshot model/migration, tests.
- Database changes: `user_creation_snapshots`.
- API behavior: add from-template/custom endpoints; legacy owner path remains temporarily.
- Security checks: `extra="forbid"`, assigned version only, no client-controlled template values.
- Tests required: Gate `G15`.
- Definition of done: reseller cannot alter template-controlled configuration.
- Rollback method: disable reseller template enforcement; retain snapshots.
- Dependencies: Phases `7`, `14`.
- Decisions required before starting: legacy endpoint window from Phase `7`; no new blocker.
- Suggested commit message: `feat: create reseller users from server templates`.
- Stable version checkpoint: contributes to `0.8.6`.
- Execution rule: Section 21.1.

### Phase 16 — Classical quota model and resolver

- Objective: define permissions-independent resource limits.
- Exact scope: all required quota fields, resolver, owner management/self read, zero/null semantics.
- Explicit exclusions: enforcement and concurrency.
- Expected files: model/migration, quota service/router/schemas, tests.
- Database changes: `admin_quota_profiles`.
- API behavior: quota management/read endpoints.
- Security checks: owner-only changes, reason/audit, bounds/overflow validation.
- Tests required: Gate `G16`.
- Definition of done: every quota resolves deterministically.
- Rollback method: keep enforcement off; retain profiles.
- Dependencies: Phases `4`, `5`.
- Decisions required before starting: quota defaults; recommended conservative explicit defaults for resellers; stop if unapproved.
- Suggested commit message: `feat: define classical reseller quotas`.
- Stable version checkpoint: contributes to `0.8.6`.
- Execution rule: Section 21.1.

### Phase 17 — Atomic quota enforcement

- Objective: prevent concurrent quota overruns.
- Exact scope: MySQL-authoritative transactional create/update/transfer/bulk validation, fixed locks, rate buckets/counters, deadlock retry, and reconciliation; establish 5,000- and 10,000-user generated-data quota/concurrent-create baselines.
- Explicit exclusions: financial balance enforcement.
- Expected files: quota/user services, repositories, database-specific tests.
- Database changes: only required lock/counter/rate rows.
- API behavior: `quota_exceeded` with safe details.
- Security checks: no count-then-insert race; owner scope inside transaction.
- Tests required: Gate `G17`.
- Definition of done: concurrent committed MySQL state never exceeds a quota and the 5,000/10,000-user reports satisfy Section 1.7 for applicable quota/user operations.
- Rollback method: disable enforcement; retain profiles/reconciliation.
- Dependencies: Phases `11`, `12`, `15`, `16`.
- Decisions required before starting: supported databases/topology from Phase `1D`; stop if absent.
- Suggested commit message: `feat: enforce reseller quotas atomically`.
- Stable version checkpoint: `0.8.6` after Gates `G14`–`G17`, backend API Gate `G29`, and checkpoint regression.
- Execution rule: Section 21.1.

### Phase 18 — Wallet account foundation

- Objective: add exact-value accounts without charging.
- Exact scope: unit, wallet row, cached balance, owner/self read, initialization.
- Explicit exclusions: ledger adjustments and traffic billing.
- Expected files: billing models/migration, wallet service/router, tests.
- Database changes: `wallet_accounts`.
- API behavior: read-only wallet summary.
- Security checks: integer/exact arithmetic and owner isolation.
- Tests required: Gate `G18`.
- Definition of done: one exact, lockable account exists per billable admin.
- Rollback method: disable endpoint; retain rows.
- Dependencies: Phases `4`, `5`.
- Decisions required before starting: credit unit/currency/scale and opening balance; stop until approved.
- Suggested commit message: `feat: add exact-value wallet accounts`.
- Stable version checkpoint: contributes to `0.8.7`.
- Execution rule: Section 21.1.

### Phase 19 — Append-only wallet ledger

- Objective: make every balance mutation traceable.
- Exact scope: entry types, idempotency, cached update, manual adjustment/refund/correction.
- Explicit exclusions: traffic-charge generation.
- Expected files: ledger model/migration, service/router, audit integration, tests.
- Database changes: `wallet_ledger_entries`.
- API behavior: scoped ledger reads and owner adjustment endpoint.
- Security checks: no update/delete, reason, signed bounds, references.
- Tests required: Gate `G19`.
- Definition of done: cached balance always equals ledger sum in tests.
- Rollback method: disable mutation API; compensate, never delete.
- Dependencies: Phases `5`, `18`.
- Decisions required before starting: adjustment/refund approval policy; recommended owner-only with reason; non-blocking if accepted.
- Suggested commit message: `feat: add append-only wallet ledger`.
- Stable version checkpoint: contributes to `0.8.7`.
- Execution rule: Section 21.1.

### Phase 20 — Raw usage-event capture

- Objective: persist raw billable traffic once.
- Exact scope: raw events, owner/user/node/period identity, ingestion key, operational-total compatibility, and staged MySQL usage-job/node-aggregation measurements at 5,000 and 10,000 users.
- Explicit exclusions: pricing and ledger charges.
- Expected files: usage model/migration, recording job/service, tests.
- Database changes: `usage_events`; non-cascading historical references.
- API behavior: internal/owner diagnostic only.
- Security checks: immutable events, no proxy/subscription secrets.
- Tests required: Gate `G20`.
- Definition of done: every collected delta is durable and uniquely identifiable, and usage/background-job reports capture duration, throughput, query latency, locks, pool behavior, and resources.
- Rollback method: disable new capture; retain events and current counters.
- Dependencies: Phases `2`, `10`, `13`.
- Decisions required before starting: raw-event boundary and multi-replica topology; stop if unapproved.
- Suggested commit message: `feat: capture immutable raw usage events`.
- Stable version checkpoint: contributes to `0.8.7`.
- Execution rule: Section 21.1.

### Phase 21 — Pricing and charge snapshots

- Objective: calculate repeatable expected charges.
- Exact scope: immutable pricing versions, exact coefficients, rounding, non-enforced charge records.
- Explicit exclusions: ledger debit worker and enforcement.
- Expected files: pricing/charge models/migrations, service/router, node coefficient compatibility, tests.
- Database changes: `pricing_versions`, `usage_charges`, exact coefficient storage for future snapshots.
- API behavior: owner pricing management and scoped previews.
- Security checks: no float finance; immutable versions; audit changes.
- Tests required: Gate `G21`.
- Definition of done: stored snapshots reproduce amounts exactly.
- Rollback method: disable calculator; retain previews.
- Dependencies: Phases `19`, `20`.
- Decisions required before starting: pricing formula, precision, aggregation boundary, rounding, legacy usage policy; stop until approved.
- Suggested commit message: `feat: snapshot pricing and usage charges`.
- Stable version checkpoint: contributes to `0.8.7`.
- Execution rule: Section 21.1.

### Phase 22 — Idempotent billing worker

- Objective: post exactly one charge effect per event.
- Exact scope: MySQL claim/lease, idempotency key, atomic event-charge-ledger transaction, deadlock retry/restart, and generated-data worker concurrency at 10,000 and 25,000 users.
- Explicit exclusions: shadow reporting policy and enforcement.
- Expected files: billing worker/repository/job, metrics, tests.
- Database changes: claim/status/idempotency constraints.
- API behavior: internal health only.
- Security checks: least-privilege system actor, fixed lock order, owner snapshot.
- Tests required: Gate `G22`.
- Definition of done: retries and concurrent workers create one effect and the 10,000/25,000-user billing-worker reports meet Section 1.7 with no unexplained financial discrepancy.
- Rollback method: stop worker; reconcile claims; retain history.
- Dependencies: Phases `19`–`21`.
- Decisions required before starting: worker topology/lease duration; recommended database claim with bounded lease; stop if topology unknown.
- Suggested commit message: `feat: process usage charges idempotently`.
- Stable version checkpoint: contributes to `0.8.7`.
- Execution rule: Section 21.1.

### Phase 23 — Billing shadow mode

- Objective: observe expected billing without impact.
- Exact scope: shadow mode, projections, variance metrics, hard no-enforcement guard.
- Explicit exclusions: spendable debit, blocking, suspension, restoration.
- Expected files: billing policy/worker/reporting, tests.
- Database changes: mode/run metadata.
- API behavior: owner shadow status/variance reads.
- Security checks: shadow cannot change balance or eligibility.
- Tests required: Gate `G23`.
- Definition of done: replayable shadow records have zero service impact.
- Rollback method: stop shadow processing; retain results.
- Dependencies: Phase `22`.
- Decisions required before starting: representative shadow duration; recommended at least one full billing period; can be finalized before Phase `24`.
- Suggested commit message: `feat: add non-enforcing billing shadow mode`.
- Stable version checkpoint: contributes to `0.8.7`.
- Execution rule: Section 21.1.

### Phase 24 — Billing reconciliation and period closure

- Objective: explain all usage, charges, and balances.
- Exact scope: periods, reconciliation runs, discrepancy types, late-event rules, controlled closure, and a 25,000-user generated-data MySQL reconciliation benchmark.
- Explicit exclusions: automatic corrections and enforcement.
- Expected files: reconciliation models/migration, service/job/router, runbook, tests.
- Database changes: billing periods/reconciliation records.
- API behavior: owner-only period/reconciliation endpoints.
- Security checks: read-only by default; audited closure.
- Tests required: Gate `G24`.
- Definition of done: representative shadow periods, including the 25,000-user stage, have zero unexplained variance and a complete Section 1.7 report.
- Rollback method: stop closure; audited reopen only; retain records.
- Dependencies: Phase `23`.
- Decisions required before starting: period length and late-event policy; stop until approved.
- Suggested commit message: `feat: reconcile billing periods`.
- Stable version checkpoint: `0.8.7` after Gates `G18`–`G24`, read-only UI Gates as approved, and checkpoint regression; enforcement off.
- Execution rule: Section 21.1.

### Phase 25 — Balance warnings

- Objective: notify without restricting service.
- Exact scope: thresholds, idempotent episodes, approved recipients.
- Explicit exclusions: blocking and suspension.
- Expected files: policy/job/notification adapters, tests.
- Database changes: warning delivery/episode rows if needed.
- API behavior: warning policy/state.
- Security checks: no cross-owner balance leakage or duplicate alerts.
- Tests required: Gate `G25`.
- Definition of done: one intended notice per threshold episode.
- Rollback method: disable notifications.
- Dependencies: Phase `24`.
- Decisions required before starting: warning thresholds/recipients; stop until approved.
- Suggested commit message: `feat: add idempotent balance warnings`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 26 — Balance-aware creation blocking

- Objective: add the first enforceable balance restriction.
- Exact scope: atomic create decision using balance, credit limit, and grace.
- Explicit exclusions: existing-user suspension.
- Expected files: billing policy, creation services/adapters, tests.
- Database changes: policy/enforcement episode fields.
- API behavior: `insufficient_balance`.
- Security checks: no legacy API/CLI/Telegram bypass.
- Tests required: Gate `G26`.
- Definition of done: all creation entry points agree at boundaries.
- Rollback method: disable block flag immediately.
- Dependencies: Phases `15`, `17`, `24`, `25`.
- Decisions required before starting: credit limit, grace, override policy, enforcement approval; stop until explicitly approved.
- Suggested commit message: `feat: block creation on exhausted balance`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 27 — Billing suspension

- Objective: suspend service without overwriting normal status.
- Exact scope: orthogonal suspension episode, worker, Xray removal, subscription behavior.
- Explicit exclusions: restoration and manual-status changes.
- Expected files: suspension model/migration, service/job/adapters, tests.
- Database changes: `billing_suspensions`.
- API behavior: additive eligibility/billing state.
- Security checks: only billing policy suspends; idempotent batches; preserve classical state.
- Tests required: Gate `G27`.
- Definition of done: eligible exhausted users suspend once.
- Rollback method: disable worker; retain episodes.
- Dependencies: Phase `26`.
- Decisions required before starting: suspension threshold/grace/batch policy and explicit enforcement approval; stop until approved.
- Suggested commit message: `feat: add separate billing suspension`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 28 — Safe billing restoration

- Objective: restore only billing-suspended, otherwise eligible users.
- Exact scope: recharge trigger, eligibility matrix, Xray retry/idempotency.
- Explicit exclusions: manual override of deleted/disabled/expired/limited states.
- Expected files: restoration service/job/adapters, tests.
- Database changes: restoration outcome metadata.
- API behavior: owner-visible restoration state/retry.
- Security checks: full state cross-product and concurrent state changes.
- Tests required: Gate `G28`.
- Definition of done: no classically/manual ineligible user reactivates.
- Rollback method: stop auto-restore; retain safe suspension.
- Dependencies: Phase `27`.
- Decisions required before starting: retry/operator escalation policy; recommended bounded retries then manual review; non-blocking if accepted.
- Suggested commit message: `feat: safely restore billing-suspended users`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 29 — Secured backend admin-management APIs

- Objective: expose tested backend administration before UI.
- Exact scope: admin CRUD/status, roles, overrides, scopes, template/quota assignments, wallet/billing/audit read links and pagination.
- Explicit exclusions: all frontend work and financial calculation logic already owned by prior phases.
- Expected files: admin/security/template/quota/billing/audit routers/schemas/services, API tests.
- Database changes: none beyond prior phases.
- API behavior: stable additive management contracts and capability discovery.
- Security checks: owner-only mutations, scoped reads, reasons/audit, last-owner protection.
- Tests required: Gate `G29`.
- Definition of done: backend workflows are secured and integration-tested without UI.
- Rollback method: disable new endpoints; core services remain.
- Dependencies: Phases `4`–`5`, `14`, `16`, and relevant billing phases for their endpoints.
- Decisions required before starting: pagination/default page size; recommended bounded cursor/offset compatibility; non-blocking.
- Suggested commit message: `feat: add secured admin management APIs`.
- Stable version checkpoint: required for `0.8.6` core API checkpoint; later billing endpoints remain additive.
- Execution rule: Section 21.1.

### Phase 30 — Admin UI capability shell

- Objective: create frontend routing/navigation that consumes backend capabilities.
- Exact scope: admin area shell, API client/types, guarded navigation, error/loading patterns.
- Explicit exclusions: feature forms and backend authorization.
- Expected files: dashboard router/layout/services/types/locales/tests.
- Database changes: none.
- API behavior: consumes Phase `29`; no new backend contract.
- Security checks: UI gating is usability only; token/secrets never rendered.
- Tests required: Gate `G30`.
- Definition of done: each role sees correct empty feature entry points and denied API remains denied.
- Rollback method: hide/remove new routes.
- Dependencies: Phase `29`.
- Decisions required before starting: none.
- Suggested commit message: `feat: add capability-aware admin ui shell`.
- Stable version checkpoint: contributes to `0.8.8`; may ship hidden earlier.
- Execution rule: Section 21.1.

### Phase 31 — Role and permission management UI

- Objective: manage admin role/overrides safely.
- Exact scope: list/detail/edit, explicit deny display, reason dialog, last-owner warning.
- Explicit exclusions: templates, quotas, billing, and audit views.
- Expected files: focused dashboard page/components/service/locales/tests.
- Database changes: none.
- API behavior: Phase `29` only.
- Security checks: server errors authoritative; no privilege inferred client-side.
- Tests required: Gate `G31`.
- Definition of done: owner workflows pass; other roles remain read/denied as designed.
- Rollback method: disable route.
- Dependencies: Phase `30`.
- Decisions required before starting: role defaults already approved in Phase `4`.
- Suggested commit message: `feat: add role and permission management ui`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 32 — Template assignment UI

- Objective: manage versioned template assignments.
- Exact scope: assigned lists, assignment/revocation, version display, reason handling.
- Explicit exclusions: user-create form redesign beyond assigned-template selection.
- Expected files: focused dashboard page/components/tests/locales.
- Database changes: none.
- API behavior: Phase `14`/`29`.
- Security checks: no client-submitted template configuration during assignment.
- Tests required: Gate `G32`.
- Definition of done: owner assigns; reseller sees only assignments.
- Rollback method: disable route.
- Dependencies: Phases `14`, `30`.
- Decisions required before starting: none beyond Phase `14`.
- Suggested commit message: `feat: add template assignment ui`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 33 — Quota management UI

- Objective: display/edit quota profiles and utilization.
- Exact scope: limit semantics, validation, reason dialog, usage indicators.
- Explicit exclusions: concurrency logic and wallet credit policy.
- Expected files: quota page/components/tests/locales.
- Database changes: none.
- API behavior: Phase `16`/`29`.
- Security checks: server recomputes; no client enforcement trust.
- Tests required: Gate `G33`.
- Definition of done: zero/null/unlimited states render and submit correctly.
- Rollback method: disable route.
- Dependencies: Phases `16`, `30`.
- Decisions required before starting: quota defaults approved in Phase `16`.
- Suggested commit message: `feat: add quota management ui`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 34 — Wallet and ledger views

- Objective: show balances and immutable entries safely.
- Exact scope: summaries, filters, entry details, authorized adjustment dialog.
- Explicit exclusions: billing/reconciliation charts.
- Expected files: wallet/ledger pages/components/tests/locales.
- Database changes: none.
- API behavior: Phases `18`, `19`, `29`.
- Security checks: exact formatting, scoped data, reason/idempotency, no client balance calculation.
- Tests required: Gate `G34`.
- Definition of done: displayed balance reconciles with paginated ledger fixture.
- Rollback method: disable routes/adjustment UI.
- Dependencies: Phases `19`, `30`.
- Decisions required before starting: approved credit unit/display precision from Phase `18`.
- Suggested commit message: `feat: add wallet and ledger views`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 35 — Billing and reconciliation views

- Objective: expose charge, shadow, period, discrepancy, and enforcement state.
- Exact scope: read/filter/detail, period close/reopen confirmation where authorized.
- Explicit exclusions: audit page and policy calculation.
- Expected files: billing pages/components/charts/tests/locales.
- Database changes: none.
- API behavior: Phases `21`–`29`.
- Security checks: owner scope, safe metadata, enforcement confirmation.
- Tests required: Gate `G35`.
- Definition of done: operators can explain a charge through stored snapshots.
- Rollback method: disable route.
- Dependencies: Phases `24`, `30`; enforcement panels wait for Phases `26`–`28`.
- Decisions required before starting: none beyond billing decisions already approved.
- Suggested commit message: `feat: add billing reconciliation views`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 36 — Audit-log views

- Objective: provide safe investigation workflows.
- Exact scope: scoped list/filter/detail, redacted diffs, request/source correlation.
- Explicit exclusions: audit mutation/export unless separately approved.
- Expected files: audit page/components/tests/locales.
- Database changes: none.
- API behavior: Phase `29`.
- Security checks: `audit.read`, safe rendering, no secret reconstruction.
- Tests required: Gate `G36`.
- Definition of done: authorized viewers trace actions without seeing secrets.
- Rollback method: disable route.
- Dependencies: Phases `5`, `29`, `30`.
- Decisions required before starting: audit reader roles; recommended owner only initially; non-blocking if accepted.
- Suggested commit message: `feat: add secure audit log views`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 37 — Operational metrics and reports

- Objective: make authorization/billing health observable.
- Exact scope: metrics, alerts, reconciliation summaries, worker/lock/queue health, MySQL latency/slow-query/lock-wait/deadlock/pool-exhaustion telemetry, and capacity-report collection.
- Explicit exclusions: retention, backup, tuning, release.
- Expected files: metrics/reporting modules, deployment config, runbook, tests.
- Database changes: measured indexes only if separately justified.
- API behavior: protected health/metrics/report endpoints.
- Security checks: no tenant labels/secrets in public metrics.
- Tests required: Gate `G37`.
- Definition of done: critical failure modes and every Section 1.7 capacity metric have actionable, access-controlled signals.
- Rollback method: disable exporters/alerts.
- Dependencies: Phases `13`, `24`, `28`.
- Decisions required before starting: monitoring destination/SLOs; recommended vendor-neutral metrics first; non-blocking.
- Suggested commit message: `ops: add authorization and billing observability`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 38 — Retention, backup, and recovery

- Objective: document and prove data protection.
- Exact scope: retention rules, non-cascading history, backup/restore rehearsal, disaster runbook.
- Explicit exclusions: performance tuning and release tagging.
- Expected files: operational docs/scripts/config and recovery tests.
- Database changes: archival metadata only if approved.
- API behavior: unchanged.
- Security checks: encrypted/restricted backups; audit/ledger/billing protected from purge.
- Tests required: Gate `G38`.
- Definition of done: production-like backup restores with verified invariants.
- Rollback method: retain prior backup process; do not enable untested purge.
- Dependencies: Phases `10`, `19`, `24`.
- Decisions required before starting: retention/purge/legal policy; stop before purge implementation, but backup rehearsal may proceed.
- Suggested commit message: `ops: define retention backup and recovery`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 39 — Performance, rate-limit, and security hardening

- Objective: validate and harden the complete system toward the 50,000-registered-user MySQL target.
- Exact scope: run generated non-production stages at 5,000, 10,000, 25,000, and 50,000 registered users across the complete Section 1.7 workload; collect acceptance reports; use MySQL query plans and before/after benchmarks for any query/index/pool/configuration change; test API rate limits, least privilege, scans, and multi-worker faults.
- Explicit exclusions: unrelated refactors/dependency upgrades and release creation.
- Expected files: targeted services/config/migrations only with evidence, security/load tests.
- Database changes: measured indexes/partitioning only when MySQL query plans and benchmark evidence justify them.
- API behavior: documented limits/retry responses.
- Security checks: dependency/container/secret scans and denial behavior.
- Tests required: Gate `G39`.
- Definition of done: all four staged reports are complete; the 50,000-user complete-system workload meets approved latency, throughput, job-duration, error, resource, locking, pool, integrity, ownership, billing, and reconciliation criteria without claiming 50,000 concurrent online users.
- Rollback method: revert individual tuning/limit flags; retain evidence.
- Dependencies: Phases `17`, `22`, `37`, `38`.
- Decisions required before starting: SLOs/rate limits; recommended production-derived conservative defaults; stop if no acceptance criteria.
- Suggested commit message: `perf: harden admin billing operations`.
- Stable version checkpoint: contributes to `0.8.8`.
- Execution rule: Section 21.1.

### Phase 40 — Release readiness and final documentation

- Objective: produce a releasable, reversible checkpoint.
- Exact scope: compatibility/migration/recovery/runbooks, final caller audit, reviewed Phase `39` capacity evidence, documented capacity limits, release candidate evidence, and version bump only after approval.
- Explicit exclusions: new features, branch/tag/push without explicit approval.
- Expected files: documentation, release configuration, approved version file only at final checkpoint.
- Database changes: none.
- API behavior: freeze and document.
- Security checks: all findings closed/accepted; enforcement kill switches verified.
- Tests required: Gate `G40` and Final Gate `GF`.
- Definition of done: owner signs off a tested usable release candidate and any capacity claim exactly matches the production-like MySQL evidence and documented workload.
- Rollback method: previous stable deployment, enforcement off, reconciliation, verified restore if necessary.
- Dependencies: all release-selected phases.
- Decisions required before starting: release scope/go-live/version approval; stop until approved.
- Suggested commit message: `release: prepare secure admin management checkpoint`.
- Stable version checkpoint: `0.8.8` when the full selected scope and Final Gate pass; earlier checkpoint releases follow Sections 19 and 21.
- Execution rule: Section 21.1.

## 22. Matching phase test gates

Every implementation phase must pass its matching gate before it can be reported complete. A gate runs the narrow tests named below plus the baseline regression set introduced in Phase `1B`. Commands are finalized when the referenced test paths are created.

### 22.1 Command groups

Backend/unit/security:

```bash
python -m pytest tests/unit tests/security -q
```

API and operations:

```bash
python -m pytest tests/api tests/operations -q
```

Migration compatibility:

```bash
alembic heads
alembic upgrade head
python -m pytest tests/migrations tests/compatibility -q
```

CLI, Telegram, and jobs:

```bash
python -m pytest tests/cli tests/telegram tests/jobs -q
```

Quota concurrency:

```bash
python -m pytest tests/quotas tests/concurrency/test_quotas.py -q
```

Billing:

```bash
python -m pytest tests/billing -q
```

Frontend:

```bash
cd app/dashboard
npm ci
npm run build
```

Full backend:

```bash
python -m pytest -q
```

### 22.2 Gate definitions

Each gate uses: **Setup** = phase fixtures plus baseline fixtures; **Expected** = named invariants pass with no unrelated regression; **Failure** = any named invariant, security boundary, data-integrity check, or baseline test fails; **Fix before continuing** = correct the phase root cause, add a regression test, and rerun the gate.

- `G1A` → Phase `1A`: redaction and failed-login reporting tests; backend/unit/security group.
- `G1B` → Phase `1B`: clean-environment local test and CI dry run; baseline smoke command configured by the phase.
- `G1C` → Phase `1C`: inventory completeness check against routes, CLI commands, Telegram handlers, and scheduled jobs.
- `G1D` → Phase `1D`: record `alembic heads`; MySQL production authority; limited SQLite role; production topology; candidate SQLAlchemy pool, isolation, timeout, slow-query, index, and deadlock-retry settings; sudo identity decision; and `0.8.4` authority. No configuration is optimized and no mutation is performed.
- `G2` → Phase `2`: MySQL-critical ownership upgrade, backfill, constraints, dual-write, transaction/locking, and rollback compatibility; SQLite runs only the compatibility subset; migration group.
- `G3` → Phase `3`: missing-context denial, explicit system context, concealed IDOR, and scoped pilot query; backend/unit/security group.
- `G4` → Phase `4`: four-role matrix, override precedence, suspension, stale token, and last-owner tests; backend/unit/security group.
- `G5` → Phase `5`: audit atomicity, redaction, reason, actor/source/request identity, append-only behavior, and 5,000-user generated audit-growth baseline; backend/unit/security group.
- `G6` → Phase `6`: single/list/count/statistics/export cross-owner IDOR, pagination totals, and 5,000/10,000-user MySQL list/search/filter/count/statistics stages; API/operations group.
- `G7` → Phase `7`: create/update permission, ownership, unlimited, protocol/inbound, expiry/limit, audit, and 5,000/10,000-user mutation plus Xray configuration-generation/reload stages; API/operations group.
- `G8` → Phase `8`: manual state and revoke transition matrix, Xray/subscription effects, ownership, and audit; API/operations group.
- `G9` → Phase `9`: reset checkpoint, no history loss/refund/duplicate/negative charge, recurring reset behavior, and 10,000-user reset/background-job duration stage; API/operations plus focused billing reset tests.
- `G10` → Phase `10`: soft-delete visibility, subscription denial, username policy, cascade/FK, auto-delete, admin preconditions, and 10,000-user disable/soft-delete stage.
- `G11` → Phase `11`: transfer authorization, immutable creator, locks, destination validation, history, and audit.
- `G12` → Phase `12`: batch bound, selection scope, deterministic locks, partial-failure contract, item/parent audit.
- `G13` → Phase `13`: REST/CLI/Telegram/job decision parity and no-direct-CRUD inventory; CLI/Telegram/jobs group plus API regression.
- `G14` → Phase `14`: version immutability, assignment isolation, legacy version-1 migration, protocol/inbound validation.
- `G15` → Phase `15`: strict payload, tampering, unassigned version, prefix/suffix, snapshot, and custom-create permission.
- `G16` → Phase `16`: every quota resolver boundary, zero/null semantics, overflow, permission, and audit.
- `G17` → Phase `17`: MySQL-authoritative concurrent create/update/transfer/bulk, rate bucket, lock order, deadlock retry, pool behavior, and 5,000/10,000-user staged reports; SQLite compatibility subset; quota concurrency group.
- `G18` → Phase `18`: exact units, bounds, one-wallet uniqueness, locking, opening balance, and owner isolation.
- `G19` → Phase `19`: ledger immutability, cached sum, idempotency, concurrent adjustments, refund/correction references, and a 10,000-user generated ledger-growth/latency baseline.
- `G20` → Phase `20`: raw-versus-operational totals, duplicate ingestion, missing references, Xray reset/persist fault boundaries, node aggregation, job duration, and MySQL 5,000/10,000-user staged reports.
- `G21` → Phase `21`: exact coefficient/pricing snapshot, rounding, unlimited user, ownership boundary, historical immutability, and 10,000-user charge-calculation throughput baseline.
- `G22` → Phase `22`: MySQL duplicate delivery, concurrent workers, crash boundaries, stale lease, deadlock retry, pool pressure, exactly-one ledger effect, and 10,000/25,000-user staged reports.
- `G23` → Phase `23`: shadow replay and hard assertions that balance, creation, and eligibility never change.
- `G24` → Phase `24`: MySQL missing/duplicate/late events, cached mismatch, period closure/reopen, 25,000-user reconciliation report, and zero unexplained variance.
- `G25` → Phase `25`: threshold boundaries, recipient scope, repeated-worker idempotency, and episode reset.
- `G26` → Phase `26`: balance/credit/grace boundary, concurrent charge/create, legacy API, CLI, Telegram, and no existing-user impact.
- `G27` → Phase `27`: classical/manual state cross-product, idempotent batch, partial Xray failure, and subscription behavior.
- `G28` → Phase `28`: full restoration state cross-product, concurrent recharge/disable/delete/transfer, retry/idempotency.
- `G29` → Phase `29`: backend admin API authorization, validation, pagination, reasons/audit, last-owner, and cross-owner IDOR.
- `G30` → Phase `30`: frontend build, capability navigation, denied API handling, token/secret rendering checks; frontend group.
- `G31` → Phase `31`: role/override UI integration, explicit deny, reason, last-owner, and non-owner denial; frontend group.
- `G32` → Phase `32`: template assignment/version UI integration and reseller isolation; frontend group.
- `G33` → Phase `33`: quota zero/null/unlimited rendering, validation, error, and permission integration; frontend group.
- `G34` → Phase `34`: exact wallet display, paginated ledger sum fixture, adjustment reason/idempotency, scope; frontend plus focused billing.
- `G35` → Phase `35`: charge traceability, shadow/period/discrepancy views, close confirmation, enforcement-state integration.
- `G36` → Phase `36`: audit scope/filter/detail, redacted diff rendering, request correlation, and secret reconstruction attempts.
- `G37` → Phase `37`: metric accuracy/cardinality, alert firing/recovery, access control, no sensitive labels, and coverage of every MySQL/capacity report metric in Section 1.7.
- `G38` → Phase `38`: backup creation, clean restore, row counts/checksums, ledger/audit/billing invariants, and no protected purge.
- `G39` → Phase `39`: complete MySQL stages at 5,000, 10,000, 25,000, and 50,000 registered users; all Section 1.7 operations and report fields; query plans and before/after evidence for every optimization; SLO/rate-limit, multi-worker fault, scan, and correctness regression checks.
- `G40` → Phase `40`: release-document completeness, reviewed capacity reports and honest capacity statement, compatibility matrix, kill switches, exact candidate provenance, and selected checkpoint suite.

For `G1A` through `G40`, the expected result is all named checks passing. Any failure blocks that phase and every dependent phase.

### Final Gate GF — Full production-readiness validation

- What is tested: full backend regression; ownership/IDOR; permission resolution; REST/CLI/Telegram/job parity; MySQL-authoritative migrations/transactions/locking/pooling; SQLite compatibility; quota concurrency; ledger integrity; billing idempotency/reconciliation; suspension/restoration; frontend build/integration; backup/restore; upgrade/rollback; the complete Section 1.7 capacity workload; and final readiness.
- Required setup: exact release candidate, generated 50,000-registered-user MySQL dataset, separately recorded active/online/usage-job populations, production-like nodes/workload/topology/hardware/MySQL/pool configuration, multiple workers, representative Xray nodes, verified backup destination, and previous stable deployment.
- Commands to run: all command groups in Section 22.1 plus documented backup/restore and deployment smoke procedures.
- Expected result: all suites pass; one Alembic head; all Section 1.7 report fields and approved acceptance criteria pass at 50,000 registered users; zero unexplained billing variance; verified restore/rollback; no critical/high unresolved security issue; working enforcement kill switches; and no unsupported concurrent-online-user claim.
- Failure conditions: any missing capacity field/workload, row-insertion-only evidence, unapproved/unmeasured optimization, failed invariant, data loss, cross-owner access, duplicate/missing financial effect, unsafe restoration, unacceptable latency/job/resource/lock/pool/error result, failed build/restore/rollback, or missing runbook/alert.
- What must be fixed before continuing: release is blocked; correct the root cause, rebuild the candidate, and rerun Final Gate `GF` in full.

## 23. Final release and final test procedure

1. Freeze the selected checkpoint scope and exact commit.
2. Confirm every included implementation phase passed its matching gate.
3. Run Final Gate `GF` on the release candidate.
4. Review the complete 5,000/10,000/25,000/50,000 MySQL reports and verify every Section 1.7 workload, metric, environment field, query-plan justification, bottleneck, and limitation is documented.
5. Confirm one Alembic head and capture MySQL migration duration, counts, checksums, orphan checks, lock behavior, and rollback evidence.
6. Verify secret/dependency/container scans, audit redaction, and least privilege.
7. For billing enforcement, require a reconciled full shadow period and explicit owner go/no-go.
8. Verify backup restoration before production migration.
9. Deploy schema expansion and application with enforcement flags off.
10. Run REST, CLI, Telegram, job, UI, worker, MySQL pool, and slow-query smoke checks.
11. Enable approved policies progressively and reconcile after each step.
12. On unexplained variance, disable enforcement, preserve history, and investigate.
13. Publish only capacity statements supported by the complete-system benchmark; distinguish registered, active, concurrently online, and per-usage-job populations.
14. Change to the approved patch version and create a tag/release only after explicit approval.

## 24. Decision timing and approval gates

Early security work must not wait for billing or release decisions.

1. **Minimal test harness mechanism**
   - First dependent phase: `1B`.
   - Recommended default: `pytest` with isolated SQLite smoke fixtures and a non-publishing CI job.
   - Must stop for approval: only if adding the minimal test-only dependency/configuration is not pre-approved.
2. **Production topology and database execution profile**
   - First dependent phase: `1D`; schema implementation first depends at Phase `2`.
   - Recommended default: MySQL is already authoritative for production; SQLite is limited to development/lightweight/fast compatibility use; assume multiple application/worker replicas for locking safety until deployment topology is confirmed.
   - Must stop for approval: database authority is not open; Phase `1D` may inspect settings, but Phase `2` stops if the production replica/worker topology and connection profile remain unknown.
3. **Environment `SUDOERS` identity**
   - First dependent phase: `1D`; implementation first depends at Phase `2`/`5`.
   - Recommended default: materialize/map each environment sudo to a stable database owner actor.
   - Must stop for approval: Phase `1D` records options; Phase `2` stops if unresolved.
4. **Legacy null `admin_id` ownership**
   - First dependent phase: `2`.
   - Recommended default: assign to a designated owner-controlled holding account with a migration report.
   - Must stop for approval: yes, before Phase `2`.
5. **Legacy immutable creator backfill**
   - First dependent phase: `2`.
   - Recommended default: copy validated current owner and mark provenance as inferred.
   - Must stop for approval: yes, before Phase `2`.
6. **Support/viewer permission defaults and scopes**
   - First dependent phase: `4`.
   - Recommended default: viewer read-only; support scoped read/update/status/reset/revoke, with no create/delete/export/billing/admin policy.
   - Must stop for approval: yes, before Phase `4`; does not block Phases `1A`–`3`.
7. **Out-of-scope object response**
   - First dependent phase: `3`.
   - Recommended default: concealed `404` for object lookup, `403` for known authorized-scope operation denial.
   - Must stop for approval: no unless the owner rejects the default.
8. **Legacy user-create endpoint**
   - First dependent phase: `7`; enforcement first depends at Phase `15`.
   - Recommended default: keep for owners with `user.create_custom` through `0.8.6`; require template creation for resellers.
   - Must stop for approval: no for Phase `7`; yes before Phase `15` enforcement if changed.
9. **Username reuse after soft deletion**
   - First dependent phase: `10`.
   - Recommended default: no reuse in the initial release.
   - Must stop for approval: yes, before Phase `10` if the default is not accepted.
10. **Bulk transaction semantics**
    - First dependent phase: `12`.
    - Recommended default: bounded per-item results for status/reset/delete; atomic-all for ownership-transfer batches.
    - Must stop for approval: yes, before Phase `12`.
11. **Legacy template assignments**
    - First dependent phase: `14`.
    - Recommended default: existing templates owner-only until explicitly assigned.
    - Must stop for approval: yes, before Phase `14`.
12. **Classical quota defaults**
    - First dependent phase: `16`.
    - Recommended default: conservative explicit reseller limits; owner is not implicitly quota-limited.
    - Must stop for approval: yes, before Phase `16`.
13. **Credit unit, currency, scale, and opening balances**
    - First dependent phase: `18`.
    - Recommended default: integer smallest credit units, zero opening balance or explicit audited opening entries; never infer debt from `admins.users_usage`.
    - Must stop for approval: yes, before Phase `18`.
14. **Pricing, coefficient precision, aggregation, rounding, and legacy usage**
    - First dependent phase: `21`.
    - Recommended default: exact decimal snapshots, charge by raw bytes at a documented period boundary, deterministic round-half-up, legacy data marked unpriced unless reconstructable.
    - Must stop for approval: yes, before Phase `21`.
15. **Billing periods and late events**
    - First dependent phase: `24`.
    - Recommended default: calendar-month periods with an explicit late-event reconciliation window; validate against business needs.
    - Must stop for approval: yes, before Phase `24`.
16. **Warning thresholds and recipients**
    - First dependent phase: `25`.
    - Recommended default: configurable percentage/absolute thresholds sent only to the reseller and authorized owners.
    - Must stop for approval: yes, before Phase `25`.
17. **Credit limit, grace, creation block, suspension, and rollout**
    - First dependent phase: `26`; suspension first depends at Phase `27`.
    - Recommended default: shadow first, then warnings, then creation block, then separately approved suspension; zero implicit credit and progressive rollout.
    - Must stop for approval: yes, before Phase `26`, and a separate explicit go/no-go before Phase `27`.
18. **Retention and physical purge**
    - First dependent phase: `38`.
    - Recommended default: never cascade/purge ledger, billing, audit, or historical usage; defer other purge until legal/operational retention is approved.
    - Must stop for approval: backup work may proceed; purge implementation stops.
19. **Canonical version scheme**
    - First dependent phase: `40`.
    - Recommended default: `0.8.4` remains authoritative; use `0.8.5`–`0.8.8` checkpoints.
    - Must stop for approval: no early phase is blocked; only a different release/version action requires explicit approval.
20. **Release scope and go-live**
    - First dependent phase: `40`.
    - Recommended default: release only complete, usable checkpoints from Section 19.
    - Must stop for approval: yes, before version bump, tag, release, or production enforcement.

## 25. Recommended starting point

The exact first implementation phase is **Phase 1A — Remove password/secret exposure and add centralized redaction**. It has no database, billing, role, quota, versioning, or release decision dependency. Do not begin it without the exact instruction `Start Phase 1A`.

## Appendix A — Superseded implementation plan (non-executable)

The content below is retained only for refinement traceability. It must not be executed; Section 21 is authoritative.

All phases require review approval before the next phase. `Expected files` are estimates based on current architecture, not authorization to modify them.

### Phase 1 — Repository and security baseline

- Objective: create safety rails and resolve architectural decisions before schema work.
- Exact scope: add test harness/CI design, request IDs, safe secret-redaction policy, remove password reporting, inventory entry points, confirm migration head/database support, decide identity and version policy.
- Expected files: `app/utils/report.py`, `app/routers/admin.py`, new `app/security/`, test configuration, `.github/workflows/`, documentation.
- Database changes: none.
- API changes: no contract change; request ID response header may be additive.
- Security checks: verify no password/token/URL/credential appears in logs or notifications; create caller matrix for REST, CLI, Telegram, jobs, subscriptions, dashboard.
- Tests required: secret-redaction unit tests, login notification tests, baseline API smoke tests.
- Definition of done: critical password exposure is closed, CI runs, migration head is confirmed, unresolved design decisions are approved.
- Rollback method: revert additive middleware/tests and reporting change; no data rollback.
- Dependencies: none.
- Suggested commit: `security: establish admin management baseline and secret redaction`.
- Suggested patch version: none; include in `0.8.5` checkpoint.

### Phase 2 — Ownership schema foundation

- Objective: represent immutable creator and mutable owner without breaking `admin_id`.
- Exact scope: add ownership columns, transfer table, environment-owner mapping, backfill/validation scripts, dual-read/write compatibility.
- Expected files: `app/db/models.py`, `app/db/migrations/versions/`, `app/models/user.py`, `app/db/crud.py`, migration tests.
- Database changes: nullable `created_by_admin_id`, `owner_admin_id`, indexes/FKs, append-only transfer table; staged backfill.
- API changes: additive creator/owner fields only for owner-authorized responses; current fields remain.
- Security checks: creator is immutable; no cascade from admin deletion; null/unowned rows handled explicitly.
- Tests required: SQLite/MySQL upgrade/downgrade, legacy null-owner backfill, dual-write consistency, FK deletion behavior.
- Definition of done: all existing users have validated owner mapping and new users write creator/owner/admin consistently.
- Rollback method: disable dual-write and revert code; retain additive columns until safely empty or forward-fix.
- Dependencies: Phase 1.
- Suggested commit: `feat: add compatible user ownership foundation`.
- Suggested patch version: none; `0.8.5` candidate.

### Phase 3 — Central authorization service

- Objective: make permission, ownership, and source context mandatory outside raw repositories.
- Exact scope: add `AccessContext`, scoped user repository/query builder, policy decision interface, system-job context, and entry-point adapters.
- Expected files: new `app/security/context.py`, `app/security/policy.py`, `app/services/`, `app/repositories/`; updates to dependencies and selected CRUD callers.
- Database changes: none.
- API changes: consistent `403`/concealed `404` and machine-readable error codes.
- Security checks: deny by default; no public service accepts an unscoped protected query; system bypass is explicit and auditable.
- Tests required: ownership isolation, IDOR, missing-context denial, system-job-context tests.
- Definition of done: central service protects a pilot read/list path and architecture guard tests prevent unscoped access.
- Rollback method: feature-flag pilot enforcement while retaining context plumbing.
- Dependencies: Phase 2.
- Suggested commit: `feat: centralize access context and ownership policy`.
- Suggested patch version: none.

### Phase 4 — Roles and permission resolution

- Objective: implement the four roles and named override rules.
- Exact scope: admin role/status, permission catalog, role defaults, allow/deny overrides, capability endpoint, compatibility mapping.
- Expected files: `app/db/models.py`, migration, `app/models/admin.py`, `app/security/permissions.py`, `app/routers/admin.py`.
- Database changes: role/status columns and `admin_permission_overrides`.
- API changes: additive `/api/me/capabilities`; admin schemas expose safe role/status data.
- Security checks: explicit deny wins, unknown permission denies, suspended/deleted admin denies, only owner changes policy.
- Tests required: permission-resolution matrix, override precedence, stale-token/status, owner lockout prevention.
- Definition of done: every role has reviewed defaults and deterministic deny-by-default resolution.
- Rollback method: compatibility mode maps sudo/non-sudo to legacy behavior; retain data.
- Dependencies: Phases 1–3.
- Suggested commit: `feat: add role defaults and permission overrides`.
- Suggested patch version: none.

### Phase 5 — Audit-log foundation

- Objective: record durable, redacted, append-only security events.
- Exact scope: audit model/repository, source adapters, reason validation, redaction, post-commit notification reference.
- Expected files: model/migration, new `app/audit/`, middleware, CLI/Telegram adapters.
- Database changes: `audit_events` with indexes by actor/action/target/time.
- API changes: owner/scoped read endpoint; sensitive mutations begin requiring reason only when their audit integration lands.
- Security checks: insert-only code path, field allowlist, secret tests, actor/request/source integrity.
- Tests required: audit atomicity, redaction, required reason, immutable repository behavior, source-context tests.
- Definition of done: representative sensitive action and failed authorization both produce safe events as designed.
- Rollback method: disable audit read endpoint; retain events; never delete recorded history.
- Dependencies: Phases 1, 3, 4.
- Suggested commit: `feat: add append-only security audit events`.
- Suggested patch version: none.

### Phase 6 — Sensitive user-operation controls

- Objective: apply central permission, ownership, reason, and audit controls to all user operations.
- Exact scope: create/edit/delete/status/reset/revoke/transfer/bulk/limit/expiry/unlimited/next-plan paths across REST, CLI, Telegram, and jobs.
- Expected files: `app/routers/user.py`, `app/services/users.py`, dependencies, CLI and Telegram handlers, jobs, report adapters.
- Database changes: transfer records from Phase 2; optional reason fields in operation records.
- API changes: reason/error codes, safe bulk result schema, transfer endpoint; legacy owner endpoint deprecated.
- Security checks: permission plus scope plus object-state validation; deterministic bulk locking; audit before/after; no frontend authorization reliance.
- Tests required: operation permission matrix, ownership bypass/IDOR, bulk partial-failure rules, CLI/Telegram parity.
- Definition of done: every listed sensitive operation uses the service layer and has negative tests for every entry point.
- Rollback method: disable new mutation endpoints and restore legacy-compatible service policy; retain audit/transfer history.
- Dependencies: Phases 2–5.
- Suggested commit: `security: enforce scoped user operation policies`.
- Suggested patch version: `0.8.5` checkpoint after Testing Phases T1–T4 and T10 baseline.

### Phase 7 — Soft deletion and history preservation

- Objective: stop user/admin deletion from erasing operational or future financial history.
- Exact scope: soft-delete fields, default scopes, Xray removal, username reuse policy, auto-delete conversion, admin deletion preconditions.
- Expected files: models/migration, user/admin services, jobs, subscription dependency, CLI/Telegram.
- Database changes: deletion metadata; remove/replace destructive cascades affecting history.
- API changes: deletes become idempotent soft deletes; optional owner-only deleted-resource views.
- Security checks: deleted users cannot authenticate/subscribe/return in normal queries; audit and history remain.
- Tests required: soft deletion, subscription invalidation, username collision, cascade/FK, auto-delete, admin-with-users tests.
- Definition of done: no supported delete path physically removes protected history.
- Rollback method: disable soft-delete UI/API visibility changes; do not physically purge soft-deleted rows.
- Dependencies: Phases 5–6.
- Suggested commit: `feat: preserve user and admin history with soft deletion`.
- Suggested patch version: none.

### Phase 8 — Template versioning and assignment

- Objective: extend current templates with immutable versions and admin assignments.
- Exact scope: template version schema, assignment service, added policy fields, migration of existing templates to version 1.
- Expected files: `app/db/models.py`, migration, `app/models/user_template.py`, router/service/repository.
- Database changes: `user_template_versions`, `admin_template_assignments`, template status/version metadata.
- API changes: assigned-template list/read; owner version/assignment management.
- Security checks: resellers see only assigned templates; immutable versions; owner-only assignment.
- Tests required: assignment isolation, version immutability, protocol/inbound validation, migration tests.
- Definition of done: every active template has version 1 and access is assignment-scoped.
- Rollback method: disable assignment enforcement while retaining versions; legacy template reads remain.
- Dependencies: Phases 3–5.
- Suggested commit: `feat: version and assign existing user templates`.
- Suggested patch version: none; `0.8.6` candidate.

### Phase 9 — Server-side template creation

- Objective: make normal reseller creation accept only username and assigned template.
- Exact scope: strict request model, server loading/application, generated proxies/inbounds, applied snapshot, separate custom creation permission.
- Expected files: user/template services and models, router, Xray operation adapter, dashboard types later.
- Database changes: `user_creation_snapshots`.
- API changes: add `/api/users/from-template` and `/api/users/custom`; deprecate unrestricted reseller use of `/api/user`.
- Security checks: `extra="forbid"`, assignment check, never trust submitted values, audit applied version.
- Tests required: template bypass/tampering, unassigned template, prefix/suffix, protocol/inbound, snapshot, custom permission.
- Definition of done: reseller payload cannot influence template-controlled fields.
- Rollback method: turn off reseller template enforcement; keep owner custom path and snapshots.
- Dependencies: Phases 4, 6, 8.
- Suggested commit: `feat: create reseller users from server-side templates`.
- Suggested patch version: none.

### Phase 10 — Basic quota model

- Objective: define and resolve classical quota limits separately from permissions.
- Exact scope: quota schema/API, normalization, effective limit resolver, read-only quota usage reporting.
- Expected files: model/migration, new `app/quotas/`, admin models/router.
- Database changes: `admin_quota_profiles` and optional usage-counter rows.
- API changes: owner quota management and self quota/usage read endpoints.
- Security checks: owner-only changes with reason/audit; deny malformed/overflow values; exact semantics for zero/null.
- Tests required: resolver matrix for all required quotas, boundary/overflow, audit and permission tests.
- Definition of done: each required classical quota has documented storage and deterministic effective value.
- Rollback method: leave quota enforcement flag off; retain configured profiles.
- Dependencies: Phases 4–5.
- Suggested commit: `feat: define reseller quota profiles`.
- Suggested patch version: none.

### Phase 11 — Atomic quota enforcement

- Objective: prevent concurrent requests from exceeding quotas.
- Exact scope: transactional creation/update/transfer/bulk enforcement, row-lock order, creation rate limiter, reconciliation of counters.
- Expected files: quota service, user service, repositories, database-specific tests.
- Database changes: lock/version/counter or rate-bucket rows if required.
- API changes: `quota_exceeded` details and retry behavior.
- Security checks: validation and mutation share one transaction; no count-then-insert race; owner scope maintained.
- Tests required: simultaneous creates/activations/transfers, unlimited and allocated limits, deadlock retry, SQLite/MySQL behavior.
- Definition of done: concurrency tests prove final committed state never exceeds any quota.
- Rollback method: disable quota enforcement atomically; preserve profiles and reconciliation data.
- Dependencies: Phases 6, 9, 10.
- Suggested commit: `feat: enforce reseller quotas atomically`.
- Suggested patch version: `0.8.6` checkpoint after Testing Phases T1–T6.

### Phase 12 — Wallet account foundation

- Objective: introduce exact-value accounts without charging traffic.
- Exact scope: credit-unit decision, wallet rows, owner/self reads, lock/version handling, opening balance policy.
- Expected files: models/migration, new `app/billing/wallet.py`, API schemas/router.
- Database changes: `wallet_accounts` with integer/NUMERIC cached balance and uniqueness.
- API changes: wallet summary endpoints; no mutation except controlled initialization.
- Security checks: exact arithmetic, owner isolation, no client-calculated balance.
- Tests required: precision, bounds, concurrent wallet creation/read, authorization.
- Definition of done: every billable reseller has one reconciliable account with documented units.
- Rollback method: disable wallet endpoints; no traffic enforcement exists.
- Dependencies: Phases 4–5 and approved financial units.
- Suggested commit: `feat: add exact-value reseller wallet accounts`.
- Suggested patch version: none; `0.8.7` candidate.

### Phase 13 — Append-only ledger and adjustments

- Objective: make all balance changes traceable and immutable.
- Exact scope: ledger entry types, idempotency, cached-balance transaction, manual adjustment/refund/correction services.
- Expected files: model/migration, billing service/router, audit integration.
- Database changes: `wallet_ledger_entries`, unique idempotency/reference indexes.
- API changes: owner adjustment endpoint and scoped ledger reads.
- Security checks: permission, required reason, signed bounds, explicit original-entry references, no update/delete methods.
- Tests required: ledger integrity, duplicate key, concurrent adjustments, refund limits, cached/sum reconciliation, redaction.
- Definition of done: every test balance change equals the immutable ledger sum.
- Rollback method: disable adjustment endpoints; compensate approved mistakes with new entries only.
- Dependencies: Phases 5, 12.
- Suggested commit: `feat: add append-only wallet ledger`.
- Suggested patch version: none.

### Phase 14 — Raw usage event capture

- Objective: preserve billable raw traffic independently of classical counters.
- Exact scope: split raw collection from adjusted display totals, durable event key/period, owner/user/node snapshots, ingestion failure handling.
- Expected files: model/migration, `app/jobs/record_usages.py`, new usage ingestion service.
- Database changes: `usage_events`; change historical FK cascades; exact node coefficient field for future snapshots.
- API changes: owner-only diagnostic usage-event views, normally internal.
- Security checks: events are immutable, scoped, and contain no proxy/subscription secrets.
- Tests required: raw-vs-adjusted, main node, missing user/node, Xray reset/persist fault injection, duplicate ingestion.
- Definition of done: each collected delta is durably represented once with raw bytes and period identity.
- Rollback method: disable new ingestion path and keep current counters; retain captured events.
- Dependencies: Phases 2, 5, 7.
- Suggested commit: `feat: capture immutable raw usage events`.
- Suggested patch version: none.

### Phase 15 — Usage charge records and pricing snapshots

- Objective: deterministically calculate expected charges with historical inputs.
- Exact scope: immutable pricing versions, exact coefficient snapshots, charge calculation/rounding, charge record without enforcement.
- Expected files: models/migrations, billing pricing/charge modules, node service.
- Database changes: `pricing_versions`, `usage_charges` and exact future coefficient representation.
- API changes: owner pricing management and scoped charge preview/read.
- Security checks: owner-only pricing change with reason/audit; immutable effective versions; no float calculation.
- Tests required: coefficient/pricing snapshots, rounding, unlimited users, ownership transfer boundary, legacy usage policy.
- Definition of done: repeated calculation from stored snapshots gives the stored amount exactly.
- Rollback method: disable calculator; retain immutable records as non-enforced previews.
- Dependencies: Phases 13–14 and approved pricing policy.
- Suggested commit: `feat: snapshot pricing and usage charge inputs`.
- Suggested patch version: none.

### Phase 16 — Idempotent billing worker

- Objective: convert chargeable events to one charge and one ledger entry safely.
- Exact scope: claim/lease protocol, deterministic idempotency, atomic charge-ledger-event transaction, retry/restart handling.
- Expected files: billing worker/job, repositories, scheduler registration, observability.
- Database changes: claim/status fields and unique idempotency constraints.
- API changes: internal health/metrics only.
- Security checks: least-privilege system actor; no cross-owner posting; fixed lock order.
- Tests required: duplicate delivery, concurrent workers, crash at each boundary, stale lease, deadlock retry, ledger invariant.
- Definition of done: arbitrary retries/workers never create more than one financial effect per event.
- Rollback method: stop worker feature flag; reconcile in-flight claims; never delete entries.
- Dependencies: Phases 13–15.
- Suggested commit: `feat: process usage charges idempotently`.
- Suggested patch version: none.

### Phase 17 — Billing shadow mode

- Objective: run production-like calculation without financial or service enforcement.
- Exact scope: shadow configuration, expected ledger projection or separate shadow entries, dashboards/metrics, no blocking/suspension.
- Expected files: billing policy/config, worker, reports and operational endpoints.
- Database changes: mode fields/configuration and shadow run metadata.
- API changes: owner shadow status and variance reports.
- Security checks: hard guard prevents shadow mode from changing spendable balance or user eligibility.
- Tests required: shadow no-effect assertions, mode transitions, configuration authorization, replay.
- Definition of done: shadow charges are queryable/reconciliable and cannot affect service.
- Rollback method: disable shadow worker; preserve results for analysis.
- Dependencies: Phase 16.
- Suggested commit: `feat: run prepaid billing in non-enforcing shadow mode`.
- Suggested patch version: none.

### Phase 18 — Billing reconciliation and period closure

- Objective: prove usage, charges, and ledger totals agree before enforcement.
- Exact scope: reconciliation runs, discrepancy taxonomy, billing periods, late-event handling, operator runbook.
- Expected files: models/migration, billing reconciliation service/job/router, docs.
- Database changes: `billing_periods`, `billing_reconciliation_runs` and discrepancy details.
- API changes: owner-only reconciliation/period endpoints.
- Security checks: reconciliation is read-only unless an explicit correction workflow is approved; period closure permission and audit.
- Tests required: missing/duplicate/late event, coefficient mismatch, cached balance mismatch, closed-period rules.
- Definition of done: representative shadow cycle closes with zero unexplained discrepancy.
- Rollback method: reopen only through audited owner workflow; stop closure job and continue shadow capture.
- Dependencies: Phase 17.
- Suggested commit: `feat: reconcile billing events and close periods`.
- Suggested patch version: `0.8.7` checkpoint after Testing Phases T1–T8; enforcement remains off.

### Phase 19 — Balance warnings

- Objective: notify safely without changing service.
- Exact scope: threshold policy, grace/credit projections, idempotent warning episodes, owner/reseller notifications.
- Expected files: billing policy/job, notification adapters, UI indicators later.
- Database changes: warning episode/delivery records if needed.
- API changes: warning policy and current threshold state.
- Security checks: no secret/balance leakage to unrelated recipients; owner-only policy changes.
- Tests required: exact thresholds, repeated worker idempotency, recharge reset, negative credit-limit cases.
- Definition of done: each threshold emits at most one intended notification per episode.
- Rollback method: disable notifications; no eligibility state changes.
- Dependencies: Phases 17–18.
- Suggested commit: `feat: add idempotent wallet balance warnings`.
- Suggested patch version: none; `0.8.8` candidate.

### Phase 20 — Creation blocking

- Objective: enforce the first low-risk balance restriction independently.
- Exact scope: balance/credit/grace policy in create service, shadow comparison, clear errors, owner override rules if approved.
- Expected files: billing policy, user creation service, API models.
- Database changes: policy fields and enforcement episode records.
- API changes: `insufficient_balance` on creation; capability reports blocked state.
- Security checks: atomic balance snapshot with quota/create transaction; cannot bypass through legacy API, CLI, or Telegram.
- Tests required: exact boundary, concurrent create/charge, grace/credit limit, all entry points, existing-user non-impact.
- Definition of done: every creation path enforces the same policy and shadow/enforced decisions match.
- Rollback method: disable creation-block flag immediately; retain episode/audit records.
- Dependencies: Phases 9, 11, 18–19 plus enforcement approval gate.
- Suggested commit: `feat: enforce balance-aware user creation blocking`.
- Suggested patch version: none.

### Phase 21 — Billing suspension

- Objective: suspend service for balance exhaustion without overwriting classical/manual status.
- Exact scope: orthogonal billing suspension record/state, policy/grace worker, Xray removal, subscription response, per-owner batching.
- Expected files: model/migration, billing eligibility service/job, Xray and subscription adapters.
- Database changes: `billing_suspensions` or equivalent fields with reason/episode/timestamps.
- API changes: safe eligibility/billing state fields and owner actions; normal status remains unchanged.
- Security checks: only billing policy creates billing suspension; idempotent batches; ownership snapshots and audit.
- Tests required: manual disabled/expired/limited/on-hold combinations, worker concurrency, partial Xray failure, subscription behavior.
- Definition of done: exhausted owners' eligible users are suspended once and classical/manual states are preserved.
- Rollback method: disable suspension worker; use Phase 22 eligibility logic for audited recovery only.
- Dependencies: Phases 18–20 and explicit enforcement approval.
- Suggested commit: `feat: suspend users with separate billing eligibility state`.
- Suggested patch version: none.

### Phase 22 — Safe restoration

- Objective: restore only users suspended specifically by billing and still otherwise eligible.
- Exact scope: recharge trigger/worker, eligibility matrix, Xray add, retry/idempotency, stale suspension handling.
- Expected files: billing restoration service/job, user eligibility and Xray adapters.
- Database changes: restoration timestamps/outcomes on billing suspension episodes.
- API changes: owner-visible restoration status; optional audited retry endpoint.
- Security checks: never reactivate manual-disabled, expired, limited, deleted, on-hold-ineligible, or ownership-moved users incorrectly.
- Tests required: full state cross-product, concurrent recharge/disable/delete, partial Xray failure, repeated restoration.
- Definition of done: restoration invariant is proven and every outcome is auditable/retryable.
- Rollback method: stop auto-restoration; leave unresolved users suspended for owner review.
- Dependencies: Phase 21.
- Suggested commit: `feat: safely restore billing-suspended users after recharge`.
- Suggested patch version: none.

### Phase 23 — Admin management APIs and UI

- Objective: provide safe operational management for roles, scopes, templates, quotas, wallets, billing, and audit.
- Exact scope: admin APIs finalized; React routes/forms/lists; capability-driven controls; localization; reason dialogs; no client-side trust.
- Expected files: admin/billing/audit routers and schemas; `app/dashboard/src/` pages, contexts, services, types, locales.
- Database changes: none beyond prior phases.
- API changes: stabilize additive admin-management endpoints and pagination/filter contracts.
- Security checks: backend remains authoritative; UI hides/disables only for usability; safe rendering and no token/URL exposure.
- Tests required: API auth, component/integration, role snapshots, error handling, accessibility, UI/API compatibility.
- Definition of done: owner and each scoped role can complete only its supported workflows through the UI.
- Rollback method: disable new UI routes/endpoints; existing dashboard remains compatible.
- Dependencies: Phases 4–22 as relevant; UI can be delivered incrementally behind flags.
- Suggested commit: `feat: add secure admin and reseller management console`.
- Suggested patch version: none.

### Phase 24 — Reports and operational hardening

- Objective: finish observability, runbooks, retention, performance, and release readiness.
- Exact scope: metrics/alerts, reconciliation dashboards, backup/restore, retention/purge rules, rate limits, key operations, incident playbooks, full caller re-audit.
- Expected files: operational docs/config, jobs, metrics, CI, deployment files, selected performance fixes.
- Database changes: indexes/partitions/archival metadata only after measured evidence.
- API changes: stable health/metrics and export/report contracts.
- Security checks: least privilege, secret scans, audit retention, denial/rate-limit behavior, dependency/container scan.
- Tests required: full regression, load/failure recovery, backup restore, migration rollback, production-readiness suite.
- Definition of done: final checklist in Section 23 passes and owner signs off enforcement and release.
- Rollback method: deploy previous stable checkpoint, turn enforcement flags off, reconcile, restore verified backup only when required.
- Dependencies: all required phases.
- Suggested commit: `chore: harden admin billing operations for release`.
- Suggested patch version: `0.8.8` (or approved canonical equivalent).

## Appendix B — Superseded testing plan (non-executable)

### T1 — Unit and baseline regression

- What is tested: permission primitives, redaction, models, quota math, exact money math, status/eligibility rules, and current CRUD behavior.
- Required setup: isolated Python environment, deterministic clock, SQLite fixture, factories.
- Commands to run:

```bash
python -m pytest tests/unit -q
```

- Expected result: all unit tests pass with no warnings indicating precision, leaked secrets, or unhandled enum states.
- Failure conditions: any nondeterminism, secret exposure, float financial calculation, or changed legacy behavior without approval.
- Before continuing: fix every failure and add a regression test for the root cause.

### T2 — Permission, ownership, IDOR, and API authorization

- What is tested: four-role matrix, overrides, scope, object lookup, lists, aggregates, exports, subscription operations, and admin/node APIs.
- Required setup: owner, two resellers, scoped support/viewer, cross-owned users, tokens for each role.
- Commands to run:

```bash
python -m pytest tests/security tests/api -q
```

- Expected result: permitted actions succeed; all cross-owner and missing-permission attempts fail without data leakage.
- Failure conditions: any IDOR, total/count leakage, guessed-ID distinction, or frontend-only restriction.
- Before continuing: block the affected phase and repair the central policy/repository, not only the route.

### T3 — Templates and sensitive operations

- What is tested: server-side template application, assignment, version snapshots, custom permission, create/edit/delete/status/reset/revoke/transfer/bulk behavior.
- Required setup: multiple template versions/assignments, mixed protocols/inbounds, all user states.
- Commands to run:

```bash
python -m pytest tests/templates tests/operations -q
```

- Expected result: client tampering is rejected, snapshots remain stable, reasons/audits are complete.
- Failure conditions: accepted extra template values, unassigned access, missing audit, destructive reset/delete history loss.
- Before continuing: fix service-level validation and rerun T1–T3.

### T4 — Soft deletion, audit, CLI, and Telegram parity

- What is tested: retention/FKs, deleted visibility, audit immutability/redaction, authorization across CLI and Telegram handlers/jobs.
- Required setup: test database with history, mocked Telegram/Xray/report adapters, CLI runner.
- Commands to run:

```bash
python -m pytest tests/audit tests/deletion tests/cli tests/telegram -q
```

- Expected result: all entry points share decisions; protected history survives; secrets never enter audit/output.
- Failure conditions: direct CRUD bypass, cascade loss, anonymous actor, inconsistent bulk behavior.
- Before continuing: migrate the caller to the central service and add a caller-registry regression test.

### T5 — Quota boundaries and concurrency

- What is tested: every classical quota, atomic creation/update/transfer, rate limit, lock order, deadlock retry.
- Required setup: SQLite and MySQL; parallel clients/processes; near-limit fixtures.
- Commands to run:

```bash
python -m pytest tests/quotas -q
python -m pytest tests/concurrency/test_quotas.py -q
```

- Expected result: committed state never exceeds a limit and no false unlimited/null interpretation occurs.
- Failure conditions: count-then-insert race, negative counters, deadlock without safe retry, database-specific divergence.
- Before continuing: correct transaction/locking design and rerun under higher concurrency.

### T6 — Migration and backward compatibility

- What is tested: clean install, production-like upgrade, backfill, constraints, downgrade/code rollback compatibility, legacy API/dashboard behavior.
- Required setup: anonymized production-scale SQLite/MySQL snapshots, previous stable image, backup/restore tooling.
- Commands to run:

```bash
alembic heads
alembic upgrade head
python -m pytest tests/migrations tests/compatibility -q
```

- Expected result: one head, validated row counts/checksums, no orphans, legacy client suite passes.
- Failure conditions: data loss, long unsafe locks, multiple heads, null ownership, irreversible code rollback before checkpoint.
- Before continuing: revise expand/backfill/constraint stages and rehearse restore.

### T7 — Ledger integrity and billing calculation

- What is tested: append-only entries, cached balance, idempotency, refunds/corrections, raw usage, coefficient/pricing snapshots, reset billing behavior.
- Required setup: exact pricing fixtures, multi-node usage, unlimited users, ownership transfers, reset checkpoints.
- Commands to run:

```bash
python -m pytest tests/billing/test_ledger.py tests/billing/test_calculation.py tests/billing/test_usage_reset.py -q
```

- Expected result: ledger sum equals balance; historical charges never change; reset creates no refund/duplicate/negative usage.
- Failure conditions: float use, mutable history, duplicate effect, coefficient drift, deleted-reference loss.
- Before continuing: stop billing work, reconcile fixtures, and fix the invariant at the transaction boundary.

### T8 — Billing worker concurrency, shadow mode, and reconciliation

- What is tested: duplicate events, concurrent workers, crashes/restarts, leases, late events, shadow no-effect, reconciliation and period close.
- Required setup: multiple worker processes, fault injection, representative billing cycle dataset.
- Commands to run:

```bash
python -m pytest tests/billing/test_workers.py tests/billing/test_shadow.py tests/billing/test_reconciliation.py -q
```

- Expected result: exactly one charge effect, zero unexplained variance, and no shadow service/balance impact.
- Failure conditions: duplicate/missing charge, stuck claim, nonzero unexplained discrepancy, shadow enforcement.
- Before continuing: enforcement remains disabled until all failures are fixed and the full cycle is repeated.

### T9 — Suspension/restoration and UI/API integration

- What is tested: warnings, create blocking, credit/grace boundary, billing suspension, complete restoration state matrix, React capability flows.
- Required setup: enforcement staging environment, mocked/realistic Xray nodes, built dashboard, accounts in every user state.
- Commands to run:

```bash
python -m pytest tests/billing/test_enforcement.py tests/integration -q
cd app/dashboard && npm ci && npm run build
```

- Expected result: only billing-suspended and otherwise eligible users restore; UI cannot bypass or misrepresent API decisions.
- Failure conditions: manual/expired/limited/deleted user reactivation, partial operation hidden, unauthorized UI/API success.
- Before continuing: disable enforcement, repair eligibility/idempotency, and repeat T7–T9.

### T10 — Full regression and production readiness

- What is tested: all suites, security scans, load, backup/restore, upgrade/rollback, observability, incident switches, CLI/Telegram/UI, final reconciliation.
- Required setup: production-like staging topology and data volume, multi-worker deployment, verified backup, release candidate image.
- Commands to run:

```bash
python -m pytest -q
cd app/dashboard && npm ci && npm run build
alembic upgrade head
```

- Expected result: zero critical/high security findings, all tests pass, performance SLOs hold, backup restores, enforcement kill switch works, reconciliation is clean.
- Failure conditions: any unresolved security/data-integrity issue, unexplained billing variance, failed restore/rollback, missing alert/runbook.
- Before continuing: release is blocked; fix, rebuild the candidate, and repeat the entire T10 procedure.

## Appendix C — Superseded release procedure (non-executable)

1. Freeze scope and map every changed caller from the inventory to an owner, test, and permission.
2. Confirm all required implementation phases and T1–T10 passed on the exact candidate commit.
3. Confirm one migration head and capture upgrade timing, row counts, checksums, orphan checks, and rollback/restore rehearsal evidence.
4. Verify secret scan, dependency/container scan, audit redaction, and least-privilege configuration.
5. Verify a complete shadow billing period with zero unexplained discrepancy.
6. Obtain explicit owner approval for pricing, rounding, credit limit, grace, warning, creation block, suspension, restoration, retention, and version scheme.
7. Back up the production database and verify restore before migration.
8. Deploy schema expansion with enforcement flags off; validate health and compatibility.
9. Deploy application, run smoke/API/CLI/Telegram/UI checks, and monitor audit/usage/worker metrics.
10. Enable warning and creation-block policies progressively. Enable suspension/restoration only after a separate go/no-go review.
11. Run reconciliation after each enablement step. On unexplained variance, turn enforcement off, preserve records, and investigate.
12. Create the approved patch tag/release only after the stable checkpoint is usable and tested; publish migration, compatibility, and rollback notes.

## Appendix D — Superseded decision list (non-executable)

1. Canonical version scheme: runtime `0.8.x` versus custom repository `v3` tags.
2. Stable database identity for environment-defined `SUDOERS`.
3. Handling of legacy users with null `admin_id`: designated owner versus holding account.
4. Whether legacy `created_by_admin_id` may be marked as inferred from owner during backfill.
5. Exact permission defaults for `support` and the allowed scope shapes for `support`/`viewer`.
6. Username reuse policy after soft deletion.
7. Credit unit/currency, integer scale, pricing formula, coefficient precision, charge aggregation boundary, and rounding rule.
8. Opening wallet balances and whether any historical usage is imported as financial debt; recommendation: do not infer debt from `admins.users_usage`.
9. Billing-period length, late-event policy, grace period, warning thresholds, credit limits, and enforcement rollout percentages.
10. Retention and physical purge policy for non-financial operational data; ledger, billing, audit, and historical usage remain non-cascading and retained according to legal/operational requirements.
11. Legacy `/api/user` deprecation window and third-party client inventory.
12. Supported production database/topology and whether multi-replica workers are expected at launch.

## Appendix E — Superseded starting point (non-executable)

This former starting point is superseded by Section 25. It must not be started.
