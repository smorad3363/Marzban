# Marzban v4.9.8 — Codex Master Runbook V3 Compact

> **Purpose:** Single English handoff/runbook for staged Marzban work. It preserves the business requirements, blockers, invariants, test contract, current baseline, and execution ledger while minimizing repeated context.
>
> **Target:** `smorad3363/Marzban`, release line `v4.9.8`.
>
> **Priority:** correctness, evidence, reversibility, and preservation of existing local work over speed.
>
> **Revision:** V3 Compact — token-optimized without reducing required verification.

---

## 1. Codex Reading Protocol — Token Efficient

Do **not** re-read this whole file before every Stage.

When the owner says `Execute Stage N`, read only:

1. Sections **1–6** of this file (control core).
2. **Current State Snapshot** in Section 7.
3. The row for Stage N in the **Dependency/Blocker Matrix**.
4. The **Stage N card**.
5. Only the `D-xx` decisions and shared rules referenced by that Stage.
6. The **latest relevant Execution Ledger entry**.
7. Applicable repository governance (`AGENTS.md` and documents it mandates).

Read other sections only when referenced, when repository evidence conflicts with this runbook, or when a Runbook revision changes the relevant contract.

### Per-Stage execution loop

For an authorized Stage N:

1. Run Stage 0 preflight in read-only mode.
2. Preserve all pre-existing local changes.
3. Check prerequisites/blockers.
4. If blocked, report `BLOCKED`, record why, and stop.
5. Re-verify the relevant historical findings against current code/DB models.
6. Implement **only Stage N**.
7. Add/update Stage-specific executable tests.
8. Run **targeted tests + adjacent regression only**; do not run the entire project suite after every Stage unless the Stage is broad enough to require it.
9. If Stage changes schema/queries, run the required MySQL/migration/query checks for that Stage.
10. If Stage changes frontend, run relevant frontend tests/typecheck/build for that Stage.
11. Update repository docs required by `AGENTS.md`.
12. Append a compact evidence entry to the Execution Ledger.
13. Stop. Do not continue to Stage N+1 automatically.

### Test cadence

- **Every Stage:** targeted verification + adjacent regression.
- **After Stage 4:** Integration Gate A for Stages 1–4.
- **After Stage 9:** Integration Gate B for Stages 5–9 plus critical dependencies from earlier stages.
- **Stage 13:** full-system regression/release gate across all implemented stages.

This prevents late discovery of old regressions without wasting time/tokens running the full suite after every small change.

### Stage 7–13 scope optimization — Owner-confirmed 2026-08-23

This contract applies to every remaining Stage, Stage 7 through Stage 13. It does
not alter completed Stage 0–6 implementation or evidence, and it remains subordinate
to `AGENTS.md` and repository documents required by it.

**Deployment/data baseline**

- This deployment has never served production traffic and has no historical
  production User/Admin/account/settings data that must be migrated.
- Do not design or test complex compatibility/backfill paths solely for hypothetical
  historical production data. Do not synthesize old account populations unless a
  current migration, current working-tree dependency, or security/accounting
  invariant requires them.
- Preserve safe upgrade from the current install baseline `v4.9.8` and from the
  current project schema/Alembic chain. At this decision point, the local schema head
  is `5b8d1f3a7c64`; later Stages must record their actual starting head.
- Preserve source/API/schema compatibility required by the current working tree.
  Keep the implemented `LEGACY_COMPAT` behavior, but do not expand it without a real
  current dependency.
- Do not rename, remove, rewrite, or retest already-PASS legacy-related code merely
  for cleanup. Revisit Stage 0–6 only when a real defect or dependency conflict is
  demonstrated.

**Database and portability baseline**

- Supported production DB for this project is MySQL 8.x / InnoDB only.
- Migration, transaction, locking, concurrency, index, query-plan, and DB performance
  evidence must run on real MySQL. SQLite may be used only as a fast isolated unit
  harness; SQLite success is never migration/concurrency/production-DB evidence.
- Do not implement or test PostgreSQL or TimescaleDB support in Stage 7–13.
- Prefer portable SQLAlchemy and Alembic constructs where practical, while preserving
  MySQL correctness, transaction safety and performance. Isolate and document any
  required MySQL-specific SQL/DDL/index/query behavior and why it is required.
- TimescaleDB/PostgreSQL migration is a separate future project. Do not sacrifice
  current MySQL correctness or add speculative portability code now.

**Efficient evidence baseline**

- Continue targeted Stage tests plus adjacent regression. Do not rerun expensive old
  matrices unless the current Stage changes their relevant behavior.
- Remove redundant cross-database and hypothetical legacy-data validation from future
  Stage requirements. Token efficiency never replaces executable evidence.
- Preserve full relevant evidence for security, accounting, hierarchy, authorization,
  idempotency, concurrency, ledger/refund correctness, Plan/network scope,
  backup/restore safety, and Telegram operational reliability.
- Stage-specific MySQL focus: Stage 7 hierarchy/freeze/delegation races; Stage 8 bulk
  accounting and resume/idempotency; Stage 9 dashboard aggregates/query plans;
  Stage 10 pagination/index plans; Stage 11 scheduler/outbox/backup locks and restore;
  Stage 12 only if installer work changes DB behavior; Stage 13 final current-baseline
  migration, concurrency, performance and restore gate.

### Evidence vocabulary

- `PASS` — exact relevant command/test was executed and succeeded.
- `FAIL` — executed and failed.
- `NOT EXECUTED` — not run.
- `UNCERTAINTY` — evidence is incomplete or an assumption/environment is unresolved.
- `BLOCKED` — safe execution cannot continue until a prerequisite/decision is resolved.

Never replace `NOT EXECUTED` with “should work”, “looks fine”, or similar language. Never claim “bug-free”.

### Compact reporting rule

Do not paste huge raw logs into this file. Record:

- exact command;
- status;
- pass/fail counts when available;
- duration when useful;
- concise failure/root-cause excerpt;
- migration/query evidence IDs or summaries.

Preserve exact raw output only when it is uniquely needed for debugging or required by repo governance.

---

## 2. Source of Truth, Safety, and Authorization

### Governance precedence

Resolve conflicts in this order:

1. applicable repository `AGENTS.md`;
2. repository docs explicitly required by `AGENTS.md` (historically including `docs/ADMIN_HIERARCHY_ROADMAP_FA.md` where applicable);
3. this Runbook;
4. historical notes, Graphify, chat summaries, comments.

This Runbook is the single Codex handoff file, not a replacement for repository governance.

### Required placement

Before Stage 1+, this Runbook must be inside the canonical Git workspace, recommended:

`docs/MARZBAN_CODEX_MASTER_RUNBOOK.md`

If it is outside the repo, Stage 0 may inspect it, but implementation is `BLOCKED` until it is placed inside the repo.

### Canonical repository rule

Use one authoritative Marzban working tree in VS Code. The VS Code root must equal:

```bash
git rev-parse --show-toplevel
```

If multiple Desktop clones/worktrees exist and any may contain unique work, do not delete or merge them blindly. Preserve unique commits, diffs, untracked files, and stashes first.

### Non-negotiable safety

Do not:

- use `git reset --hard`, destructive checkout/restore, `git clean -fdx`, forced stash deletion, or broad filesystem deletion to “clean up” context;
- overwrite uncommitted fixes without inspecting the current diff;
- delete tests, migrations, docs, backups, DB data, `.env`, secrets, keys, or files of uncertain purpose;
- mutate production silently;
- commit/push/tag/release/deploy/fork unless explicitly authorized for that action;
- treat UI hiding as authorization; protected behavior must be enforced server-side;
- implement accounting only in frontend state;
- add a cash/payment/wallet subsystem to the panel;
- remove the legacy/default Marzban sales bot until functional parity is proven and the owner approves;
- treat Graphify as stronger evidence than source code, DB behavior, migrations, or tests.

If deletion/cleanup is uncertain: **keep it and report `UNCERTAINTY`.**

### Current authorization model

Saying `Execute Stage N` authorizes code/test work necessary for **that Stage only**. It does not automatically authorize commit, push, release, deploy, production restart, production data mutation, or unrelated external operations.

---

## 3. Project Identity and Historical Baseline

### Repository

`https://github.com/smorad3363/Marzban`

### Target version

`v4.9.8`

Historical reviewed commit:

`b45e3af663cd16d6dcca8492a6520b7e39db9d80`

Re-verify current HEAD/tag every Stage 0.

### Owner install command

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v4.9.8/scripts/marzban.sh)" @ install --version v4.9.8 --database mysql
```

### Owner update command

```bash
marzban update --version v4.9.8
```

### Upstream node installer currently referenced

```bash
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/smorad3363/Marzban-scripts/1ef7ad62d2c16e4450f1a0de9678c8a8c883b154/marzban-node.sh)" @ install --name master
```

### Historical checkout observations — leads, not current PASS

| ID | Historical observation |
|---|---|
| BASE-01 | Checkout was `v4.9.8` / `b45e3af...` and dirty. |
| BASE-02 | BUG-04 still existed in renewal classification. |
| BASE-03 | A local uncommitted BUG-09 fix existed around device-limit delete accounting (`capture_delete()` or equivalent). |
| BASE-04 | A local uncommitted BUG-10 fix existed around real Owner vs legacy `is_sudo`. |
| BASE-05 | Plan Inbound selector was partially implemented locally, but empty Inbound remained allowed/inconsistent. |
| BASE-06 | New billing IDs `SEAT_CREDIT`, `USED_TRAFFIC`, `ALLOCATED_TRAFFIC` were not observed yet. |
| BASE-07 | Hierarchy, Plan access, renewal policy, ledger, and bulk infrastructure already existed; later work is refactor/migration, not greenfield. |
| BASE-08 | Historical Graphify output was fresh for released v4.9.8 but potentially stale versus local working-tree changes. |
| BASE-09 | Real Master/Node/Tunnel validation was previously `NOT EXECUTED`. |
| BASE-10 | Required MySQL migration validation was previously incomplete in one environment. |

“No Stage recorded” means no Stage has been executed under **this evidence contract**; it does not mean the project is unimplemented.

---

## 4. Mandatory Stage 0 — Read-Only Preflight

Stage 0 runs before every implementation Stage and must not modify the working tree.

### Repository state

Record at minimum:

```bash
git rev-parse --show-toplevel
git rev-parse HEAD
git describe --tags --always --dirty
git status --short --branch
git diff --stat
git diff
git diff --staged
git log --oneline --decorate -n 20
```

Also inspect remotes, relevant local branches/stashes, and any duplicate repo risk if applicable.

### Repository instructions

Read applicable:

- `AGENTS.md`;
- required roadmap/docs;
- README/build/test instructions;
- package scripts/lockfiles;
- migration conventions;
- deployment/test harness instructions.

Do not invent package-manager/test commands.

### Environment baseline

Identify:

- backend dependency/environment method;
- backend targeted/full test commands;
- frontend package manager and test/typecheck/build commands;
- Alembic head(s) and migration commands;
- production DB expectation (`MySQL` for owner install path);
- availability of disposable MySQL;
- API/integration/E2E harness;
- Graphify invocation and freshness.

SQLite is not evidence for MySQL-specific migration behavior.

### Graphify

During Stage 0, inspect only. Do not refresh Graphify if refresh changes files. After Stage 0, the authorized Stage may refresh it when useful, and must record generated changes separately.

Use Graphify mainly for blast-radius understanding of:

- user update -> policy -> quota/accounting;
- admin resource adjustment -> ledger -> hierarchy;
- Plan -> user create -> Inbound/Host -> subscription;
- device-limit -> delete/suspend -> deleted-user accounting;
- freeze -> admin auth/actions -> users/subtree;
- backup -> scheduler -> artifact -> Telegram -> health.

### Obsidian-compatible memory

Keep durable project memory as Markdown compatible with Obsidian. Obsidian is a workstation application, not a Marzban dependency. Do not create competing runbooks. If Obsidian cannot be opened from the environment, report `NOT EXECUTED` rather than pretending.

---

## 5. Product Contract — Requirements Registry

These IDs are authoritative requirements for Stage planning. Stage cards reference them instead of repeating long prose.

### Admin roles and accounting modes

| ID | Requirement |
|---|---|
| R-ADM-01 | Roles/scopes must distinguish real Owner, Admin/Reseller, and optional Sub-admin; legacy `is_sudo` is not a substitute for Owner identity. |
| R-MODE-01 | `SEAT_CREDIT`: consumable user/device-capacity units. Creation consumes finite units. Expiry does **not** restore them. |
| R-MODE-02 | `USED_TRAFFIC`: user count unlimited by this mode; accounting charges only newly consumed traffic delta. |
| R-MODE-03 | `ALLOCATED_TRAFFIC`: user count unlimited by this mode; accounting charges traffic allocated/provisioned during create/renew/update. |
| R-MODE-04 | Billing mode, permissions, network assignment, and resource entitlements are separate concepts. |

### Restricted creation and network ownership

| ID | Requirement |
|---|---|
| R-CREATE-01 | `SEAT_CREDIT` Admin is Plan-only; raw user builder unavailable in UI and denied server-side. |
| R-CREATE-02 | `USED_TRAFFIC` normal create form exposes only username, volume, time, description. |
| R-CREATE-03 | `ALLOCATED_TRAFFIC` uses the same simplified field philosophy unless a documented constraint requires otherwise. |
| R-NET-01 | Restricted admins cannot select/inject arbitrary Inbound, Host, or device/concurrency count. |
| R-NET-02 | Allowed Inbounds/Hosts are assigned centrally from Admin Management/Plans and enforced by backend/subscription generation. |
| R-USER-01 | Each Admin gets a unique stable random prefix; new customer usernames become `prefix_requestedusername`. Existing users are not mass-renamed without explicit authorization. |

### Plans and Trials

| ID | Requirement |
|---|---|
| R-PLAN-01 | Replace comma-separated Inbound typing with live multi-select/checkbox selector and backend validation. |
| R-PLAN-02 | Do not allow a Plan state that cannot produce a valid user; empty network scope must follow an explicit rule. |
| R-PLAN-03 | If Plan-specific Host selection is supported, persist it and enforce it in generated subscriptions. |
| R-PLAN-04 | Wire Plan access controls (`allowed_admin_ids`, subtree semantics/current equivalent) into real UI + authorization. |
| R-PLAN-05 | Unlimited semantic values must display as Unlimited/Persian equivalent, not `0 B` where zero is the unlimited sentinel. |
| R-TRIAL-01 | Trial/Test is first-class metadata, not inferred from names/usernames. |
| R-TRIAL-02 | Required examples: 1 GiB/1 day/1 device; 2 GiB/1 day/1 device; Unlimited/1 day/1 device; Unlimited/1 day/2 devices when accounting permits. |
| R-TRIAL-03 | Per-admin Trial quota is independently grantable/reclaimable and idempotent. |
| R-TRIAL-04 | Trial cleanup supports preview/dry-run and preserves required deleted-user accounting/history. |

### Admin resources, hierarchy, referral, freeze

| ID | Requirement |
|---|---|
| R-RES-01 | Do not edit finite admin resources as blind absolute fields. Use auditable Grant/Reclaim delta operations. |
| R-RES-02 | Resource adjustments record resource, delta, before/after, actor, target, reason, timestamp, idempotency/correlation ID. |
| R-RES-03 | New-admin initial credit uses the same accounting-safe adjustment mechanism. |
| R-HIER-01 | Child cannot receive/delegate resources, Plans, network scope, or permissions beyond parent’s delegable authority. |
| R-HIER-02 | Finite parent->child delegation is transactional and cannot double-spend. |
| R-REF-01 | Referral relationship is separate from hierarchy; only Owner can set/change referral relation/rate. |
| R-REF-02 | Do not add cash/pricing/payment-wallet clutter. Referral reward unit remains an explicit business decision. |
| R-FREEZE-01 | Owner can freeze/unfreeze an Admin; freeze blocks management activity and applies an explicit reversible user/subtree policy. |
| R-FREEZE-02 | Unfreeze must not wrongly reactivate users disabled for unrelated reasons; preserve provenance. |

### Admin UX, bulk operations, pagination, localization

| ID | Requirement |
|---|---|
| R-UX-01 | Refactor Admin create/manage flow to be simpler and mode-aware; new-admin phone required; Discord removed from intended UI. |
| R-UX-02 | Admin dashboard shows professional mode-aware metrics and week-over-week change with efficient aggregation. |
| R-BULK-01 | Bulk Admin actions include Grant/Reclaim such as N GiB to selected Admins. |
| R-BULK-02 | Bulk User actions can add volume/time/both to all users or selected-admin users under explicit scope/transaction semantics. |
| R-PAGE-01 | User cards use true server-side pagination: default 10, options 10/25/50, backend hard max 50; search/filter/sort server-side. |
| R-I18N-01 | Persian UX uses stable backend error codes mapped to clean Persian text; raw English is not normal user-facing behavior. |

### Telegram, backup, legacy bot, external scripts

| ID | Requirement |
|---|---|
| R-TG-01 | Telegram integration sends detailed operation logs, backup events/files, backup health/failures, and near-limit Admin alerts. |
| R-TG-02 | Default backup interval is 30 minutes; generation health and remote delivery health are tracked separately. |
| R-TG-03 | Near-limit alerts require dedup/hysteresis to avoid spam. |
| R-TG-04 | Prefer durable outbox/retry semantics so Telegram failure does not erase a successful business operation. |
| R-BOT-01 | Do not remove the legacy/default sales bot until capability parity is proven and Owner approves. |
| R-OPS-01 | Fork `gozargah/Marzban-scripts` into Owner GitHub in the dedicated authorized Stage; preserve upstream sync and prefer pinning stable tag/commit over floating master when practical. |

### Existing correctness issues from review

| ID | Requirement / bug |
|---|---|
| BUG-04 | Numeric increase of user volume/time must not automatically mean renewal. Ordinary edits must not consume Renewal quota. |
| BUG-05 | Renewal quota/policy management exists backend-side historically but needs clear management UI/flow. |
| BUG-06 | Admin traffic credit is read-only by design; desired editable UX must translate delta to ledger-safe Grant/Reclaim, never blind `total_traffic` mutation. |
| BUG-07 | Raw English backend/domain errors and generic English fallbacks must be localized through stable codes. |
| BUG-08 | Unlimited Plan display must not show `0 B` where zero means unlimited. |
| BUG-09 | Device-limit auto-delete must preserve deleted-user traffic/accounting exactly once. |
| BUG-10 | Legacy `is_sudo=True` must not exempt non-Owner hierarchy admins from policy. |

---

## 6. Shared Engineering Contract

### Critical security/data invariants

1. Ordinary edit does not consume Renewal quota unless the operation is explicitly a renewal.
2. Actual renewal still enforces Renewal policy exactly once.
3. Device-limit and manual delete preserve required deleted-user accounting exactly once.
4. Only intended real Owner receives policy bypass where defined.
5. Restricted Admin cannot bypass Plan/network/device restrictions by direct API payload.
6. Every finite resource mutation changes balance exactly once and creates one auditable effect.
7. Idempotent retry cannot double grant/reclaim/charge/consume Trial quota/referral effect/bulk mutation.
8. Child delegation cannot create resources from nothing or exceed parent authority.
9. `USED_TRAFFIC` charges only new bytes; repeated reconciliation with unchanged usage charges zero.
10. `ALLOCATED_TRAFFIC` charges defined allocation delta and never silently refunds without an approved rule.
11. `SEAT_CREDIT` does not auto-return on expiry.
12. Plan state must be sufficient to create a valid user.
13. Host/Inbound scoping must affect actual subscriptions, not only UI/storage.
14. Freeze/unfreeze preserves unrelated prior disabled state.
15. Bulk operations respect target scope and authorization.
16. Telegram secrets never leak into logs/API responses.
17. Telegram delivery failure does not erase the durable underlying event.
18. Backup health distinguishes generated vs remotely delivered.
19. Username prefix uniqueness is enforced server-side/DB-side where feasible.

### Explicit operation intent

Do not infer business operations only from numeric deltas. Propagate trusted server-side intent such as Create, Edit, Renew, Trial Create, Bulk Adjust. Do not trust a client-provided flag as authorization to avoid quota consumption.

### Idempotency and concurrency

For retryable create/renew/grant/reclaim/Trial/bulk operations:

- use an idempotency key or equivalent;
- persist/derive a canonical **payload fingerprint**;
- same key + materially different payload => deterministic conflict;
- define key scope, retention, and replay response;
- enforce critical races at DB/transaction level, not UI level.

Explicitly test races for grants/reclaims, parent delegation, last Trial quota, usage reconciliation, prefix collision, bulk retry, backup scheduler overlap, and Telegram outbox delivery.

### Migration/MySQL discipline

For schema/data changes:

1. Verify current Alembic head and representative current/null data. For Stage 7–13,
   include legacy data only when an actual current dependency requires it; do not
   create hypothetical production populations.
2. Prefer additive migration -> backfill -> code switch -> later cleanup for risky changes.
3. Do not mass-rename existing users without explicit authorization.
4. Do not guess a billing mode for legacy Admins.
5. Test on actual supported MySQL for MySQL claims.
6. Define online-DDL/lock budget for large tables; do not assume ALTER is non-blocking.
7. Large backfills: batch size, checkpoint/resume, bounded transactions, observable progress.
8. Define deadlock/lock-timeout retry; retries must be idempotent.
9. Define rolling backward/forward app-schema compatibility.
10. Distinguish schema rollback, application rollback, and data rollback.
11. New high-traffic indexes must be justified by actual MySQL query plans.

### Performance discipline

- Pagination hard max 50; never fetch all users to render 10.
- Stable deterministic ordering with unique tie-breaker.
- Offset pagination is acceptable if representative MySQL measurements are healthy; use cursor/keyset only when evidence shows deep-offset/consistency problems.
- Avoid N+1 in user cards, dashboard, Plan/network selectors, bulk previews, hierarchy trees.
- For critical MySQL list/dashboard queries use `SHOW INDEX` and `EXPLAIN ANALYZE` where supported, otherwise `EXPLAIN` + measured timing.
- Add composite indexes from real filter/sort/group patterns, not speculation.
- Ledger/outbox tables need query-driven indexes and approved retention/archive strategy before unbounded growth.

### Telegram/backup shared rules

- Prefer existing Marzban backup mechanism over a second incompatible format.
- Default schedule: every 30 minutes.
- Track last attempt, generation success, delivery success, artifact ID/name, size/hash when practical, last error, retry count, health.
- Prevent overlapping same-period backup jobs where multiple workers exist.
- A generated archive with failed Telegram upload is not a successful remote backup.
- Use durable outbox/retry for operation notifications where feasible.
- Do not log bot token/secrets.
- Real Telegram delivery is `NOT EXECUTED` unless real credentials/environment are used.

---

## 7. Current State Snapshot

Update this compact section only when a Stage changes durable project state. Do not paste raw logs here.

- Target: `v4.9.8`.
- Historical reviewed HEAD: `b45e3af663cd16d6dcca8492a6520b7e39db9d80`; re-verify.
- Working tree historically dirty with meaningful local changes.
- BUG-04 historically still present.
- BUG-09 and BUG-10 historically had local uncommitted fixes; preserve/verify before reimplementation.
- Plan Inbound selector historically partially implemented locally; empty selection still inconsistent.
- Three new billing-mode identifiers historically not present.
- `D-05` was resolved on `2026-08-22`: `ALLOCATED_TRAFFIC` never auto-refunds;
  refund requires a persistent authorized approval request and only approval may
  create ledger credit.
- Existing hierarchy/ledger/Plan/renewal/bulk infrastructure must be reused/refactored where sound.
- Historical real Master/Node/Tunnel validation: `NOT EXECUTED`.
- Historical supported-MySQL migration validation: incomplete / `NOT EXECUTED` in one environment.
- No implementation Stage from V3 is `PASS` until entered in the Execution Ledger below.

---

## 8. Open Decisions — Do Not Guess

| ID | Decision | Blocks |
|---|---|---|
| D-01 | **RESOLVED 2026-08-22.** `SEAT_CREDIT` renewal consumes Seat Credit exactly like creation. Cost equals the Plan's explicit finite positive device/concurrency count; expiry never restores old Seat Credit. Renewal must be transactional and idempotent so retry cannot double-consume. | implementation in Stage 5 |
| D-02 | **RESOLVED 2026-08-23.** Referral is attribution-only for now. Persist and audit the referral relationship/configuration; create no automatic financial, traffic, Seat or other resource reward. | implementation in Stage 7 |
| D-03 | **RESOLVED 2026-08-22.** Apply each creator Admin/Owner's stable unique persisted prefix to every newly created customer User as `prefix_requested_username`. Never prefix Admin/Owner login usernames and never mass-rename existing Users. Enforce prefix and final username uniqueness server-side under concurrency. | implementation in Stage 5 |
| D-04 | **RESOLVED 2026-08-23.** Owner Freeze covers the target Admin, every descendant Admin and all Users in that subtree. Freeze/unfreeze is reversible, audited and idempotent, and restoration may change only state caused by that freeze event. | implementation in Stage 7 |
| D-05 | **RESOLVED 2026-08-22.** `ALLOCATED_TRAFFIC` never auto-refunds on delete/expiry/reduction. Refund uses the persistent approval workflow defined below. | implementation in Stage 3/5 |
| D-06 | **RESOLVED 2026-08-23.** Every User bulk job requires explicit `ALL_USERS`, `SELECTED_ADMINS_DIRECT`, or `SELECTED_ADMINS_SUBTREE` scope. DIRECT never implies descendants; SUBTREE uses the selected Admins plus their authorization descendants. Resolve and persist an immutable User-ID snapshot at job creation; exclude deleted Users; enforce actor authorization server-side; persist scope, selected Admin IDs, resolved count, actor and operation ID; show scope/count preview in UI. | implementation in Stage 8 |
| D-07 | **RESOLVED 2026-08-23.** Use a persistent idempotent job, deterministic bounded chunks and one short transaction per target User. Persist `PENDING/SUCCESS/FAILED/SKIPPED`, stable operation/per-target fingerprints and error codes. Partial failure does not rollback successes; retry only incomplete/retryable targets and never reapplies success. Final report stores total/success/failed/skipped. Use MySQL 8/InnoDB row locking and deadlock retry; never hold a transaction across the full job. | implementation in Stage 8 |
| D-08 | **RESOLVED 2026-08-23.** MySQL backup every 30 minutes/RPO <=30m; one job; validated AES-256-GCM artifact with size/SHA-256; Telegram remote plus encrypted local spool; delivered local retention 48h without deleting the only valid backup; bounded retry/dead-letter and Owner escalation; oversize preserved and blocked; explicit isolated restore verification and RTO <=2h; never automatic production restore. | implementation in Stage 11 |
| D-09 | **RESOLVED 2026-08-22.** No fallback. A `SEAT_CREDIT` Plan requires an explicit finite positive device/concurrency count; its Seat cost equals that count. Missing, zero/unlimited, or unlimited values are rejected. | implementation in Stage 3 |
| D-10 | **RESOLVED 2026-08-22 — Option 1.** Strict explicit scope: every Plan requires at least one allowed Inbound and, where Host scoping applies, at least one eligible active Host per selected Inbound. Empty, disabled, deleted, unavailable, or out-of-Admin-scope network selections fail closed and never mean “all”. Enforce the same effective scope during Plan validation, user creation, and subscription generation. No snapshot default or dynamic inheritance unless explicitly configured in a later Stage. | implementation in Stage 4 |
| D-11 | **RESOLVED 2026-08-23.** Audit/accounting/security/hierarchy/refund/freeze/grant history is retained indefinitely. Outbox PENDING/RETRYING is never purged; DELIVERED retention is 30 days; FAILED/DEAD_LETTER retention is 90 days; cleanup is bounded and cannot remove business idempotency or ledger evidence. | implementation in Stage 11 |

### Resolved D-05 — Allocated Traffic Refund Request contract

1. User deletion and refund approval are separate operations. Delete, expiry, or
   quota reduction never returns `ALLOCATED_TRAFFIC` credit.
2. A requested refund creates a persistent Refund Request routed to the authorized
   parent Admin or Owner.
3. The request preserves an immutable account snapshot containing requester Admin,
   target User, owner/parent Admin, billing mode/Plan, allocated quota, current
   quota, used traffic, remaining traffic, created/expiry dates, pre-delete status,
   requested refund amount, request reason/note, timestamp, and
   operation/correlation ID.
4. Status is exactly one of `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`.
5. Authorized parent/Owner may approve or reject. Approval/rejection may include an
   optional explanation.
6. Only `APPROVED` creates actual ledger credit/refund. `REJECTED` and `CANCELLED`
   never alter credit.
7. Preserve full Refund Request history and audit trail. Enforce authorization,
   idempotency, transaction atomicity, and concurrency protection.

### Resolved D-09 and legacy migration contract

1. `SEAT_CREDIT` has no one-Seat fallback. A Plan is valid only with an explicit
   finite positive device/concurrency count, and Seat cost equals that count.
2. Missing, zero-as-unlimited, or unlimited device/concurrency values are invalid
   for `SEAT_CREDIT` and must be rejected.
3. Existing Admins remain `LEGACY_COMPAT` (or equivalent backward-compatible
   state) and preserve legacy behavior until Owner explicitly assigns a new billing
   mode.
4. Migration must not silently select a new mode, reinterpret balances, or convert
   historical usage/allocation/Seat counters.

Ask only when the requested Stage actually depends on the decision.

---

## 9. Stage Dependency and Blocker Matrix

A Stage may run only when prerequisites are recorded `PASS`, unless the owner explicitly re-baselines/waives with evidence recorded in the Ledger.

| Stage | Hard prerequisites | Formal blockers |
|---|---|---|
| 1 | Stage 0 | none currently known |
| 2 | Stage 1 PASS | none currently known |
| 3 | Stage 2 PASS | no unresolved decision; implement resolved D-05/D-09 and legacy compatibility contracts |
| 4 | Stage 3 PASS | D-10 |
| 5 | Stages 3,4 PASS + Gate A PASS | D-01, D-03; preserve resolved D-05 contract |
| 6 | Stage 5 PASS | Unlimited Trial accounting must be safe for active billing modes |
| 7 | Stages 2,3,5 PASS | D-02 for reward settlement, D-04 for freeze cascade |
| 8 | Stages 2,3,6,7 PASS | none; D-06 and D-07 resolved 2026-08-23 |
| 9 | Stages 3–8 PASS | inherited unresolved decisions only |
| 10 | Stage 9 PASS + Gate B PASS | pagination API contract explicit |
| 11 | Stages 2,7,8,10 PASS | D-08, D-11 for retention/purge |
| 12 | Stage 0 + explicit Owner authorization for external GitHub action | authenticated GitHub access + pin/update strategy |
| 13 | Stages 1–11 PASS; Stage 12 PASS or explicitly excluded from release scope | all release-blocking uncertainty resolved/accepted |

If prerequisite/blocker fails: append `BLOCKED` with exact reason and stop. Do not smuggle earlier work into a later Stage.

---

# 10. Stage Cards

## Stage 1 — Critical Accounting and Policy Correctness

**Scope:** BUG-04, BUG-09, BUG-10 only. No Admin redesign.

**Outcome:**

- ordinary volume/time edit is not renewal merely because a value increases;
- explicit renewal still enforces Renewal policy;
- device-limit deletion preserves deleted-user accounting exactly once;
- only intended real Owner gets policy bypass.

**Required targeted tests:**

1. Ordinary data-limit increase with `renewal_remaining=0` and sufficient ordinary allowance succeeds if otherwise allowed; Renewal quota unchanged.
2. Explicit renewal with exhausted quota fails with correct structured error.
3. Explicit renewal with available quota succeeds and consumes exactly intended renewal amount.
4. Repeated ordinary edits do not decrement Renewal quota.
5. Manual delete and device-limit auto-delete produce equivalent required deleted-user traffic capture.
6. Retry/shared delete path does not duplicate capture.
7. Real Owner exemption works as intended.
8. Legacy/non-Owner `is_sudo=True` remains policy-enforced.
9. Existing tests no longer encode “numeric increase == renewal”.

**Verification:** Stage-specific backend tests + adjacent policy/device-limit regression. MySQL-specific checks only where relevant; otherwise `NOT EXECUTED`.

---

## Stage 2 — Admin Resource Ledger, Credit Editing, Renewal Management

**Scope:** BUG-05, BUG-06, R-RES-01..03.

**Outcome:** Grant/Reclaim-based resource editing; safe initial Admin credit; visible authorized Renewal policy/quota; auditable history.

**Required targeted tests:**

1. `+30 GiB` grant changes balance exactly once + ledger/audit effect.
2. `-30 GiB` reclaim exactly once.
3. Over-reclaim rejected.
4. Parent-funded balance remains consistent.
5. Idempotent duplicate cannot double-grant.
6. Concurrent grant/reclaim cannot create invalid balance.
7. New Admin initial credit uses adjustment path.
8. Unauthorized resource adjustment rejected.
9. Renewal quota API/UI authorization correct.

**Verification:** backend DB state before/after + affected UI/API tests; relevant MySQL transaction checks.

---

## Stage 3 — Billing-Mode Foundation

**Scope:** R-MODE-01..04; create explicit persistent `SEAT_CREDIT`, `USED_TRAFFIC`, `ALLOCATED_TRAFFIC` semantics through a coherent strategy/service boundary.

**Blocked by:** none. D-05, D-09, and legacy migration/default are resolved and must be implemented as specified.

**Outcome:**

- explicit mode state and safe migration;
- no guessed legacy commercial model;
- Seat capacity consumable and not restored on expiry;
- Used Traffic incremental accounting basis;
- Allocated Traffic allocation accounting basis;
- persistent immutable Allocated Traffic Refund Requests with authorized approval;
- only approved refund requests create ledger credit; deletion/rejection/cancellation do not;
- mode changes Owner-only and balance-safe.

**Required targeted tests:**

1. migration on representative legacy data;
2. correct strategy selection per mode;
3. Seat consumption not returned on expiry;
4. unchanged Used Traffic reconciliation charges zero;
5. usage increase charges only delta;
6. usage reset/restart cannot create negative/duplicate charge;
7. Allocated create charges once;
8. Allocated increase charges intended delta;
9. no unauthorized automatic refund;
10. mode change cannot silently reinterpret balances.
11. refund request snapshot is immutable and contains every required D-05 field;
12. only authorized parent/Owner can approve or reject;
13. rejection/cancellation changes no credit;
14. approval and ledger credit are atomic and idempotent;
15. concurrent/retried approval creates exactly one credit and one auditable effect.

**Verification:** real disposable MySQL migration/query evidence required for MySQL claims.

---

## Stage 4 — Plan, Inbound, Host, Access-Control Integrity

**Scope:** R-PLAN-01..05, R-NET-02.

**Blocked by:** D-10.

**Outcome:**

- live Inbound selector + backend validation;
- invalid empty Plan rejected according to explicit network rule;
- Plan Host scoping, if required, is first-class and enforced in subscription generation;
- Plan access/subtree controls wired to real authorization;
- Admin network access representable for later restricted creation.

**Required targeted tests:**

1. UI loads live Inbounds;
2. unknown Inbound rejected server-side;
3. invalid empty Plan rejected UI + API;
4. valid Plan creates valid user/proxy state;
5. selected Hosts persist;
6. subscription contains only permitted Hosts;
7. disabled/deleted Host behavior tested;
8. unauthorized Plan access denied;
9. subtree access semantics correct.

### Integration Gate A — mandatory after Stage 4

Run the integrated regression for Stages 1–4 only, not the entire future product:

- renewal/edit accounting;
- deleted-user accounting;
- Owner/sudo authorization;
- resource ledger/renewal management;
- billing-mode persistence/accounting foundation;
- Plan/Inbound/Host/access flow;
- migrations introduced by Stages 1–4 on disposable MySQL.

Gate A must be `PASS` before Stage 5.

---

## Stage 5 — Restricted Creation, Renewal UX, Username Namespace

**Scope:** R-CREATE-01..03, R-NET-01..02, R-USER-01.

**Blocked by:** none; D-01 and D-03 were resolved on 2026-08-22. Preserve the
resolved D-05 contract.

**Outcome:**

- Seat Admin raw builder unavailable/denied; authorized Plan flow works;
- Used/Allocated forms expose only username, volume, time, description;
- network/device fields cannot be injected by API;
- effective network config applied centrally;
- stable unique Admin prefix creates `prefix_requestedusername` for new customer users under finalized scope;
- existing users not mass-renamed.

**Required targeted tests:**

1. Seat raw create denied;
2. authorized Plan create works;
3. Used/Allocated simple create works;
4. injected Inbound/Host/device count rejected/ignored by explicit contract, never honored;
5. generated user receives only authorized network config;
6. prefix generated once/stable;
7. concurrent prefix uniqueness;
8. same requested suffix under two Admins -> distinct usernames;
9. existing users unchanged by migration;
10. renewal obeys same protected-field rules and finalized Seat charging rule.

---

## Stage 6 — Trial/Test System and Trial Cleanup

**Scope:** R-TRIAL-01..04.

**Outcome:** first-class Trial metadata/Plans, per-Admin Trial entitlement, idempotent consumption, safe cleanup preview.

**Required targeted tests:**

1. 1 GiB / 1 day / 1 device;
2. 2 GiB / 1 day / 1 device;
3. Unlimited / 1 day / 1 device when accounting allows;
4. Unlimited / 1 day / 2 devices when accounting allows;
5. exhausted Trial quota error;
6. retry consumes quota once;
7. cleanup preview count;
8. cleanup deletes only Trial records in scope;
9. normal user containing “test” in name/note is not misclassified;
10. deleted-user accounting preserved.

If Unlimited Trial can bypass finite accounting and no safe policy exists, that scenario is `BLOCKED`.

---

## Stage 7 — Hierarchy Delegation, Referral, Freeze

**Scope:** R-HIER-01..02, R-REF-01..02, R-FREEZE-01..02.

**Blocked by:** none after resolved D-02/D-04. Referral remains attribution-only and
creates no reward; Freeze covers the full descendant subtree with provenance-safe
restoration.

**Outcome:** bounded transactional sub-admin delegation; referral config separate from parent hierarchy and Owner-only; reversible auditable freeze with support warning.

**Required targeted tests:**

1. valid delegation debits parent/credits child once;
2. over-delegation rejected;
3. concurrent delegation cannot double-spend;
4. child cannot receive inaccessible Plan/network/permission;
5. non-Owner cannot modify referral config;
6. frozen Admin with existing session/token cannot perform protected actions;
7. user-state freeze effect correct;
8. unfreeze restores only freeze-caused state;
9. freeze/unfreeze audit exists;
10. finalized cascade behavior correct.

---

## Stage 8 — Bulk Admin and Bulk User Actions

**Scope:** R-BULK-01..02 and reuse Trial cleanup infrastructure rather than duplicating it.

**Blocked by:** none after resolved D-06/D-07. Preserve explicit target snapshots and
bounded per-target transactional execution exactly as specified above.

**Outcome:** preview/count, explicit batch semantics, idempotency/correlation ID, correct per-mode accounting, auditable results. Telegram outbox hooks may be prepared without requiring live Telegram.

**Required targeted tests:**

1. correct target selection;
2. no unauthorized cross-scope targets;
3. idempotent retry;
4. partial failure matches finalized contract;
5. bulk volume change does not accidentally consume Renewal quota;
6. accounting effects differ correctly by billing mode;
7. representative bounded batch has no obvious N+1/excessive transaction behavior.

---

## Stage 9 — Admin Create/Manage UX and Professional Dashboard

**Scope:** R-UX-01..02 plus useful existing backend capabilities.

**Outcome:**

- simpler mode-aware Admin creation;
- phone required for new Admins;
- Discord removed from intended UI without unsafe legacy schema deletion;
- network section clear;
- resource changes via Grant/Reclaim;
- Trial/Renewal controls where relevant;
- freeze/sub-admin/referral controls only for authorized roles;
- professional dashboard with week-over-week + mode-specific metrics.

Audit whether useful UI is missing for existing capabilities such as Renewal Policy, User Creation Mode, plan management permission, API tokens, suspend/resume, reparent, credit ledger, hierarchy/bulk controls. Do not expose every backend endpoint just because it exists.

**Required targeted tests:**

1. create Admin happy path per billing mode;
2. new Admin phone required;
3. current working-tree Admin edit/manage flow remains compatible without creating a
   synthetic historical-phone backfill matrix;
4. irrelevant fields hidden by mode;
5. API still validates required fields/permissions;
6. dashboard aggregates numerically correct on seeded data;
7. week-over-week boundary/timezone correctness;
8. bounded query count/no per-card N+1;
9. frozen Admin warning/actions correct.

### Integration Gate B — mandatory after Stage 9

Run integrated regression for Stages 5–9 plus critical dependencies from Stages 1–4:

- all three creation modes;
- network/Plan enforcement;
- renewal and resource accounting;
- username namespace;
- Trial create/quota/cleanup;
- hierarchy/referral authorization/freeze;
- bulk operations;
- Admin create/manage + dashboard;
- migrations and critical MySQL queries introduced through Stage 9, validated on
  real MySQL 8.x / InnoDB from the current supported schema baselines.

Gate B must be `PASS` before Stage 10.

---

## Stage 10 — Localization, Error Contract, Pagination, Performance

**Scope:** R-I18N-01, R-PAGE-01, BUG-07, BUG-08.

**Outcome:** stable business error codes -> Persian UX; controlled Persian fallback; correct Unlimited rendering; true server pagination 10/25/50 hard max 50; server-side search/filter/sort; measured index/query behavior.

**Required targeted tests:**

1. representative error code -> correct Persian text;
2. unknown error -> controlled Persian fallback with safe diagnostics;
3. Unlimited semantics render correctly;
4. page sizes 10, 25, 50;
5. 500 rejected/clamped by explicit contract with hard max 50;
6. search/filter/sort totals/results correct;
7. query count avoids N+1;
8. payload contains requested page, not entire dataset;
9. ordering stable with unique tie-breaker;
10. representative MySQL `SHOW INDEX` + `EXPLAIN ANALYZE` or `EXPLAIN` + timing;
11. composite indexes justified by real predicates;
12. cursor/keyset only if measured deep-offset/consistency evidence requires it.

---

## Stage 11 — Telegram Logs, 30-Minute Backup, Health, Limit Alerts

**Scope:** R-TG-01..04, R-BOT-01.

**Blocked by:** D-08; D-11 before retention/purge behavior.

**Outcome:** secure config, durable operation notification path, individual traceable operation messages/events, individually traceable backup sends, 30-minute backups, separate generation/delivery health, retries, non-empty/plausibility checks, size/hash when practical, no overlapping jobs, near-limit dedup/hysteresis, legacy-bot parity matrix.

**Required targeted tests:**

1. business operation creates outbox event once;
2. Telegram transient failure retries without duplicating business mutation;
3. successful delivery marks event delivered;
4. secrets absent from logs/API;
5. default backup interval = 30 minutes;
6. backup artifact non-empty/plausible;
7. generation failure -> generation health failure;
8. upload failure -> delivery failure while generation remains accurately represented;
9. retry reuses event/artifact safely;
10. concurrent schedulers do not duplicate same-period backup when lock/lease required;
11. near-limit crossing alerts;
12. repeated checks in same band do not spam;
13. alert recovery/re-arm behavior;
14. legacy sales-bot capability parity matrix.

Real Telegram send/upload is `NOT EXECUTED` unless real credentials/environment are used.

---

## Stage 12 — Fork `Marzban-scripts` and Pin Node Installer

**External action:** execute only with explicit Owner authorization + authenticated GitHub access.

**Outcome:** fork `gozargah/Marzban-scripts`, record upstream sync strategy, verify `marzban-node.sh`, update Owner-facing URL to fork, prefer stable tag/commit pin when practical.

**Evidence:**

1. fork exists under correct account;
2. upstream relationship clear;
3. raw script URL resolves;
4. checksum/content matches intended baseline before custom edits;
5. node install tested in safe disposable environment if available;
6. otherwise real node install = `NOT EXECUTED`.

---

## Stage 13 — Full Regression, Migration Validation, Capability Audit, Release Gate

No new features except regression fixes required to restore intended behavior.

### Full test gate — mandatory

Run the complete relevant suite across all implemented stages:

**Backend/API/security**

- full backend suite;
- MarzHelp/accounting integration;
- resource ledger;
- billing modes;
- Plan/network/access;
- Trial;
- hierarchy/referral/freeze;
- bulk actions;
- authorization negative tests;
- Telegram/outbox/backup integration;
- API integration.

**Frontend**

- typecheck;
- lint if project uses it;
- unit/component tests;
- production build;
- critical create/edit/renew/Admin management flows;
- pagination/search/filter;
- Persian localization smoke;
- freeze UX;
- dashboard metrics.

**MySQL migration**

Use disposable MySQL 8.x / InnoDB. Production DB evidence must cover only relevant
current supported states, not hypothetical historical production populations:

1. fresh/current `v4.9.8` schema through the current project migration chain -> head;
2. project schema head present when Stage 13 starts -> new head;
3. partial-DDL/rerun recovery for MySQL migrations introduced by remaining Stages;
4. verify current transformed/preserved IDs, ownership, accounting, ledger and scope
   data required by actual current dependencies;
5. app starts on upgraded schema and critical reads/writes work;
6. application rollback compatibility is checked where current deployment policy
   requires it; schema downgrade only if safely supported;
7. verify new constraints, indexes and query plans on real MySQL;
8. record lock, backfill, backup/restore and rollback risks.

Do not add PostgreSQL/TimescaleDB tests or broad historical-account migration
matrices. SQLite results may support isolated logic tests but cannot satisfy this
gate.

**Master/Node/Tunnel real environment**

Where available, verify Master, Node, Tunnel/network path, subscription generation, Host/Inbound enforcement, device limit, traffic accounting/reconciliation. Each unavailable scenario is `NOT EXECUTED`.

**Backup/Telegram real environment**

If credentials/environment are available, perform real send/upload and practical restore smoke test in disposable environment. Otherwise report each missing layer separately.

**Graphify final audit**

Rebuild after major changes, compare blast radius/coupling/cycles/hot paths, but do not use graph output as release proof.

### Final capability audit — English only

Cover with severity + evidence status:

- auth/session;
- Owner/Admin/Sub-admin permissions;
- user create/edit/delete/renew;
- Plans/Inbound/Host/subscriptions;
- Nodes/Master/Tunnel;
- device limit;
- traffic/accounting/ledger;
- three billing modes;
- Trial/quota/cleanup;
- freeze/referral/hierarchy;
- bulk actions;
- pagination/search/filter;
- localization/errors;
- dashboard;
- Telegram/backups/alerts;
- legacy-bot parity;
- retained API-token/admin-management capabilities.

### Release conclusion

Do not say “bug-free”. Report:

- verified invariants;
- failed invariants;
- `NOT EXECUTED` items;
- unresolved uncertainty;
- migration/deployment risk;
- rollback prerequisites;
- recommendation: `READY FOR NEXT ENVIRONMENT` or `NOT READY`.

---

## 11. Compact Test Matrix

| Area | Per-stage target | Integration Gate | Final Stage 13 |
|---|---|---|---|
| Renewal / deleted-user / Owner policy | Stage 1 | Gate A | Full |
| Resource ledger / renewal management | Stage 2 | Gate A | Full |
| Billing modes / migrations | Stage 3 | Gate A | Full + real MySQL |
| Plan / Inbound / Host / access | Stage 4 | Gate A | Full + real subscription path if available |
| Restricted creation / namespace | Stage 5 | Gate B | Full |
| Trial | Stage 6 | Gate B | Full |
| Hierarchy / referral / freeze | Stage 7 | Gate B | Full |
| Bulk | Stage 8 | Gate B | Full |
| Admin UX / dashboard | Stage 9 | Gate B | Full |
| Localization / pagination / performance | Stage 10 | targeted | Full + MySQL plans |
| Telegram / backup / alerts | Stage 11 | targeted | Full + real send/restore if available |
| Node installer fork | Stage 12 | external evidence | Final scope dependent |

A successful build does not prove business logic. A unit test does not prove MySQL migration behavior. A mocked Telegram test does not prove live delivery.

---

## 12. Execution Ledger — Compact, Append Only

Do not erase prior Stage evidence. Keep entries concise. Summarize repetitive logs; preserve exact commands/results, decisions, migration IDs, and unresolved risks.

### Pre-V3 baseline

- Implementation Stages under this V3 evidence contract: `NOT EXECUTED` until recorded below.
- Historical checkout: `v4.9.8` / `b45e3af663cd16d6dcca8492a6520b7e39db9d80`, dirty; re-verify.
- Historical concerns: BUG-04 present; local BUG-09/10 fixes; Plan selector partial with empty-Inbound issue; three new billing mode IDs absent.
- V3 changes process only: compact reading protocol, targeted per-Stage tests, Gate A after Stage 4, Gate B after Stage 9, full regression only in Stage 13.

### Entry template

```markdown
### Stage N — <name> — <date/time>
Status: PASS | FAIL | NOT EXECUTED | UNCERTAINTY | BLOCKED

Baseline: <commit>; working tree <clean/dirty>; preserved local changes: <short list>
Scope: <what was actually changed>
Files: <paths + short reason>
Migration: <revision/backfill or none>
Decisions used: <D-xx or none>

Commands:
- `<command>` -> <status>; <counts/duration/important note>

Evidence:
- Invariants PASS: ...
- FAIL: ...
- NOT EXECUTED: ...
- UNCERTAINTY/BLOCKED: ...
- MySQL/query evidence: ...
- Security negative tests: ...

Remaining risks / next prerequisites: ...
Commit/push/deploy: NOT EXECUTED unless explicitly authorized.
```

### Integration Gate entry template

```markdown
### Integration Gate A|B — <date/time>
Status: ...
Covered Stages: ...
Commands: ...
PASS: ...
FAIL: ...
NOT EXECUTED: ...
UNCERTAINTY: ...
```

### Stage 1 — Critical Accounting and Policy Correctness — 2026-08-22
Status: PASS

Baseline: `b45e3af663cd16d6dcca8492a6520b7e39db9d80`; working tree dirty;
preserved local changes: Plan/Inbound UI, device-limit work, Owner-policy fix,
accounting/access tests, generated dashboard files, local docs and Graphify.
Scope: `BUG-04`, `BUG-09`, `BUG-10` only. Numeric deltas no longer infer
renewal; trusted server-side `edit`/`renew` operation intent controls renewal
quota. Telegram template charge and Next Plan activation are explicit renewals.
Device-limit auto-delete uses the shared idempotent delete capture. Only the
`SystemOwner` bypasses policy while hierarchy is enabled; legacy sudo bypass is
retained only in compatibility mode.
Files: `app/utils/marzhelp_policy.py`, `app/db/crud.py`,
`app/telegram/handlers/admin.py`, preserved local `app/device_limit/engine.py`,
tests, this Runbook, roadmap, and legacy archive metadata.
Migration: none. Decisions used: none.

Commands:
- Python command preamble: `$env:SQLALCHEMY_DATABASE_URL='mysql+pymysql://test:test@127.0.0.1/test'; $env:XRAY_EXECUTABLE_PATH='C:\Users\Saji\Desktop\vProject\Marzban\.codex\xray-v26.7.28\xray.exe'; $env:DEBUG='false'; $env:DOCS='false'`.
- `& 'C:\Users\Saji\AppData\Local\Temp\marzban-stage1-venv\Scripts\python.exe' -m pytest -q tests/test_marzhelp_policy.py -k 'ordinary_volume_and_time_edits or explicit_renewal_enforces or conversion_to_unlimited_is_an_ordinary_edit or only_real_owner_is_policy_exempt' --tb=short`
  -> FAIL; `3 failed, 1 passed` in `18.96s`.
- `& 'C:\Users\Saji\AppData\Local\Temp\marzban-stage1-venv\Scripts\python.exe' -m pytest -q tests/test_marzhelp_policy.py -k 'ordinary_volume_and_time_edits or explicit_renewal_enforces or next_plan_activation_is_an_explicit_renewal or conversion_to_unlimited_is_an_ordinary_edit or only_real_owner_is_policy_exempt' --tb=short --disable-warnings`
  -> PASS; `5 passed, 22 deselected` in `10.27s`.
- `& 'C:\Users\Saji\AppData\Local\Temp\marzban-stage1-venv\Scripts\python.exe' -m pytest -q tests/test_marzhelp_policy.py tests/test_device_limit.py tests/test_user_access_scope.py tests/test_user_status_integrity.py --tb=short --disable-warnings`
  -> initial FAIL `1 failed, 77 passed` in `45.49s` because an old test encoded
  numeric increase as renewal; after marking that server-side scenario explicit,
  final PASS `78 passed` in `46.97s`.
- `& 'C:\Users\Saji\AppData\Local\Temp\marzban-stage1-venv\Scripts\python.exe' -m pytest -q tests/test_user_access_scope.py::test_delete_after_usage_reset_and_renewal_preserves_lifetime_and_credit --tb=short --disable-warnings`
  -> PASS; `1 passed` in `8.16s`.
- `$env:PYTHONPYCACHEPREFIX='C:\Users\Saji\AppData\Local\Temp\marzban-stage1-pycache'; & 'C:\Users\Saji\AppData\Local\Temp\marzban-stage1-venv\Scripts\python.exe' -m compileall -q app tests`
  -> PASS.
- `git diff --check` -> PASS.
- `graphify update .` -> PASS; final graph `3744 nodes`, `8894 edges`, `437 communities`.
- `graphify query "Verify Stage 1 final blast radius for trusted user update operation, renewal quota enforcement, next-plan activation, Telegram charge, device-limit delete accounting, and real Owner versus legacy sudo policy. Identify affected callers and tests." --context call --budget 4000`
  -> PASS; policy/CRUD/Telegram/Next Plan/device-limit/tests surfaced.

Evidence:
- Invariants PASS: ordinary volume/time edits preserve Renewal quota; explicit
  renewal rejects exhausted quota with `renewal_quota_exhausted`; available
  quota decrements once; Next Plan is explicit renewal; manual/device-limit
  delete capture is non-refundable and idempotent; real Owner bypass and
  non-Owner sudo enforcement both verified.
- FAIL: none remaining in the executed Stage 1 set.
- NOT EXECUTED: live MySQL, live Telegram, frontend build, full project suite,
  commit, push, tag, release, deploy.
- UNCERTAINTY: six pre-existing inaccessible `.test-*` directories were kept;
  deprecation warnings remain; neither affects the executed Stage 1 assertions.
- MySQL/query evidence: no schema/index/query-shape change; existing indexed
  settings-row lock and conditional quota updates retained. Live MySQL is not
  relevant to this no-migration Stage and was not executed.
- Security negative tests: hierarchy-enabled non-Owner `is_sudo=True` remains
  policy-enforced; client request models cannot select the internal operation intent.

Remaining risks / next prerequisites: Stage 2 requires explicit owner command;
real MySQL/Telegram remain later-environment evidence. Commit/push/deploy: NOT EXECUTED.

### Stage 2 — Admin Resource Ledger, Credit Editing, Renewal Management — 2026-08-22
Status: PASS

Baseline: `b45e3af663cd16d6dcca8492a6520b7e39db9d80` / tag `v4.9.8`;
working tree dirty; all pre-existing local Plan/Inbound, device-limit, Stage 1,
dashboard build, docs, tests and Graphify changes preserved. Remote branch divergence
remained `0/0`. Scope: `BUG-05`, `BUG-06`, `R-RES-01..03` only.
Files: `app/{db/models.py,models/admin_hierarchy.py,utils/admin_hierarchy.py,routers/admin.py,routers/admin_hierarchy.py}`;
`app/db/migrations/versions/7d2c6a4e9b10_expand_admin_credit_ledger.py`;
dashboard hierarchy/Admin form/types/localization/auth test utility; Stage 2, API,
migration and MySQL tests; this Runbook and roadmap.
Migration: additive `7d2c6a4e9b10` (`4f9c3a2b1d06 -> 7d2c6a4e9b10`).
Nullable columns preserve rollback-image writes; legacy rows backfill deterministic
`resource`, signed `delta`, and adjusted Admin while unreconstructable historical
before/after snapshots remain `NULL`. Decisions used: none.

Commands:
- Stage 0: `git rev-parse HEAD`, `git status --short --branch`, remotes/tags/upstream,
  `git ls-remote --tags origin`, GitHub/GHCR verification -> PASS for tag
  `v4.9.8@b45e3af...`, upstream `0/0`, GHCR digest
  `sha256:f0fb12952f4120705eb1be24d1f174be7f877023133c1d53c73441f24e683081`;
  GitHub REST retry was rate-limited, with the successful same-session Stage 0
  release verification retained.
- `graphify query "Trace Stage 2 implementation and gaps ..." --context call --budget 5000`
  -> PASS; existing service/router/UI/tests and missing initial-credit/renewal/audit
  semantics surfaced.
- Initial Stage 2 test -> FAIL; `1 failed, 6 passed` in `12.74s`: concurrent SQLite
  reclaims created two ledger rows with one effective decrement. Fixed with ordered
  wallet locks plus transactional compare-and-swap.
- `python -m pytest -q tests/test_stage2_resource_ledger.py ...` -> PASS;
  final Stage 2 file `6 passed` in `16.14s`; API/UI authorization contract included.
- Migration rerun/backfill target -> PASS; `1 passed, 6 deselected` in `7.66s`.
- First live MySQL run -> FAIL before Stage 2 migration on legacy TLS certificate
  generation: `OverflowError: integer 3153600000 does not fit '32-bit int'`.
  A test-only pyOpenSSL Windows cap was added; application behavior was not changed.
- `TEST_MYSQL_DATABASE_URL=mysql+pymysql://root@127.0.0.1:33079/stage2_marzban_test ... pytest -q tests/test_mysql_admin_hierarchy_migration.py`
  -> PASS; `1 passed` in `36.45s` on portable MySQL/InnoDB `8.0.43`.
- Final targeted + adjacent backend/DB suite -> PASS; `90 passed` in `80.11s`.
- `npm run test:admin-hierarchy` -> PASS; Owner/direct-parent allowed, outsider/self
  denied. `npm run build` -> PASS; TypeScript + Vite, `1749 modules transformed`;
  existing vendor chunk-size warning remains.
- `python -m compileall -q app tests` -> PASS; `git diff --check` -> PASS.
- `EXPLAIN ... WHERE adjusted_admin_id=202 ORDER BY created_at DESC,id DESC LIMIT 50`
  -> `ix_admin_credit_adjusted_created`, `Backward index scan`; transaction rollback
  left `0` test ledger rows.
- `graphify update .` -> PASS; `3780 nodes`, `9027 edges`, `441 communities`.
  Final Stage 2 blast-radius query -> PASS.

Evidence:
- Invariants PASS: `+30 GiB` Grant and `-30 GiB` Reclaim each change target and
  parent-funded delegated balance once; over-reclaim and unauthorized sibling are
  rejected; duplicate idempotency produces one ledger and one audit; audit failure
  rolls back balance and ledger; concurrent reclaims cannot create negative or
  unfunded balance; initial Admin credit produces a parent-funded Grant; Renewal
  policy resets and exposes quota only to Owner/direct parent.
- Ledger evidence PASS: new rows store resource, signed delta, target Admin,
  target before/after, parent delegated before/after, actor, reason, timestamp and
  idempotency key. Audit stores the same effect in the business transaction.
- MySQL/query evidence PASS: fresh-to-head, legacy-to-head, partial/rerun migration,
  InnoDB concurrency and target-history index were executed on MySQL `8.0.43`.
  Test DB ended at head `7d2c6a4e9b10`, Admin IDs `101,202` preserved, Admin count
  `2 -> 2`, ledger count `0 -> 0` for the legacy scenario. No production DB was touched.
- Migration operations: backup/checksum/restore `N/A` because the database was a
  new isolated disposable test DB under local `%TEMP%`; real deployment backup and
  restore verification remain a release-gate requirement. Application rollback is
  compatible because additions are nullable and old columns/contracts remain.
- FAIL: none remaining in the executed Stage 2 set.
- NOT EXECUTED: authenticated browser visual pass at `375/768/1024/1440`, full
  repository suite, production/staging database migration, commit, push, tag,
  release, deploy.
- UNCERTAINTY: six pre-existing inaccessible `.test-*` directories were kept;
  existing Vite vendor chunk warning and deprecation warnings remain. No Stage 2
  invariant depends on them.

Remaining risks / next prerequisites: Stage 3 is blocked by `D-05`, `D-09`, and
the safe legacy billing-mode migration/default. Stop after Stage 2.
Commit/push/tag/release/deploy: NOT EXECUTED.

---

### Stage 3 — Billing-Mode Foundation — 2026-08-22
Status: BLOCKED

Baseline: `b45e3af663cd16d6dcca8492a6520b7e39db9d80` / tag `v4.9.8`;
Stage 2 prerequisite is recorded `PASS`; working tree remained dirty and all local
changes were preserved. Scope checked: `R-MODE-01..04`. No source, schema,
migration, test, or application-behavior change was made.

Commands/evidence:
- Stage 0 repository/remote verification -> PASS: canonical root
  `C:/Users/Saji/Desktop/vProject/Marzban`, branch
  `agent/admin-hierarchy-v4.9.0`, upstream divergence `0/0`, immutable remote tag
  `v4.9.8@b45e3af663cd16d6dcca8492a6520b7e39db9d80`, GitHub Latest Release
  `v4.9.8`, GHCR digest
  `sha256:f0fb12952f4120705eb1be24d1f174be7f877023133c1d53c73441f24e683081`.
- `graphify query "Trace Stage 3 billing-mode foundation ..." --context call --budget 5000`
  -> PASS; existing legacy settings, policy/accounting paths, ledger, device-limit,
  migrations, and tests were surfaced.
- Source evidence: current policy persists legacy
  `calculate_volume=used_traffic/created_traffic`; current capacity helper treats
  `concurrent_user_limit=None` as weight `1`; no explicit persistent
  `SEAT_CREDIT`, `USED_TRAFFIC`, or `ALLOCATED_TRAFFIC` state was established as
  the new commercial contract. Historical behavior is not sufficient authority to
  choose the new contract or reinterpret legacy balances.
- PASS: Stage 0 read-only checks and blocker detection.
- BLOCKED: `D-05` (Allocated-credit refund/reclaim semantics) and `D-09` (finite
  Seat cost for a Plan with unlimited/no device limit) remain unresolved. Safe
  legacy billing-mode migration/default also requires evidence or an explicit Owner
  decision; the existing combined legacy fields do not uniquely identify the new
  billing mode.
- NOT EXECUTED: Stage 3 implementation, migration, targeted/adjacent tests, live
  MySQL migration/query verification, Graphify update, commit, push, tag, release,
  deploy.
- UNCERTAINTY: six pre-existing inaccessible `.test-*` directories were kept;
  their contents were not used to resolve the commercial decisions.

Next prerequisite: Owner must explicitly resolve `D-05`, `D-09`, and confirm a
safe legacy migration/default rule. Repeat Stage 0, then resume Stage 3 only.
Commit/push/tag/release/deploy: NOT EXECUTED.

---

### Stage 4 — Plan, Inbound, Host, Access-Control Integrity — 2026-08-22
Status: BLOCKED

Baseline: `b45e3af663cd16d6dcca8492a6520b7e39db9d80` / tag `v4.9.8`;
working tree remained dirty and all local changes were preserved. Scope checked:
`R-PLAN-01..05`, `R-NET-02`. No source, UI, schema, migration, test, or
application-behavior change was made.

Commands/evidence:
- Stage 0 repository/remote verification -> PASS: canonical root
  `C:/Users/Saji/Desktop/vProject/Marzban`, branch
  `agent/admin-hierarchy-v4.9.0`, upstream divergence `0/0`, immutable remote tag
  `v4.9.8@b45e3af663cd16d6dcca8492a6520b7e39db9d80`, GitHub Latest Release
  `v4.9.8`, GHCR digest
  `sha256:f0fb12952f4120705eb1be24d1f174be7f877023133c1d53c73441f24e683081`.
- `graphify query "plan inbound host access subscription permission network scope" --context call --budget 3000`
  -> PASS; existing Plan UI utility, Host dialog, inbound permissions, backend
  access filters, subscription paths, and adjacent tests were surfaced read-only.
- PASS: Stage 0 read-only checks and blocker detection.
- BLOCKED: the hard prerequisite is `Stage 3 PASS`, but the latest Ledger entry is
  `Stage 3 = BLOCKED`. `D-10` is also unresolved: empty allowed Inbound/Host must
  be rejected, explicitly inherited/defaulted, or handled by another controlled
  Owner-approved rule; it may never silently mean all.
- NOT EXECUTED: Stage 4 implementation, frontend work, migration,
  targeted/adjacent tests, browser/typecheck/build, live subscription validation,
  Graphify update, commit, push, tag, release, deploy.
- UNCERTAINTY: six pre-existing inaccessible `.test-*` directories were kept;
  their contents were not used for blocker resolution.

Next prerequisite: resolve Stage 3 decisions and record Stage 3 `PASS`, then resolve
`D-10`. Repeat Stage 0 before resuming Stage 4.
Commit/push/tag/release/deploy: NOT EXECUTED.

---

### Decision D-05 — Allocated Traffic Refund Request — 2026-08-22
Status: RESOLVED; implementation NOT EXECUTED

Owner decision: `ALLOCATED_TRAFFIC` never auto-refunds on delete, expiry, or quota
reduction. Refund requires a persistent request routed to the authorized parent
Admin or Owner, with the immutable snapshot and exact status/approval/ledger/audit
contract recorded in Section 8. User deletion and refund approval remain separate;
only approval may create credit. Authorization, idempotency, transaction atomicity,
concurrency protection, immutable history, and audit trail are mandatory.

Remaining Stage 3 blockers: `D-09` and safe legacy billing-mode migration/default.
Source/schema/tests/commit/push/tag/release/deploy: NOT EXECUTED.

---

### Stage 3 — Billing-Mode Foundation — 2026-08-22 (resumed implementation)
Status: PASS

Baseline and scope: `b45e3af663cd16d6dcca8492a6520b7e39db9d80`, branch
`agent/admin-hierarchy-v4.9.0`, immutable tag `v4.9.8`; only
`R-MODE-01..04`, resolved `D-05`, resolved `D-09`, and the confirmed legacy
migration contract were implemented. Existing dirty work and six inaccessible
`.test-*` directories were preserved. Stage 4 was not started.

Implemented:

- Added explicit persistent `LEGACY_COMPAT`, `SEAT_CREDIT`, `USED_TRAFFIC`, and
  `ALLOCATED_TRAFFIC` strategy selection. Existing rows are backfilled only to
  `LEGACY_COMPAT`; old counters and `calculate_volume` behavior are preserved.
- Owner-only, idempotent billing-mode assignment rejects transitions that would
  reinterpret existing users or economic state.
- `SEAT_CREDIT` rejects a Plan without an explicit finite positive
  device/concurrency count. Seat cost is exactly that count; reduction, deletion,
  and expiry do not restore consumed Seat Credit. `D-01` remains unresolved for
  Stage 5, so Seat renewal is explicitly rejected instead of guessing a charge.
- `USED_TRAFFIC` derives spend from current, reset, and deleted lifetime usage;
  unchanged reads/reconciliation add zero and reset does not create a negative or
  duplicate charge.
- `ALLOCATED_TRAFFIC` charges create allocation, positive update delta, and the
  defined renewal allocation; reduction, deletion, and expiry never auto-refund.
- Added persistent Refund Request and append-only event history with the complete
  D-05 immutable snapshot, `PENDING/APPROVED/REJECTED/CANCELLED`, authorized
  parent/Owner decisions, optional explanations, scoped cursor listing, correlation
  IDs, idempotency keys, row locks, and approval-only ledger credit. Reject/cancel
  create no credit; concurrent approvals create one credit and one approval event.

Database/migration evidence:

- Source Alembic head `7d2c6a4e9b10`; target head `8c4d7e9f2a31`.
- Engine: disposable MySQL/InnoDB `8.0.43` on `127.0.0.1:3308`.
- Fresh-to-head, representative legacy-to-head, partial-DDL recovery, and migration
  rerun: PASS. Existing Admin IDs, User ownership, legacy balances, and old columns
  were preserved by the additive expand/backfill migration. Legacy rows were
  verified as `LEGACY_COMPAT` without counter conversion.
- Live final query evidence: Alembic head `8c4d7e9f2a31`; billing rows
  `ALLOCATED_TRAFFIC=1`, `LEGACY_COMPAT=1`; Refund Requests=`1`, events=`2`,
  approved-refund ledger rows=`1`. Reviewer/status/time/id, requester/time/id,
  correlation, idempotency, and ledger uniqueness indexes were present.
- Backup/restore: NOT EXECUTED because the database was newly created and disposable;
  production/staging migration and rollout remain release-gate work. Old application
  compatibility risk is low because the migration only adds one nullable/defaulted
  column and new tables; no old column was dropped, renamed, narrowed, or repurposed.

Commands/tests:

- Targeted SQLite/adjacent: `54 passed, 1 skipped, 314 warnings`.
- Real MySQL migration plus concurrent approval: `2 passed, 70 warnings`.
- Full backend regression: `150 passed, 3 skipped, 803 warnings`.
- `python -m compileall -q app tests`: PASS.
- `git diff --check`: PASS; only pre-existing line-ending warnings were reported.
- `graphify update .`: PASS; `3869 nodes`, `9331 edges`, `441 communities`.
- FAIL: none in the executed Stage 3 set.
- NOT EXECUTED: frontend/browser tests because Stage 3 made no frontend changes;
  production/staging migration, backup/restore, commit, push, tag, release, publish,
  and deploy.
- UNCERTAINTY: six pre-existing inaccessible `.test-*` directories remain kept;
  existing deprecation warnings remain. GitHub REST preflight returned
  `403 Forbidden`; immutable remote tag and GHCR digest were verified separately in
  the same Stage 0 session.

Database performance review used Graphify, the MySQL workflow, and SQL optimization:
the new request/history tables are append-oriented and bounded list queries use
keyset `before_id` pagination with composite reviewer/requester indexes. Approval
locks one request and one account settings row, preventing duplicate credit while
keeping transaction scope small. No destructive migration or unbounded refund query
was added.

Next prerequisite: stop. Wait for explicit authorization; Stage 4 also requires
Owner resolution of `D-10`.
Commit/push/tag/release/publish/deploy: NOT EXECUTED.

---

### Stage 4 — Plan, Inbound, Host, Access-Control Integrity — 2026-08-22 (new start)
Status: BLOCKED

Stage 3 prerequisite is now `PASS`. Stage 0 read-only verification preserved the
dirty working tree and confirmed canonical root
`C:/Users/Saji/Desktop/vProject/Marzban`, branch
`agent/admin-hierarchy-v4.9.0`, HEAD
`b45e3af663cd16d6dcca8492a6520b7e39db9d80`, upstream divergence `0/0`, remote
tag `v4.9.8` peeled to the same commit, and GHCR digest
`sha256:f0fb12952f4120705eb1be24d1f174be7f877023133c1d53c73441f24e683081`.
GitHub Latest Release REST returned `403 Forbidden`; no release-sensitive state was
changed.

Read-only Graphify/source evidence:

- `PlanVersionInput.inbounds` defaults to an empty list and backend validation
  rejects unknown/unauthorized tags but does not reject an empty selection.
- `_plan_user_payload()` derives proxies exclusively from persisted Plan Inbounds;
  an empty selection can therefore produce empty proxy/inbound state.
- The dashboard already loads live Inbounds and preserves missing historical tags,
  but its current validation permits an empty selection.
- Plan access and optional subtree propagation already have SQL-scoped authorization
  paths that can be tested after D-10 is resolved.
- Hosts belong to runtime Inbounds; no first-class Plan-to-Host persistence model
  exists. Empty Host selection could mean reject, snapshot the current controlled
  defaults, or dynamically inherit future runtime Hosts. These choices have
  materially different subscription and security behavior.

BLOCKED: unresolved `D-10`. The Runbook forbids guessing whether empty allowed
Inbound/Host means rejection, explicit snapshot/default, or controlled inheritance;
it may never silently mean all.

PASS: Stage 0 root/HEAD/upstream/remote tag/GHCR/diff check and read-only Graphify
impact analysis. FAIL: none. NOT EXECUTED: Stage 4 source/schema/UI changes,
targeted tests, Integration Gate A, MySQL migration tests, browser validation,
commit, push, tag, release, publish, and deploy. UNCERTAINTY: six pre-existing
inaccessible `.test-*` directories remain preserved; GitHub Latest API remained
rate-limited.

Next prerequisite: Owner resolves D-10 explicitly. Repeat Stage 0 and resume Stage 4
only. GitHub publication remains prohibited.

---

### Stage 5 — Restricted Creation, Renewal UX, Username Namespace — 2026-08-22 (start)
Status: BLOCKED

Stage 0 read-only preflight confirmed canonical root
`C:/Users/Saji/Desktop/vProject/Marzban`, branch
`agent/admin-hierarchy-v4.9.0`, HEAD
`b45e3af663cd16d6dcca8492a6520b7e39db9d80`, upstream divergence `0/0`, remote
tag `v4.9.8` peeled to the same commit, GitHub Latest Release `v4.9.8`, and GHCR
digest `sha256:f0fb12952f4120705eb1be24d1f174be7f877023133c1d53c73441f24e683081`.
The dirty working tree and all existing local work were preserved.

Hard prerequisite evaluation:

- Stage 3: `PASS`.
- Stage 4: `BLOCKED` before implementation because `D-10` is unresolved.
- Integration Gate A: `NOT EXECUTED`.
- `D-01`: unresolved Seat renewal charging rule; current code deliberately rejects
  Seat renewal with `seat_renewal_policy_unresolved` instead of guessing.
- `D-03`: unresolved username-prefix scope across non-Owner customer users,
  Owner-created users, and Admin login usernames.
- Resolved `D-05`: preserved unchanged; delete/expiry/reduction never auto-refunds
  `ALLOCATED_TRAFFIC`, and only approved persistent Refund Requests create credit.

Read-only Graphify/source impact analysis found the Stage 5 paths through
`create_user_from_plan()`, `renew_user_from_plan()`, raw user creation, billing
strategies, dashboard forms, and existing legacy template username-prefix behavior.
Implementing restricted creation before Stage 4 would bind user creation to an
unresolved Plan/Inbound/Host contract. Implementing renewal or namespace behavior
would also guess `D-01` or `D-03`. The Runbook prohibits all three guesses.

PASS: Stage 0 root/HEAD/upstream/remote tag/GitHub Latest/GHCR/diff check and
read-only Graphify impact analysis. FAIL: none. NOT EXECUTED: Stage 5 source,
schema, migration, UI, targeted tests, Integration Gate A, browser validation,
MySQL tests, commit, push, tag, release, publish, and deploy. UNCERTAINTY: six
pre-existing inaccessible `.test-*` directories remain preserved. BLOCKED: Stage 4,
Gate A, `D-01`, and `D-03`.

Next prerequisite: Owner resolves `D-10`; resume and complete Stage 4, then run
Integration Gate A. After `D-01` and `D-03` are explicitly resolved, repeat Stage 0
and resume Stage 5 only. GitHub publication remains prohibited.

---

### Stage 4 — Plan, Inbound, Host, Access-Control Integrity — 2026-08-22 (completed)
Status: PASS

Scope and baseline: only Stage 4 and confirmed `D-10 = Option 1` were implemented
on branch `agent/admin-hierarchy-v4.9.0`; HEAD remained
`b45e3af663cd16d6dcca8492a6520b7e39db9d80`. Existing dirty work was preserved.
Stage 5 was not started.

Implemented:

- Every new Plan version now requires at least one explicit allowed Inbound and at
  least one explicit eligible active Host for every selected Inbound. Empty never
  means all. Missing, disabled, deleted, blank-address, unavailable, mismatched, or
  Admin-out-of-scope network objects fail closed.
- Added immutable version-scoped Host selections in
  `admin_user_plan_hosts`. Host IDs are retained as selection evidence even if a
  runtime Host is later removed; runtime validation then fails closed.
- Plan create/update and subtree access propagation validate that the effective Plan
  scope does not exceed the actor or target Admin network scope. Host checks are
  batched to avoid per-Host queries.
- Actual Plan user creation and renewal revalidate current Admin/Inbound/Host scope
  and apply exactly the versioned Inbounds. Subscription generation also revalidates
  the latest assignment and emits links only for the explicitly selected Hosts.
- The Plan API exposes only eligible scoped Inbound/Host options and does not expose
  Host addresses. List serialization is batched; the measured query count remained
  four for three Plans instead of scaling per Plan.
- The dashboard now provides explicit nested Inbound/Host checkboxes, preserves and
  labels stale historical selections for repair, blocks incomplete scope locally,
  and sends the explicit Host map to the API. No snapshot default or dynamic
  inheritance was introduced.

Database/migration evidence:

- Source Alembic head `8c4d7e9f2a31`; target head `9f6a2c8d4e10`.
- Additive, rerunnable migration creates only `admin_user_plan_hosts` with composite
  primary key `(version_id, inbound_tag, host_id)` and an InnoDB foreign key from
  `version_id` to the immutable Plan version.
- Disposable MySQL/InnoDB `8.0.43` on `127.0.0.1:3308` passed fresh, legacy,
  partial-DDL recovery, and rerun coverage. Live `alembic_version` was
  `9f6a2c8d4e10` and the new table used InnoDB/utf8mb4.
- Legacy Plan versions are deliberately not assigned inferred Hosts. A legacy
  version without explicit Host rows fails closed until an authorized Admin creates
  a new explicit version. This avoids silently widening network access.
- `EXPLAIN` used the composite primary key for Plan Host lookup (`type=ref`,
  `Using index`) and `ix_user_plan_assignments_user_created` with backward index scan
  for latest assignment lookup.
- Backup/restore was NOT EXECUTED because the database was newly created and
  disposable. Staging/production migration and rollback-application validation
  remain release-gate work.

Executed evidence:

- Stage 4 targeted plus hierarchy adjacent tests: `17 passed, 226 warnings`.
- Integration Gate A: `124 passed, 801 warnings in 115.04s`.
- Full backend regression after final changes: `160 passed, 851 warnings in 124.73s`.
- Real MySQL migration suite: `1 passed, 60 warnings`.
- Dashboard selection test: `plan inbound selection: 14 assertions passed`.
- TypeScript check: PASS. Vite production build: PASS (`1749 modules transformed`).
- `python -m compileall -q app tests`: PASS.
- `git diff --check`: PASS; only pre-existing line-ending warnings were emitted.
- `graphify update .`: PASS; `3916 nodes`, `9517 edges`, `446 communities`.
  Follow-up query resolved `AdminUserPlanHost`, `subscription_host_scope()` and
  `get_plan_network_options()` from the updated graph.
- Standalone `alembic heads`: FAIL in this workstation environment because importing
  a historical migration requires the absent Xray executable. This did not replace
  the real migration test: the full chain ran against MySQL and the database head was
  queried directly as `9f6a2c8d4e10`.
- Browser/live Core/Node/Tunnel and staging/production rollout: NOT EXECUTED.
- UNCERTAINTY: the existing deprecation warnings and six pre-existing inaccessible
  `.test-*` directories remain preserved. No claim is made about unexecuted live
  infrastructure paths.

Database performance review used Graphify, the MySQL workflow, and SQL optimization.
The new lookup is index-backed, selected Hosts are loaded in one bounded query, Plan
responses are batch-loaded, and subscription assignment lookup uses the existing
composite index. No unbounded list, per-row Host query, destructive migration, or
network-scope fallback was added.

Next prerequisite: stop. Stage 5 remains unstarted and additionally requires the
Runbook's unresolved `D-01` and `D-03` decisions before implementation.
Commit/push/tag/release/publish/deploy: NOT EXECUTED.

---

### Stage 5 — Restricted Creation, Renewal UX, Username Namespace — 2026-08-23
Status: PASS

Baseline: `b45e3af663cd16d6dcca8492a6520b7e39db9d80`; branch
`agent/admin-hierarchy-v4.9.0`; working tree remained dirty and all pre-existing
local work was preserved. HEAD and upstream divergence remained unchanged (`0 0`).

Scope: implemented resolved `D-01` and `D-03` only. `SEAT_CREDIT` creation and
Plan renewal consume the Plan's explicit finite positive concurrency count;
expiry/deletion do not restore Seat Credit. Plan renewal uses one transaction,
row locks, an idempotent assignment, and one unique accounting operation. Raw
Seat creation and non-Plan Seat renewal paths fail closed. Used/Allocated raw
creation accepts only username, traffic, expiry and note; network/device/status
fields are server-derived and protected from injection. Every new customer User
created by Owner, Super Admin, Admin or Sub-admin receives the creator's stable
persisted namespace as `prefix_requested_username`; Admin login usernames and
existing customer usernames are unchanged.

Files: `app/db/models.py`, `app/db/crud.py`,
`app/db/migrations/versions/3a7e5c1b8d42_add_admin_user_namespace.py`,
`app/utils/marzhelp_policy.py`, `app/utils/admin_plans.py`,
`app/routers/user.py`, `app/routers/admin_hierarchy.py`,
`app/models/admin_hierarchy.py`, `app/telegram/handlers/admin.py`, and dashboard
account/create-user types and components. Stage 5 tests were added in
`tests/test_stage5_restricted_creation_namespace.py`; migration, MySQL and adjacent
assertions were extended only where the finalized namespace changed expected names.

Migration: Alembic `3a7e5c1b8d42` after `9f6a2c8d4e10`; additive nullable
`admins.user_namespace_prefix VARCHAR(16)`, deterministic legacy Admin backfill,
and unique index `uq_admins_user_namespace_prefix`. The migration is rerunnable
after partial DDL and never updates the `users` table. Runtime generation locks the
Admin row and the unique index remains the concurrency authority.

Executed evidence:

- Stage 5 targeted + migration: `18 passed, 125 warnings in 18.60s`.
- Adjacent Stage 3/4, hierarchy, policy, device and access regression:
  `101 passed, 1 skipped, 635 warnings in 49.25s`.
- Full backend regression: `167 passed, 3 skipped, 902 warnings in 83.29s`.
- Disposable MySQL/InnoDB `8.0.43` fresh/legacy/partial-DDL/rerun and concurrent
  Seat-renewal idempotency: `1 passed, 66 warnings in 39.33s`.
- MySQL concurrent renewal used two workers with one idempotency key: exactly one
  `plan_renew_seat` row and one two-Seat charge survived; the duplicate transaction
  rolled back. Prefix backfill preserved Admin IDs/login names and produced distinct
  values (`u2t6542`, `u5m92f`).
- `SHOW INDEX` confirmed visible unique BTREE
  `uq_admins_user_namespace_prefix`; `EXPLAIN` prefix lookup used `type=const`,
  `rows=1`, `Using index`.
- Dashboard `tsc && vite build`: PASS (`1749 modules transformed`). UI utility
  tests: `14 assertions passed`; hierarchy authorization: `PASS`.
- `python -m compileall -q app tests`: PASS. `git diff --check`: PASS with only
  pre-existing LF/CRLF warnings.
- Graphify incremental extraction/merge produced `3909 nodes` and `9178 edges`,
  but final export was `BLOCKED` by its shrink guard because the authoritative
  graph has `3916 nodes`. No force overwrite was used; the prior `graph.json` was
  preserved. This is `UNCERTAINTY`, not Stage 5 functional-test failure.

Security/invariant evidence: raw Seat create denied; protected inbound/device/status
injection denied; effective network is server-derived; Plan renewal has no protected
client fields; same suffix under distinct creators yields distinct final usernames;
Owner/Super Admin/Admin creator coverage, concurrent prefix creation, stable prefix,
unchanged Admin logins, and unchanged legacy Users all passed.

NOT EXECUTED: browser interaction, live Core/Node/Tunnel, staging/production
migration, backup/restore, commit, push, tag, release, publish and deploy.
UNCERTAINTY: browser/live infrastructure behavior remains unclaimed; existing
deprecation warnings and six inaccessible pre-existing `.test-*` directories were
kept. Graphify requires a later full rebuild or verified shrink before its
incremental result can become authoritative. No Stage 6 work was started.

Database review used Graphify, MySQL and SQL-optimization workflows. Prefix lookup
is unique-index backed; namespace allocation locks one Admin primary-key row; Seat
renewal locks the User/settings rows and writes one bounded ledger row. Operational
risk is limited to the additive backfill/index build on the `admins` table; production
rollout still requires the release gate and backup procedure.

Next prerequisite: stop. Stage 6 may start only after an explicit new instruction.
Commit/push/tag/release/publish/deploy: NOT EXECUTED.

---

### Stage 6 — Trial/Test System and Trial Cleanup — 2026-08-23
Status: PASS

Baseline: `b45e3af663cd16d6dcca8492a6520b7e39db9d80`; branch
`agent/admin-hierarchy-v4.9.0`; upstream divergence remained `0 0`. Stage 0 was
rerun read-only, Stage 5 was confirmed `PASS`, no unresolved Stage 6 decision was
found, and all pre-existing dirty/uncommitted work was preserved. Stage 7 was not
started.

Implemented:

- Plans and immutable user assignments carry first-class `is_trial` metadata.
  Only the actual Owner can create a Trial Plan; Trial status cannot be changed by
  editing a Plan version, and Trial renewal is rejected.
- Every Admin has independent `trial_quota` remaining and `trials_used` counters.
  Owner-only grant/reclaim uses the existing persistent resource ledger with
  authorization, note, before/after values, idempotency key, row locking and
  transaction/concurrency protection.
- Trial creation atomically consumes exactly one Trial entitlement and records the
  immutable assignment. An SQL conditional update prevents two concurrent requests
  from consuming the last quota; retry with one operation key consumes once.
- Trial creation still traverses the active billing mode. `SEAT_CREDIT` requires
  explicit finite device count and Seat Credit, `USED_TRAFFIC` remains usage-based,
  and finite `ALLOCATED_TRAFFIC` rejects unlimited traffic. No unlimited bypass or
  empty-scope fallback was added.
- Cleanup has separate scoped preview and execute endpoints. Classification uses
  immutable assignment metadata, never username/note heuristics. Execution is
  bounded, persistent and idempotent, preserves deleted-user accounting, and keeps
  an operation snapshot/audit trail.
- Dashboard Plan creation exposes an Owner-only Trial control and Trial badge.
  Admin hierarchy shows remaining/used Trial quota with confirmed Owner grant and
  reclaim actions. Trial cleanup previews the count before confirmed deletion and
  reports loading/success/failure. Existing general expired-user cleanup remains
  separate.

Database/migration evidence:

- Additive Alembic head `5b8d1f3a7c64` after `3a7e5c1b8d42` adds Trial metadata,
  counters, the persistent cleanup-operation table, and composite index
  `ix_user_plan_assignments_trial_operation_user`. Legacy rows remain commercial
  (`is_trial=false`) and legacy Admin quota starts fail-closed at zero.
- Disposable MySQL/InnoDB `8.0.43` upgraded through the real chain to
  `5b8d1f3a7c64`; fresh/legacy state, backfill, last-quota concurrency and concurrent
  same-key idempotency passed.
- `SHOW INDEX` confirmed the composite Trial lookup index and `SHOW CREATE TABLE`
  confirmed InnoDB. `EXPLAIN ANALYZE` used the covering Trial assignment index plus
  primary-key User lookup for cleanup candidates.

Executed evidence:

- Stage 6 targeted SQLite/API: `9 passed, 1 deselected in 12.67s`.
- Real MySQL migration/concurrency/idempotency: `1 passed in 23.98s`.
- Adjacent Stage 2–5 billing/network/device/policy/access/API regression:
  `83 passed, 1 skipped`.
- Full backend regression: `176 passed, 4 skipped`.
- Dashboard Plan selection: `14 assertions passed`; hierarchy authorization:
  `PASS`; TypeScript check and Vite production build: `PASS` (`1749 modules`).
- `python -m compileall -q app tests`: PASS. `git diff --check`: PASS with only
  line-ending warnings.
- `graphify update .` without force: PASS; authoritative graph updated to
  `3988 nodes`, `9884 edges`, `436 communities`. The prior shrink-guard uncertainty
  is resolved without deleting or overwriting information by force.

Security/performance review used Graphify, MySQL and SQL-optimization workflows.
Trial quota updates are bounded conditional writes, idempotency is protected by
unique keys and serialized transactions, cleanup is capped at 500 rows, and its
classification query is composite-index backed. No unbounded Trial scan, N+1 Host
lookup, destructive migration or automatic billing refund was introduced.

NOT EXECUTED: browser interaction, live Core/Node/Tunnel, staging/production
migration, backup/restore, commit, push, tag, release, publish and deploy.
UNCERTAINTY: remote tag refresh failed because of workstation TLS; Graphify warned
that 11 source/config files produced zero nodes; existing deprecation warnings and
six inaccessible pre-existing `.test-*` directories remain preserved. None is a
Stage 6 functional blocker, and no live-infrastructure claim is made.

Next prerequisite: stop. Stage 7 remains unstarted and requires a separate explicit
instruction plus its Runbook decisions/prerequisites. No publication action was
performed.

---

### Global scope optimization for Stage 7–13 — 2026-08-23
Status: PASS — documentation/governance only

Owner confirmed no historical production account/settings data exists for this
deployment. Sections 1, Stage 9, Gate B and Stage 13 now require current-baseline
upgrade safety and real MySQL 8.x / InnoDB evidence without speculative production
legacy or cross-database matrices. Future PostgreSQL/TimescaleDB portability is
separated from current implementation; portable SQLAlchemy/Alembic remains preferred
where it does not weaken MySQL correctness. Implemented `LEGACY_COMPAT` and all
Stage 0–6 code/evidence remain unchanged.

Files changed: this Runbook and `docs/ADMIN_HIERARCHY_ROADMAP_FA.md` only. Application,
schema, migrations and tests were not changed. Stage 7 was not started. Verification:
Markdown scope/precedence search and `git diff --check`. Commit/push/tag/release/
deploy/publish: NOT EXECUTED. Blocker: none. Uncertainty: none for this governance
decision; future Stage-specific environment evidence remains to be executed in its
own Stage.

Next prerequisite: stop. Await explicit Stage 7 instruction; then rerun Stage 0 and
resolve Stage 7 decisions `D-02` and `D-04` before implementation.

---

### Stage 7 — Hierarchy Delegation, Referral, Freeze — 2026-08-23 (start)
Status: BLOCKED before implementation

Stage 0 was rerun read-only. Repository root, branch, HEAD, upstream divergence,
dirty worktree, stashes, remote tags, `git diff --check`, Stage 7 card, dependencies,
latest Ledger entries and Graphify impact paths were inspected. Baseline remained
`agent/admin-hierarchy-v4.9.0@b45e3af663cd16d6dcca8492a6520b7e39db9d80`,
upstream divergence `0 0`, and remote `v4.9.8` peeled to the same commit. Existing
local/uncommitted work and six inaccessible `.test-*` directories were preserved.

Prerequisites Stages 2, 3 and 5 are recorded `PASS`. Implementation cannot safely
start because both formal Stage 7 decisions remain unresolved:

- `D-02`: select the referral settlement resource/unit. Traffic credit, Seat Credit,
  another internal resource, or a no-settlement/config-only model are materially
  different accounting contracts. Cash/pricing/payment-wallet UI remains prohibited.
- `D-04`: select freeze scope. Direct Admin/users only versus the entire descendant
  subtree changes authorization, active-session behavior, User state provenance and
  unfreeze restoration.

Graphify query identified existing delegation, suspension, scope and ledger paths in
`app/utils/admin_hierarchy.py`, `app/db/models.py`, `app/utils/billing_service.py`,
`app/utils/marzhelp_policy.py`, the hierarchy API/UI and adjacent tests. No source,
schema, migration, UI or test file was changed. Targeted tests, MySQL evidence and
frontend verification: NOT EXECUTED because implementation is formally blocked.

Commit/push/tag/release/deploy/publish: NOT EXECUTED. Next prerequisite: Owner must
resolve `D-02` and `D-04`; then rerun Stage 0 and resume Stage 7 only. Stage 8 was not
started.

---

### Stage 8 — Bulk Admin and Bulk User Actions — 2026-08-23 (start)
Status: BLOCKED before implementation

Stage 0/prerequisite review was read-only. Root, branch, HEAD, upstream divergence,
dirty worktree, stashes, remote `v4.9.8`, `git diff --check`, current Ledger,
Stage 8 card and Graphify impact paths were inspected. Baseline remained
`agent/admin-hierarchy-v4.9.0@b45e3af663cd16d6dcca8492a6520b7e39db9d80`;
upstream divergence remained `0 0`; remote `v4.9.8` peeled to the same commit. All
pre-existing local/uncommitted work was preserved.

Implementation is blocked for two independent reasons:

1. Hard prerequisite Stage 7 is not `PASS`; its latest Ledger entry is `BLOCKED`
   before implementation on unresolved `D-02` and `D-04`.
2. Stage 8 decisions remain unresolved:
   - `D-06`: inclusion/exclusion and explicit-filter semantics for expired, disabled,
     frozen-admin and Trial users;
   - `D-07`: whole-batch atomicity versus bounded chunk/per-item results, partial
     failure and retry semantics.

Graphify read-only traversal identified Trial cleanup reuse, existing bulk UI,
accounting ledger/idempotency paths and adjacent authorization tests. No source,
schema, migration, query, UI or test file was changed. Targeted/adjacent tests,
MySQL evidence and frontend verification: NOT EXECUTED because the prerequisite and
formal decisions block implementation. SQLite/PostgreSQL/TimescaleDB evidence was
not attempted.

Commit/push/tag/release/deploy/publish: NOT EXECUTED. Next prerequisite: complete
Stage 7 after resolving `D-02`/`D-04`, resolve `D-06`/`D-07`, rerun Stage 0, then
resume Stage 8 only. Stage 9 was not started.

---

### Stage 7 — Hierarchy Delegation, Referral, Freeze — 2026-08-23 (final)
Status: PASS

Stage 0/prerequisite review was repeated. Stages 2, 3 and 5 remained `PASS`; Owner
contracts `D-02` and `D-04` were recorded before implementation. Root, branch and
HEAD remained `agent/admin-hierarchy-v4.9.0@b45e3af663cd16d6dcca8492a6520b7e39db9d80`;
upstream divergence remained `0 0`. All pre-existing local/uncommitted work and
stashes were preserved.

Implemented contracts:

- Referral is a separate Owner-managed attribution record with immutable event
  history, bounded rate metadata, audit and idempotency. It never writes a credit,
  Seat, traffic, financial or other reward ledger entry.
- Owner Freeze always covers target plus every descendant Admin and User. Each
  event snapshots exact pre-freeze Admin account/suspension fields and only Users
  changed from `active`/`on_hold`. Unfreeze restores a row only while that row still
  carries state owned by the same freeze event; independent later changes are kept.
- Freeze/unfreeze and referral mutations use stable idempotency keys, ordered row
  locks, unique constraints, transactions and bounded retry for MySQL error `1213`.
  Existing authenticated sessions are denied protected writes by the existing
  active-account guard once the Admin settings row is frozen.
- Owner-only API and dashboard controls were added. Referral metadata is exposed in
  the hierarchy tree only for Owner view. Freeze actions include full-subtree warning,
  confirmation, loading and success/error feedback.
- Admin deletion now fails closed when immutable referral/freeze history exists.

Schema/migration:

- Additive Alembic head `7c9a2e4f1b65` after `5b8d1f3a7c64` adds
  `admin_referral_attributions`, `admin_referral_events`,
  `admin_suspension_admins`, and freeze idempotency/resolution metadata.
- Real MySQL `8.0.43` / InnoDB evidence covered fresh upgrade, supported current
  Stage 6 schema-to-head upgrade with current row preservation, InnoDB table checks,
  concurrent same-key Owner Freeze, concurrent same-key referral attribution and
  idempotent unfreeze. SQLite was used only as an isolated unit-test harness and is
  not claimed as database evidence.

Executed evidence:

- Stage 7 targeted/API tests: `16 passed, 248 warnings in 10.37s`.
- Adjacent Stage 2–6 accounting, Plan/network, device, namespace, Trial, access and
  migration regression: `72 passed, 2 skipped, 556 warnings in 46.75s`.
- Real MySQL migration/current-data/concurrency test:
  `1 passed, 85 warnings in 58.67s`.
- Isolated real-MySQL Stage 7 downgrade to `5b8d1f3a7c64` and re-upgrade to
  `7c9a2e4f1b65`: PASS; Alembic reported one head, `7c9a2e4f1b65`.
- Dashboard TypeScript and Vite production build: PASS, `1749 modules transformed`;
  hierarchy authorization utility: `PASS`.
- `python -m compileall -q app`: PASS. `git diff --check`: PASS with line-ending
  warnings only.
- `graphify update .` without force: PASS; graph rebuilt to `4031 nodes`,
  `10110 edges`, `446 communities`.

Database performance review used Graphify, MySQL and SQL-optimization workflows.
The observed same-key gap-lock deadlock matters under parallel Owner operations;
both mutation services now isolate the MySQL-specific `1213` check in bounded retry
logic while retaining portable SQLAlchemy transactions and unique-key idempotency.
Ordered primary-key locks bound contention, tree referral/freeze metadata is loaded
in the existing hierarchy query rather than per-node queries, and the constant-query
tree test passed. Expected effect: one durable mutation under retries without
double-application or N+1 growth. Migration risk is additive MySQL non-transactional
DDL; release recovery must use the existing partial-DDL rerun procedure.

NOT EXECUTED: full backend suite, browser interaction, live Core/Node/Tunnel,
staging/production migration, backup/restore, commit, push, tag, release, deploy and
publish. UNCERTAINTY: Graphify retained its warning for 11 zero-node source/config
files; six pre-existing inaccessible `.test-*` directories remain untouched. These
are not Stage 7 functional blockers. No Stage 8 work was started.

Next prerequisite: stop. Stage 8 requires a new explicit instruction plus resolution
of `D-06` and `D-07` before implementation.

---

### Stage 8 — Bulk Admin and Bulk User Actions — 2026-08-23 (resume)
Status: BLOCKED before implementation

The Stage 8 preflight was repeated read-only after the Owner's new instruction.
Stage 7 is now `PASS`, with its recorded targeted, adjacent-regression, real
MySQL/InnoDB, frontend and Graphify evidence. Stage 8 prerequisites from Stages 2,
3, 6 and 7 are therefore satisfied. Repository root remained
`C:/Users/Saji/Desktop/vProject/Marzban`; branch remained
`agent/admin-hierarchy-v4.9.0`; HEAD remained
`b45e3af663cd16d6dcca8492a6520b7e39db9d80`; upstream divergence remained `0 0`;
stash count remained zero; `git diff --check` passed. The dirty working tree and all
pre-existing local/uncommitted work were preserved.

Implementation remains formally blocked by the unresolved Stage 8 contracts:

1. `D-06`: inclusion/exclusion, default selection and explicit-filter behavior for
   expired, disabled, frozen-admin and Trial users;
2. `D-07`: whole-batch atomicity versus bounded chunk/per-item persistence, plus
   partial-failure, resume and idempotent-retry behavior.

Graphify read-only traversal confirmed the existing bulk UI, Trial cleanup,
accounting, authorization and idempotency paths that Stage 8 must reuse. No source,
schema, migration, query, UI or test file was changed. Targeted tests, adjacent
regression, real MySQL evidence and frontend verification are `NOT EXECUTED` because
the Runbook forbids guessing these two contracts. SQLite was not treated as database
evidence; PostgreSQL/TimescaleDB work was not attempted.

Commit, push, tag, release, deploy and publish: `NOT EXECUTED`. Stage 9 was not
started. Next prerequisite: Owner must resolve `D-06` and `D-07`; then repeat the
read-only preflight and resume Stage 8 only.

---

### Stage 8 — Bulk Admin and Bulk User Actions — 2026-08-23 (final)

Status: PASS

The Stage 8 preflight was repeated after the Owner resolved `D-06` and `D-07`.
Stages 2, 3, 6 and 7 remained `PASS`; repository root, branch, HEAD, upstream
divergence and stash count remained unchanged. All pre-existing dirty/uncommitted
work was preserved.

Implementation evidence:

- migration `2e8c4a6f9b17` extends the durable job record and adds immutable
  `admin_bulk_job_targets` snapshots with per-target status, fingerprints, attempts,
  retryability, error/result details and bounded-query indexes;
- User bulk scope is mandatory and server-enforced as `ALL_USERS`,
  `SELECTED_ADMINS_DIRECT` or `SELECTED_ADMINS_SUBTREE`; `ALL_USERS` is Owner-only,
  selected Admins must be within actor scope, deleted Users are absent, and target IDs
  are resolved once in deterministic ID order;
- User and Admin-credit jobs use stable operation IDs, payload-conflict detection,
  bounded target insertion/execution/report pages, one short locked transaction per
  target, MySQL deadlock/lock-timeout retry, durable partial results and retry of only
  incomplete/retryable targets. A successful target cannot be applied twice;
- User volume/day/status/delete actions reuse the existing authorization and
  accounting policies. Bulk volume edit records `renewal_delta=0`; billing-mode
  effects remain distinct. Admin Grant/Reclaim creates one existing credit ledger
  transfer per target;
- dashboard User and hierarchy panels require explicit scope/selection, show the
  server-resolved count before execution, create the persistent job, execute bounded
  chunks and show/retry detailed non-success results. Legacy `/api/users/bulk` now
  fails closed with `bulk_scope_required` after preserving missing/foreign-target
  authorization responses.

Executed evidence:

- Stage 8 targeted plus closest access regression: `33 passed`;
- adjacent billing, Trial, hierarchy and status regression: `81 passed, 2 skipped`;
- real MySQL `8.0.43` / InnoDB: `1 passed` covering upgrade from revision
  `7c9a2e4f1b65`, idempotent partial-DDL rerun, downgrade/re-upgrade, two concurrent
  workers over 20 snapshotted Users, exact-once mutations/ledgers and `EXPLAIN`
  selection of the pending/report indexes;
- frontend hierarchy authorization script: `PASS`; TypeScript plus Vite production
  build: `1749 modules transformed`, exit `0`; Python `compileall`: exit `0`;
- Graphify update: `4146 nodes / 10577 edges / 452 communities`; follow-up query
  found the new model, service, router and MySQL test paths.

Database/performance review used the MySQL and SQL-optimization workflows. The old
single-request bulk path had no durable target snapshot and could not safely resume
at scale. The replacement uses bounded pages/chunks, keyset cursors, target-level
transactions and covering-prefix indexes verified by real MySQL `EXPLAIN`; it avoids
one global transaction and unbounded result responses. The additive MySQL DDL risk is
documented and its rerun plus rollback path executed. PostgreSQL/TimescaleDB work was
not attempted; SQLite results were used only as unit/adjacent harness evidence.

NOT EXECUTED: full backend suite, browser interaction, live Core/Node/Tunnel,
staging/production migration, commit, push, tag, release, deploy and publish.
UNCERTAINTY: Graphify still reports 11 source/config files producing zero nodes; the
update completed without force or data removal and this is not a Stage 8 functional
blocker. Stage 9 was not started.

Next prerequisite: stop. Stage 9 requires a new explicit instruction.

---

### 2026-08-23 — Stage 9 final and Integration Gate B

Status: `PASS` for Stage 9 and `PASS` for Integration Gate B. Stage 10 was not
started.

Implemented evidence:

- new Admin phone is required by the managed-create API/model and UI; the database
  column remains nullable so the current supported schema upgrades safely without a
  hypothetical historical-data backfill;
- managed Admin creation accepts an explicit billing mode, keeps it immutable after
  creation, shows only the relevant initial traffic/Seat Credit resource field, and
  removes Discord from the intended UI without deleting the legacy schema field;
- Grant/Reclaim now moves `device_capacity_limit` and records `seat_credit` for
  `SEAT_CREDIT`, while traffic modes retain `total_traffic`/`traffic_credit`;
- `/api/dashboard/overview` performs authorization-scoped bounded aggregates,
  exposes explicit timezone week boundaries and week-over-week values, and returns
  metrics for all four billing modes; the responsive UI includes text/progress
  alternatives, loading/error/retry and frozen-account warning remains visible;
- migration `6d4f2a9c8e10` adds `admins.phone`,
  `ix_users_created_at_id(created_at,id)` and
  `ix_users_admin_status(admin_id,status)`. Its MySQL rollback restores a supporting
  `admin_id` index before dropping the composite index, preserving the foreign key.

Executed evidence:

- Stage 9 targeted + resource-ledger adjacency: `14 passed`;
- Gate B Stages 1–9 selected integration matrix: `93 passed, 2 skipped` (SQLite was
  used only as a unit/adjacent harness and is not database evidence);
- real MySQL `8.0.43` / InnoDB Stage 9: `1 passed`, fresh current-baseline migration
  through `head`, idempotent migration rerun, downgrade/re-upgrade, schema/index
  inspection, 2,000 seeded Users, aggregate correctness and `EXPLAIN` selection of
  both Stage 9 indexes;
- real MySQL `8.0.43` / InnoDB Gate B hierarchy/bulk migration, locking,
  concurrency, idempotency and query-plan regression: `2 passed`;
- TypeScript + Vite production build: `1750 modules transformed`, exit `0`; Python
  `compileall`: exit `0`; focused `git diff --check`: exit `0` with only line-ending
  warnings;
- Graphify update completed without `--force` or deletion: `4195 nodes / 10733 edges
  / 452 communities`.

Database/performance review used the MySQL and SQL-optimization workflows. The
dashboard query count is bounded and independent of card/User count; the new
composite indexes were selected by real MySQL `EXPLAIN` on the representative seeded
dataset. Additive DDL and rollback were both executed. PostgreSQL/TimescaleDB were
not implemented or tested.

NOT EXECUTED: full repository suite, browser interaction, live Core/Node/Tunnel,
staging/production migration, commit, push, tag, release, deploy and publish.
UNCERTAINTY: two optional harness tests were skipped; Graphify still reports 11
source/config files with zero nodes; six inaccessible `.test-*` directories remain
untouched. None is a Stage 9 or Gate B blocker.

Next prerequisite: stop. Stage 10 requires a new explicit instruction.

---

### 2026-08-23 — Stage 10 final

Status: `PASS` for Stage 10. Stage 11 was not started.

Implemented evidence:

- the Users API now enforces explicit page sizes `10`, `25` and `50`, rejects other
  values and misaligned offsets with stable business error codes, returns page
  metadata, performs search/filter/sort server-side and uses `id` as the unique
  ordering tie-breaker;
- the count query is narrow and eager relationship loading is applied only to the
  bounded result page, preventing per-User N+1 growth;
- frontend preferences and controls expose only `10/25/50`; stale asynchronous
  responses cannot replace the latest requested page; controls retain semantic and
  accessible loading/current-page state;
- centralized frontend error localization maps known business codes to Persian and
  uses a controlled Persian fallback with only safe operation/correlation reference
  diagnostics. Raw backend detail is not displayed. Unlimited remains `نامحدود`;
- migration `1a9e7c3d5b20` adds
  `ix_users_status_created_id(status,created_at,id)` and
  `ix_users_admin_created_id(admin_id,created_at,id)` using additive, portable
  Alembic/SQLAlchemy patterns and no hypothetical data backfill.

Executed evidence:

- Stage 10 targeted and directly adjacent pagination/access/bulk tests:
  `32 passed`;
- adjacent Stage 8/9 hierarchy, policy, bulk and dashboard regression:
  `48 passed`;
- real MySQL `8.0.43` / InnoDB: `1 passed`; fresh migration through `head`, downgrade
  to Stage 9 and re-upgrade, `SHOW INDEX`, 10,000 seeded Users, representative index
  selection, `EXPLAIN ANALYZE` and measured deep-offset timing;
- TypeScript + Vite production build to the served `build` directory:
  `1751 modules transformed`, exit `0`;
- Graphify update completed without `--force` or deletion:
  `4217 nodes / 10795 edges / 455 communities`.

Database/performance review used the MySQL and SQL-optimization workflows. The
detected issue was pagination ordered/filtered without covering composite order
paths plus a count query carrying unnecessary eager-loading structure. At scale this
increases sorting, payload and ORM work. The two measured composite indexes and
narrow count/page split bound the request work; real MySQL selected the relevant
indexes on 10,000 rows. Migration risk is limited to additive index build time and
write amplification. No PostgreSQL/TimescaleDB behavior was implemented or tested.
Cursor pagination was not introduced because the measured Stage 10 dataset did not
require it; the explicit offset contract remains the supported behavior.

NOT EXECUTED: full repository suite, browser interaction, live Core/Node/Tunnel,
staging/production migration, commit, push, tag, release, deploy and publish.
UNCERTAINTY: Vite reports the pre-existing large vendor-chunk warning; Graphify still
reports 11 source/config files producing zero nodes; six inaccessible `.test-*`
directories remain untouched. None is a Stage 10 blocker.

Next prerequisite: stop. Stage 11 requires a new explicit instruction and resolution
of its formal `D-08` and `D-11` blockers.

---

### 2026-08-23 — Stage 11 start

Status: `BLOCKED` before implementation. Stage 10 is `PASS`, but the formal Stage 11
decisions `D-08` and `D-11` remain unresolved.

Read-only evidence:

- canonical root: `C:/Users/Saji/Desktop/vProject/Marzban`;
- branch: `agent/admin-hierarchy-v4.9.0`;
- HEAD and local `v4.9.8` tag: `b45e3af663cd16d6dcca8492a6520b7e39db9d80`;
- upstream divergence: `0/0`; stash list empty; remote tag reference was reachable;
- existing dirty tracked/untracked work was inventoried and left untouched;
- Graphify read-only traversal identified existing Telegram, report, scheduler,
  audit, hierarchy and bulk/accounting integration paths.

Blocking decisions required:

1. `D-08`: backup retention, encryption and key ownership/rotation, destination(s),
   Telegram oversize behavior, RPO, RTO, restore-verification frequency and target,
   and failure escalation destination/timing;
2. `D-11`: retention/archive/purge periods and rules for Telegram outbox and audit
   records, including whether delivered/failed events differ and confirmation that
   resource/accounting ledger evidence is never automatically deleted.

NOT EXECUTED: Stage 11 source/schema/migration changes, targeted tests, adjacent
regression, real MySQL outbox/locking/index evidence, failure/retry tests,
backup/restore tests, live Telegram, Stage 12, commit, push, tag, release, deploy and
publish.

Next prerequisite: Owner resolves `D-08` and `D-11`; then repeat Stage 11 preflight
and resume only Stage 11.

---

### 2026-08-23 — Stage 11 final

Status: `PASS` for Stage 11. Stage 12 was not started. `D-08` and `D-11` are resolved
by the Owner contracts received in the attached instruction.

Implemented evidence:

- migration `4c8e1a7d9b30` adds persistent `telegram_outbox` and
  `backup_artifacts` tables with unique idempotency/period keys and dispatch,
  retention and delivery indexes;
- audit events enqueue in the same business transaction, while Telegram delivery is
  independent; dispatch uses bounded deterministic chunks, InnoDB `SKIP LOCKED`,
  exponential retry, terminal dead-letter and safe error codes;
- delivered outbox retention is 30 days, failed/dead-letter retention is 90 days,
  pending/retrying rows are never purged, and cleanup is bounded;
- MySQL dumps use single-transaction mode, structural/non-empty validation,
  AES-256-GCM authenticated encryption, SHA-256, encrypted local spool and a
  configurable conservative Telegram size limit; plaintext temporary dumps are
  removed;
- backup generation and delivery have separate durable states. Oversize or delivery
  failure preserves the encrypted artifact. Scheduler defaults to 30 minutes and
  uses `max_instances=1`; local delivered files expire after 48 hours except the only
  newest valid backup;
- existing usage/expiry reminder hysteresis and node watchdog remain intact. Legacy
  bot parity is recorded in `docs/STAGE11_LEGACY_BOT_PARITY.md`.

Executed evidence:

- targeted failure/retry/idempotency/encryption/retention tests: `5 passed`;
- adjacent security/accounting/bulk/dashboard/health regression, including targeted
  tests above: `73 passed`;
- real MySQL `8.0.43` / InnoDB: `1 passed`; migration upgrade/downgrade/re-upgrade,
  table/index inspection, `EXPLAIN` dispatch-index selection, two concurrent workers,
  exact-once delivery of 40 events, and authenticated decrypt/apply/verify restore in
  an isolated disposable MySQL schema;
- Python compile and focused diff validation: `PASS`;
- Graphify updated without force or deletion: `4256 nodes / 10915 edges / 467 communities`.

Database review used MySQL and SQL-optimization workflows. Persistent transport state
replaces process-local-only delivery for business audit events. Equality/range/order
dispatch and terminal-retention predicates have separate measured composite indexes.
Transactions are bounded; external Telegram I/O cannot roll back business mutations.
Migration risk is additive table/index creation only. PostgreSQL/TimescaleDB were not
implemented or tested.

NOT EXECUTED: live Telegram message/upload because no real Stage 11 credentials were
provided; production backup/restore; full repository suite; browser interaction;
live Core/Node/Tunnel; Stage 12; commit, push, tag, release, deploy and publish.
UNCERTAINTY: deployment must install a compatible `mysqldump` binary before enabling
the scheduler; live credentials were unavailable. Telegram's official Bot API limit
was verified as 50 MB and the configurable default is conservatively 45 MiB.
Telegram-side retention remains externally managed. These are operational checks,
not failures of the tested local/MySQL contracts.

Next prerequisite: stop. Stage 12 requires separate explicit authorization and is not
started.

---

### 2026-08-23 — Stage 12 start

Status: `BLOCKED` before external action. Stage 11 is `PASS`, but Stage 12 requires
authenticated GitHub access and explicit authorization to create/publish the fork.

Read-only evidence:

- canonical Marzban HEAD remains
  `b45e3af663cd16d6dcca8492a6520b7e39db9d80`, upstream divergence `0/0`;
- upstream `gozargah/Marzban-scripts` is reachable and its current HEAD is
  `24a772d297c7518dae7650b8f106419e73813cda`;
- `gh auth status` reports: `You are not logged into any GitHub hosts.`;
- the requested prohibition on push/publish conflicts with creating and populating a
  GitHub fork, and no destination user/organization was specified.

Required Owner decision: identify the destination GitHub user/organization, complete
secure `gh auth login`, and explicitly authorize only the fork creation and required
Stage 12 push. Tag, release, deploy and unrelated publication remain prohibited.

NOT EXECUTED: fork creation, clone/edit/pin of `marzban-node.sh`, raw fork URL check,
checksum comparison, node installer test, targeted/adjacent tests, Stage 13, commit,
push, tag, release, deploy and publish.

Next prerequisite: resolve the GitHub authorization conflict and authentication, then
repeat Stage 12 preflight and resume only Stage 12.

---

### 2026-08-23 — Stage 12 authorized resume

Status: `BLOCKED` before fork creation. Owner authorization is now explicit and
limited to creating, changing, committing and pushing
`smorad3363/Marzban-scripts`; main Marzban publication remains forbidden.

Fresh executable evidence:

- Stage 11 remains `PASS`;
- upstream `gozargah/Marzban-scripts` is reachable at
  `24a772d297c7518dae7650b8f106419e73813cda`;
- destination `https://github.com/smorad3363/Marzban-scripts.git` returns
  `Repository not found`;
- `gh auth status` reports no authenticated GitHub host;
- `GH_TOKEN_PRESENT=false` and `GITHUB_TOKEN_PRESENT=false`.

BLOCKED: authenticated access to the authorized destination account is unavailable.
No safe external write can be executed. Per the explicit Stage gate, Stage 13 was not
started.

NOT EXECUTED: fork creation, Stage 12 edits/commit/push, installer pin/checksum/test,
Stage 12 targeted/adjacent tests, and every Stage 13 verification. Main Marzban
commit/push/tag/release/deploy/publish and production actions remain not executed.

Next prerequisite: authenticate `gh` as `smorad3363`, then repeat Stage 12. Stage 13
may begin only after Stage 12 receives fresh `PASS` evidence.

---

### 2026-08-23 — Stage 12 final

Status: `PASS`. Stage 11 remained `PASS`, the Owner-authorized external scope was
limited to `smorad3363/Marzban-scripts`, and the main Marzban repository was not
committed, pushed, tagged, released, deployed or published.

Fresh executable evidence:

- authenticated GitHub account: `smorad3363`;
- fork: `https://github.com/smorad3363/Marzban-scripts`, with parent
  `Gozargah/Marzban-scripts` and default branch `master`;
- upstream baseline: `24a772d297c7518dae7650b8f106419e73813cda`;
- fork commit pushed only to the authorized fork:
  `1ef7ad62d2c16e4450f1a0de9678c8a8c883b154`;
- upstream relation: fork is one commit ahead and zero commits behind; local
  `upstream` remains `https://github.com/gozargah/Marzban-scripts.git`;
- stable Owner-facing installer reference:
  `https://raw.githubusercontent.com/smorad3363/Marzban-scripts/1ef7ad62d2c16e4450f1a0de9678c8a8c883b154/marzban-node.sh`;
- pinned raw content and committed Git blob both resolve to
  `c7c1270fc43f015f20963aa19077b63ec567239a`;
- `bash -n marzban-node.sh` passed for both the committed checkout and downloaded
  pinned raw script;
- `pytest tests/test_release_contract.py -q` -> `1 passed`;
- `python -m compileall -q app tests` and `git diff --check` -> `PASS`.

The fork changes route the installer's self-update source to the fork, document an
upstream fetch/fast-forward workflow without force-push, and make release-facing
documentation use the immutable commit pin. A real node install is `NOT EXECUTED`
because no safe disposable Linux/Node target is available in this Windows workspace;
the Stage 12 contract explicitly permits this evidence status.

Stage 13 may now start under its independent final-verification gate.

---

### 2026-08-23 — Stage 13 final verification gate

Status: `PASS` for the executable local/disposable-environment release-readiness
gate. Recommendation: `READY FOR NEXT ENVIRONMENT`, not ready for production
publication until the environment-dependent checks below are executed. No new
feature or application-behavior change was introduced.

Fresh executable evidence:

- backend/API/security/accounting/hierarchy/bulk/Telegram-backup logic:
  `212 passed, 9 skipped` in `115.46s`;
- SQLite full-chain migration was explicitly excluded because the agreed production
  migration contract is MySQL 8/InnoDB only; SQLite remains a unit harness and is
  not database evidence;
- frontend Plan/Inbound selection: `14 assertions passed`;
- frontend hierarchy authorization: `PASS`;
- TypeScript and Vite production build: `1751 modules transformed`, `PASS`;
- MySQL `8.0.43` / InnoDB: six dedicated tests passed, covering fresh/current
  migration through head `4c8e1a7d9b30`, Stage 6-to-current preservation, rerun
  and partial-DDL recovery, hierarchy/freeze/referral and credit concurrency,
  Seat renewal idempotency, bulk exact-once behavior, dashboard and pagination
  indexes/query plans, 2,000/10,000-row performance fixtures, outbox claiming,
  backup encryption and isolated restore;
- disposable DB direct check: `('8.0.43', 'InnoDB', '4c8e1a7d9b30')`;
- release contract: `1 passed`; `compileall` and `git diff --check`: `PASS`;
- Graphify rebuilt without force/delete after creating its own curated backup:
  `4260 nodes / 10919 edges / 461 communities`; critical-path query completed;
- Git integrity: main HEAD remained
  `b45e3af663cd16d6dcca8492a6520b7e39db9d80`, upstream divergence `0/0`,
  staged files `0`, stashes `0`.

Test-harness corrections made during the gate:

1. the obsolete SQLite full migration test is explicitly skipped under the global
   MySQL-only production migration rule;
2. the MySQL device partial-DDL test uses the same bounded OpenSSL certificate-time
   monkeypatch already used by the hierarchy migration test, avoiding a Windows
   32-bit FFI overflow without changing application behavior.

#### Final capability audit (English only)

| Capability | Severity | Evidence status |
|---|---:|---|
| Auth/session and retained API-token administration | Critical | `PASS` — full backend authorization and token tests |
| Owner/Admin/Sub-admin permissions | Critical | `PASS` — hierarchy/API negative tests and MySQL hierarchy gate |
| User create/edit/delete/renew | Critical | `PASS` — backend regression, accounting and status-integrity tests |
| Plans/Inbound/Host/subscriptions | Critical | `PASS` in API/unit integration; live network path `NOT EXECUTED` |
| Nodes/Master/Tunnel | Critical | `NOT EXECUTED` — no Core binary, Node or Tunnel environment |
| Device limit | High | `PASS` in regression and MySQL partial-DDL recovery; live Core signals `NOT EXECUTED` |
| Traffic/accounting/ledger and three billing modes | Critical | `PASS` — regression plus MySQL concurrency/idempotency evidence |
| Trial/quota/cleanup | High | `PASS` — full backend regression |
| Freeze/referral/hierarchy | Critical | `PASS` — regression plus MySQL concurrency evidence |
| Bulk actions | Critical | `PASS` — per-target failure/retry and MySQL exact-once evidence |
| Pagination/search/filter/performance | High | `PASS` — frontend build and MySQL `EXPLAIN`/large-fixture evidence |
| Localization/errors | Medium | `PASS` — backend localization tests and frontend production build |
| Dashboard | High | `PASS` — scope tests, frontend build and MySQL aggregate/query plans |
| Telegram/outbox/alerts | High | `PASS` for transactional outbox/failure/retry tests; live send `NOT EXECUTED` |
| Backup/restore | Critical | `PASS` for encryption, state and isolated MySQL restore; native `mysqldump` smoke `NOT EXECUTED` |
| Legacy-bot parity | Medium | `PASS` for documented/tested retained behavior; real legacy bot runtime `NOT EXECUTED` |
| Browser critical UX | High | `NOT EXECUTED` — Browser runtime reported no available browser |

No failed invariant remains in the executable test scope. Environment-dependent
Master/Node/Tunnel, live subscription traffic, live Telegram delivery, native
`mysqldump`, and Browser flows remain `NOT EXECUTED`; production migration and
production restore were intentionally not attempted. Graphify still reports 11
JSON/localization/config files with zero extractable nodes and refreshed 461
communities against 467 prior labels; this is `UNCERTAINTY`, not release proof.
The frontend vendor chunk remains above Vite's 500 KiB warning threshold.

The Runbook does not place release-version preparation inside Stage 13. Therefore
`VERSION`, `app.__version__`, release contracts and install documentation remain
at `4.9.8`. The intended `v5.0.0` bump, main-repository commit, tag, release and
publication are the next separately authorized release-preparation step and were
not executed.

---

## 13. Final Owner/Codex Control Notes

1. This project is an existing customized Marzban system with local work; never treat it as greenfield.
2. Preserve released-v4.9.8 behavior vs local uncommitted fixes as separate facts during review.
3. Reuse sound existing hierarchy/ledger/Plan/bulk infrastructure instead of duplicating it.
4. Keep project context focused by Stage. Summarize stale reasoning; never delete files just to reduce AI context.
5. Keep this file as the single consolidated Codex runbook/ledger, while obeying higher-priority repository docs.
6. Do not add speculative features outside the Stage.
7. Do not over-test every Stage with the full suite; use targeted tests + required integration gates + final full regression.
8. Do not under-test a Stage: every critical invariant it changes must have executable evidence before `PASS`.
9. Anything not actually executed remains `NOT EXECUTED`.
10. Stop after the requested Stage and wait for explicit authorization.

---

## Release-candidate preparation — `v5.0.0-rc.1`

Owner explicitly authorized publication of only the current Marzban release
candidate to `https://github.com/smorad3363/Marzban.git`. The release baseline is
the completed Stage 1–13 working tree on `b45e3af`; historical references to
`v4.9.8` and `v4.9.0` remain historical evidence and are not rewritten.

Release rules:

- runtime and release-contract version: `5.0.0-rc.1`;
- annotated Git tag: `v5.0.0-rc.1`;
- GitHub publication must be a prerelease;
- RC images may publish immutable version and SHA tags but must not move `latest`;
- no automatic server deployment and no final `v5.0.0` tag or release;
- local tooling, Graphify output, caches, test databases, environment files and
  secrets are excluded from the release commit;
- the intentional stale dashboard bundle deletions are included with their
  replacement hashed bundles;
- uncertain deletions of `docs/DEVICE_LIMITS.md` and
  `docs/HEISENBERG_IMPLEMENTATION_ROADMAP_FA.md` remain preserved locally but are
  excluded from the release commit;
- the Stage 12 Marzban-scripts fork remains pinned at
  `1ef7ad62d2c16e4450f1a0de9678c8a8c883b154`.

Pre-publication gate: `PASS`. Candidate scan found no real private key or provider
credential; matches were documented placeholders in `.env.example` and synthetic
test passwords only. `git diff --check`, release contract (`1 passed`) and workflow
YAML parsing passed. Publication remains limited to the exact reviewed manifest,
annotated RC tag and GitHub prerelease; no deployment or final release is allowed.
