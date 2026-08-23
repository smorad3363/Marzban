# Marzban v4.9.8 — Codex Master Specification, Runbook, and Staged Execution Contract

> **Purpose:** This is the single control document for the Marzban customization work discussed with the owner. Give this file to Codex in VS Code and instruct it to execute exactly one numbered stage at a time, for example: **“Execute Stage 1.”** Codex must read this entire file before changing code.
>
> **Language:** This document is intentionally in English. UI copy for the product remains Persian where specified.
>
> **Primary target:** `smorad3363/Marzban`, line/version `v4.9.8`.
>
> **Execution philosophy:** correctness, evidence, and reversible changes are more important than speed. Do not claim the system is “bug-free.” Prove important invariants with executable tests and explicitly report what was not tested.

---

## 1. How Codex Must Use This File

When the owner says **“Execute Stage N”**, Codex must do the following and then stop:

1. Read this entire document.
2. Run the mandatory **Stage 0 preflight** in read-only mode.
3. Inspect the current working tree and preserve all user/local changes.
4. Re-verify the assumptions relevant to Stage N against the actual source code and database models. Historical review notes in this file are leads, not unquestionable truth.
5. Use Graphify when it materially improves call-graph/dependency/blast-radius understanding. Rebuild or refresh the graph if it is stale relative to the current commit/working tree.
6. Implement **only Stage N**, plus the smallest prerequisite changes that are strictly necessary to make Stage N correct.
7. Add or update executable tests for the invariants of Stage N.
8. Execute those tests. Do not infer success from code review alone.
9. Run the relevant regression subset for adjacent functionality.
10. Record the exact commands, results, changed files, migrations, uncertainties, and unexecuted tests in the **Execution Ledger** at the end of this file.
11. Stop. Do **not** automatically continue to Stage N+1.

If a business rule is materially under-specified and a wrong guess could corrupt accounting, permissions, usernames, backups, or hierarchy, mark it **BLOCKED / UNCERTAINTY** and ask for the missing decision instead of inventing behavior.

### Status vocabulary — mandatory

Use only these meanings:

- `PASS` — the exact relevant test/command was actually executed and succeeded.
- `FAIL` — the test/command was executed and failed.
- `NOT EXECUTED` — it was not run. Do not replace this with “should work,” “looks fine,” or “probably works.”
- `UNCERTAINTY` — evidence is incomplete, behavior depends on an unresolved business rule, or the environment cannot prove the claim.
- `BLOCKED` — execution cannot safely continue until a specific prerequisite or decision is provided.

A successful build is **not** proof that business logic works. A successful unit test is **not** proof that MySQL migrations work. A mocked Telegram test is **not** proof that a real Telegram credential can send a message. Report each layer separately.

---

## 2. Non-Negotiable Engineering Rules

1. **Never destroy user work to simplify the task.** Do not run `git reset --hard`, destructive checkout, cleaning commands, forced stashes, or delete files merely to reduce AI context.
2. **Do not conflate AI context with the filesystem.** Old reasoning/logs may be summarized out of active context; project files must not be removed to “make context smaller.”
3. **Do not overwrite existing local fixes blindly.** The uploaded working tree previously contained local, uncommitted changes around Plans, MarzHelp policy, and device-limit accounting. Verify current `git diff` before editing.
4. **Do not silently mutate production.** Tests and migrations must run against disposable/local environments unless the owner explicitly authorizes production work.
5. **Do not silently commit or push.** Code changes for the requested stage are allowed when the owner says to execute that stage; commit, push, release, deploy, or GitHub fork operations require explicit authorization unless the requested stage itself explicitly includes that external action.
6. **Do not use UI hiding as authorization.** Every restricted action must also be enforced server-side/API-side.
7. **Do not use frontend-only accounting.** Quotas, grants, reclaims, billing modes, trial consumption, freeze, referral effects, and bulk operations must be enforced transactionally in the backend.
8. **Do not parse English human-readable error strings as business logic.** Prefer stable machine-readable error codes.
9. **Do not add a cash/payment subsystem.** The owner explicitly does not want prices, money, or financial wallet clutter in the panel. If referral reward units remain ambiguous, stop and ask rather than inventing a cash system.
10. **Do not remove the legacy/default Marzban sales bot until functional parity is demonstrated.** First build a capability matrix and prove nothing required is lost.
11. **Do not call a test “definitive” unless the relevant environment exists.** For MySQL behavior, use MySQL. For real Master/Node/Tunnel behavior, use an actual suitable environment or report `NOT EXECUTED`.
12. **No Caveman-style/tool audit.** Final panel capability/problem audits must be written as normal technical English with severity and evidence.

---

## 3. Project Identity and Operational Baseline

### Primary repository

`https://github.com/smorad3363/Marzban`

### Target release line

`v4.9.8`

Historical review identified the published `v4.9.8` release around commit `b45e3af6`. **Verify this locally before relying on it.**

### Fresh install command currently used by the owner

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v4.9.8/scripts/marzban.sh)" @ install --version v4.9.8 --database mysql
```

### Update command currently used by the owner

```bash
marzban update --version v4.9.8
```

### Marzban Node script currently referenced upstream

```bash
sudo bash -c "$(curl -sL https://github.com/gozargah/Marzban-scripts/raw/master/marzban-node.sh)" @ install --name master
```

A later stage must fork `gozargah/Marzban-scripts` into the owner’s GitHub and update the operational URL to the fork. Prefer a stable tag/commit over a floating `master` when practical.

### Uploaded review material

The prior review included:

- an uploaded project archive;
- a screenshot showing the admin traffic-credit field as non-editable;
- a Graphify graph/report;
- a comparison between published `v4.9.8` and an uploaded working tree with local changes.

Do not assume the current checkout is identical to either historical state. Re-run preflight.

---

## 4. Mandatory Stage 0 — Read-Only Preflight Before Every Implementation Stage

Stage 0 is not a feature stage. It is a mandatory safety check before any numbered implementation stage.

### 4.1 Repository state

Record at minimum:

```bash
git status --short
git rev-parse HEAD
git describe --tags --always --dirty
git diff --stat
git diff
git diff --staged
```

Also inspect recent history relevant to the target files:

```bash
git log --oneline --decorate -n 20
```

Do not alter the working tree during preflight.

### 4.2 Read repository instructions

Read all applicable `AGENTS.md`, contributing instructions, README build/test instructions, package scripts, migration conventions, and deployment scripts before changing code.

### 4.3 Determine exact dependency/test commands

Do not invent package-manager commands. Inspect lockfiles and scripts first. Identify:

- backend dependency/environment method;
- backend test command;
- frontend package manager;
- frontend typecheck/lint/test/build commands;
- Alembic migration commands;
- MySQL test environment or Docker/Compose support;
- existing integration/E2E harness;
- Graphify invocation and graph freshness.

### 4.4 Database baseline

Record:

- database engine expected in production (`MySQL` for the owner’s install path);
- current Alembic head(s);
- current schema revision in test DB;
- whether a disposable MySQL instance is available;
- whether migration backup/restore can be tested safely.

Never substitute SQLite results for a required MySQL migration claim.

### 4.5 Graphify

Use Graphify for dependency mapping where useful, especially these flows:

- `user update -> MarzHelp policy -> quota/accounting`;
- `admin resource adjustment -> ledger -> parent/child hierarchy`;
- `plan -> user creation -> inbound/host -> subscription generation`;
- `device limit -> penalty -> delete/suspend -> deleted-user accounting`;
- `freeze -> admin auth/actions -> user state -> subtree`;
- `backup scheduler -> backup generation -> Telegram delivery -> health state`.

Historical Graphify output was built against the `v4.9.8` baseline and was therefore potentially stale relative to local changes. Never treat graph output as stronger evidence than source, migrations, runtime behavior, or tests.

### 4.6 Obsidian-compatible project memory

For all software projects, Codex should maintain durable project memory as Markdown compatible with Obsidian.

For this project, **this file is the single master control document**. Update its Execution Ledger after each stage instead of creating multiple competing runbooks.

Obsidian itself is an external application, not a library that belongs inside the Marzban codebase. If the workstation has Obsidian available, Codex may open/use this Markdown as the project vault/control note. If the owner has authorized environment setup and Obsidian is missing, install/configure it at the workstation level when technically possible; never add Obsidian as an application dependency of Marzban. If GUI execution is not possible from the VS Code/Codex environment, report `NOT EXECUTED` rather than pretending it ran.

---

## 5. Historical Review Findings — Re-Verify Before Editing

These were identified earlier and must be treated as concrete leads. Exact paths/functions may have changed in the current working tree.

### BUG-01 — Plan Inbound Selector UX

Historical location: `app/dashboard/src/pages/Plans.tsx`.

Released `v4.9.8` used a raw text/string model for inbound tags, with comma-separated typing and splitting/joining. Desired behavior: populate configured inbounds from the backend and let the user select them with a real multi-select/checkbox UI.

### BUG-02 — Empty Inbound Plan Integrity

A Plan can historically be represented with an empty inbound list, but user creation requires at least one proxy/inbound. A Plan must not be persistable if it cannot later produce a valid user, unless an explicit, tested fallback semantic is introduced.

### BUG-03 — Plan Host Scoping Gap

Plan-specific Host selection is not merely a UI task. Historical data modeling linked Plans to Inbounds while Hosts belonged to Inbounds and subscription generation consumed active Hosts. If a Plan must select specific Hosts, the relation must exist in schema/API and be enforced during subscription generation.

### BUG-04 — False Renewal Classification

Historical location: `app/utils/marzhelp_policy.py`, around renewal classification logic such as `_is_renewal()`.

An ordinary increase of a user’s `data_limit` was historically interpreted as a renewal, causing:

`MarzHelp: renewal quota is exhausted`

even when the admin had ordinary edit/traffic allowance. Renewal must represent an actual renewal business event, not simply “new numeric value > old numeric value.”

### BUG-05 — Renewal Quota Management Gap

A backend renewal-policy management endpoint existed historically, but dashboard management was incomplete. An admin could reach `renewal_remaining = 0` without a clear management path.

### BUG-06 — Admin Traffic Credit Read-Only

Historical location: `app/dashboard/src/pages/Admins.tsx`.

The traffic-credit field was explicitly `readOnly`/`isReadOnly`. Backend hierarchy logic also protected direct `total_traffic` mutation. Correct behavior is not “remove readOnly and update the number directly.” It must translate a desired change into ledger-safe `grant`/`reclaim` operations.

Example:

- `200 GiB -> 230 GiB` means `grant 30 GiB`.
- `200 GiB -> 170 GiB` means `reclaim 30 GiB`.

### BUG-07 — Unlocalized Error Pipeline

Historical location included `app/dashboard/src/utils/toastHandler.ts` and raw backend errors.

Examples included English MarzHelp errors and generic fallback text such as `Something went wrong!`. The Persian UI should resolve stable error codes to clean Persian messages instead of exposing backend prose.

### BUG-08 — Unlimited Plan Display

Where `data_limit = 0` semantically means Unlimited, historical UI could render it as `0 B`. Correct that semantic display without globally assuming every zero-valued field is Unlimited.

### BUG-09 — Device Auto-Delete Accounting

Historical device-limit auto-delete in released `v4.9.8` could bypass deleted-user traffic capture. The uploaded working tree may already have added something equivalent to `marzhelp_policy.capture_delete(db, user)` before deletion. Verify the current diff and ensure all deletion paths preserve required accounting exactly once.

### BUG-10 — Legacy Sudo Policy Bypass

Historical policy logic could exempt any `is_sudo=True` admin from MarzHelp enforcement, including legacy hierarchy admins. The intended exemption is only the actual Owner where explicitly required. A local fix may already exist; verify it.

### GAP-01 — First-Class Trial Plan

Trial/Test is not allowed to be inferred from plan name or username heuristics. It must be first-class metadata.

### GAP-02 — Per-Admin Trial Quota

Each admin needs an independently adjustable Trial creation entitlement. Retry/idempotency must not consume Trial quota twice.

### GAP-03 — General Admin Bulk Actions

Required first action: grant `N GiB` to selected admins through the resource ledger. Additional actions should map to real persistent admin settings/resources, not frontend-only invented state.

### GAP-04 — Plan Access Controls UI

Historical backend support included concepts such as `allowed_admin_ids` and `include_subtree`, while the Plan UI did not meaningfully expose them. Verify and wire them correctly.

### PERF-01 — User Card Pagination

Server-side pagination requirements:

- default page size `10`;
- selectable `10`, `25`, `50`;
- hard backend maximum `50`.

A frontend-only page size does not reduce database load if the backend still fetches a large dataset.

### OPS-01 — Marzban-scripts Fork

Fork upstream scripts into the owner’s GitHub only in the dedicated external-operations stage and only with usable GitHub authorization.

---

## 6. Product Architecture Target

The current admin/reseller management is considered unnecessarily complicated. The target is a simpler system where **billing/accounting model**, **permissions**, **network assignment**, and **resource entitlements** are separate concepts.

### 6.1 Roles

At minimum, reason about these roles/scopes explicitly:

- **Owner** — ultimate policy and infrastructure authority.
- **Admin / Reseller** — creates/manages customers within an assigned commercial/accounting model and permission scope.
- **Sub-admin** — optional child admin who receives a delegable subset of parent resources/permissions.

Do not use legacy `is_sudo` as a substitute for a clear Owner identity if the hierarchy model distinguishes them.

### 6.2 Three primary admin accounting modes

Use stable machine-readable identifiers. Suggested names are shown below; Codex may adapt names to existing conventions but must preserve semantics.

| Mode | Suggested ID | Accounting basis | User count | Normal user creation UX |
|---|---|---|---|---|
| Seat/User capacity credit | `SEAT_CREDIT` | units consumed when accounts/plans are created | constrained by consumable capacity | Plan-only |
| Actual used traffic | `USED_TRAFFIC` | real traffic actually consumed | unlimited by this mode | simplified manual form |
| Allocated/created traffic | `ALLOCATED_TRAFFIC` | traffic quota allocated during create/renew/update | unlimited by this mode | simplified manual form |

Billing mode and permission flags must not be mixed into one giant conditional admin form.

---

## 7. Exact Business Rules Captured From the Conversation

### 7.1 `SEAT_CREDIT` is consumable, not an active-seat pool

This corrects an earlier wrong suggestion.

If an admin has `100` seat/user-capacity units and creates a subscription requiring `2` simultaneous users/devices, remaining capacity becomes `98`.

**Expiration does not restore those 2 units.** The admin cannot bypass the limit by waiting for expiry and creating another account. Additional capacity must be explicitly granted by the Owner (or an authorized parent if delegation policy permits it).

This resource behaves like a consumable entitlement/credit, not “currently active seats.”

#### Blocking decision still required

**D-01 — Seat renewal charging:** Does renewing an existing 2-seat account consume another 2 seat-credit units, consume a separate renewal entitlement, or use another rule? Do not invent this. Before Stage 5 finalizes renewal behavior for `SEAT_CREDIT`, resolve this decision with the owner.

### 7.2 `SEAT_CREDIT` admins are Plan-only

These admins must not see or access the raw user builder. They create/renew normal accounts and Trial accounts only from Plans they are authorized to use.

They must not choose or edit low-level fields such as:

- arbitrary volume when Plan defines it;
- inbound;
- host;
- arbitrary expiry/duration outside Plan;
- concurrency/device count outside Plan;
- protocol/proxy primitives that the Plan/network policy owns.

This restriction must be enforced at API/service level, not merely by hiding controls.

### 7.3 `USED_TRAFFIC` admins use a simplified manual user form

They are **not** forced into Plans for every normal account.

Allowed editable fields for normal creation:

- desired username;
- volume/data limit;
- time/duration/expiry;
- description/note.

They must **not** be able to select or modify:

- Inbound;
- Host;
- concurrency/device count.

Those protected network/device settings are centrally assigned from Admin Management by the Owner or another explicitly authorized authority.

Accounting must charge only newly consumed traffic, never re-charge the same previously counted bytes.

### 7.4 `ALLOCATED_TRAFFIC` admins

User count is unlimited by this model. Accounting is based on the traffic quota allocated/provisioned to users during create/renew/update, rather than actual bytes consumed.

The simplified form should generally expose the same user-friendly fields as `USED_TRAFFIC` unless an existing product constraint requires otherwise:

- username;
- volume;
- time;
- description.

Inbound, Host, and concurrency/device count remain centrally controlled.

#### Safety rule

Do not automatically refund allocated credit on delete, expiry, or volume reduction unless the owner explicitly confirms that refund policy. Silent automatic refunds create an obvious abuse path. Any refund/reclaim must be explicit and auditable unless a tested business rule says otherwise.

### 7.5 Network assignment belongs to admin management / Plans

Resellers must not manually choose arbitrary Inbounds/Hosts during restricted user creation.

Owner-level configuration must define which Inbounds/Hosts an admin or Plan may use. If Plan-specific Host selection is supported, subscription generation must enforce it.

### 7.6 Resource changes use explicit adjustments, not raw absolute edits

Instead of repeatedly editing fields such as “Admin traffic limit = 700,” use explicit operations:

- Grant traffic;
- Reclaim traffic;
- Grant seat/user capacity;
- Reclaim seat/user capacity;
- Grant Trial quota;
- Reclaim Trial quota;
- other real resource types discovered in the persistent model.

Each adjustment needs an audit record containing at least:

- resource type;
- delta;
- before value;
- after value;
- actor;
- target admin;
- reason/note where appropriate;
- timestamp;
- idempotency key or equivalent duplicate protection;
- correlation/operation ID suitable for Telegram logs.

### 7.7 Trial/Test subscriptions

Required examples include:

- `1 GiB / 1 day / 1 device`;
- `2 GiB / 1 day / 1 device`;
- `1 day / Unlimited / 1 device`;
- `1 day / Unlimited / 2 devices`.

Trial must be explicit metadata, not inferred from names.

Per-admin Trial creation quota must be separately adjustable. A successful Trial creation consumes exactly one Trial entitlement according to the defined quota model. Retrying the same idempotent operation must not consume it twice.

Unlimited Trial accounting must be explicitly defined for finite-credit admins before enabling it.

### 7.8 Sub-admin delegation

An admin may optionally be allowed to create sub-admins from its own delegable resources/limits.

Core invariant:

> A child must never receive a resource, Plan, network scope, permission, or delegable authority that the parent is not authorized to delegate.

Delegating finite resources must debit the parent and credit the child transactionally where applicable. No double-spend under concurrent requests.

### 7.9 Referral

A referral relationship is conceptually separate from hierarchy/parenthood.

- `parent_admin_id` and `referrer_admin_id` must not be assumed to be the same concept.
- Only the Owner may set/change the referral relationship/rate for an admin.
- The owner does **not** want cash, prices, or monetary wallet UI clutter in the panel.

#### Blocking decision still required

**D-02 — Referral reward unit:** The conversation requires referral profit/credit, but intentionally rejects a money subsystem in the panel. Before implementing actual reward settlement, confirm whether referral reward should be traffic credit, seat credit, another internal resource credit, or something else. Do not invent currency.

### 7.10 Admin username namespace / user prefix

Each admin should receive a unique, stable random namespace prefix. Users created by that admin should use:

`randomprefix_requestedusername`

Goals:

- prevent cross-admin username collisions;
- retain the admin’s human-chosen username suffix;
- make namespace ownership deterministic.

Rules:

- prefix generated once and persisted;
- prefix must be unique;
- final username validated server-side;
- client cannot bypass prefix generation;
- do not rename existing users during migration unless explicitly authorized because subscription identities/URLs may depend on usernames.

#### Clarification still useful

**D-03 — Owner and admin-login naming:** Confirm whether the prefix applies only to customer usernames created by non-owner admins, or also to Owner-created customers/admin login usernames. Default safest migration behavior is to preserve existing login/user names and apply namespaces only to new customer creation under admins.

### 7.11 Admin freeze mode

Owner must be able to freeze an admin.

A freeze must:

- prevent the frozen admin from performing management actions;
- block authentication/session use according to the chosen auth architecture;
- suspend/disable that admin’s users according to an explicit reversible freeze contract;
- show a clear panel message instructing the admin to contact support;
- be fully auditable;
- be reversible.

Critical invariant: unfreeze must not incorrectly re-enable users that were already disabled for unrelated reasons before the freeze. Track freeze-origin state or equivalent provenance.

#### Blocking decision still required

**D-04 — Freeze cascade:** Confirm whether freezing an admin also freezes all descendant sub-admins and their users, or only the direct admin and directly owned users. Do not silently guess.

### 7.12 Bulk user operations

Owner needs bulk operations to add:

- volume;
- time;
- or both

to:

- all users;
- users belonging to selected admins;
- other safely filterable target sets if useful.

Before implementation define:

- idempotency;
- per-item vs all-or-nothing transaction semantics;
- partial failure reporting;
- renewal-quota interaction;
- accounting impact for each admin billing mode;
- whether disabled/expired/trial users are included.

### 7.13 Trial cleanup

Add safe bulk cleanup for Trial/Test subscriptions.

- select trials by first-class Trial metadata;
- never infer Trial from username patterns;
- preserve required deleted-user traffic/accounting history;
- support dry-run/count preview before destructive cleanup;
- report exactly what was deleted/skipped/failed.

### 7.14 Admin creation refactor

The current create-admin flow is too slow and overloaded with irrelevant options. Redesign it around the new model.

Required:

- phone number is mandatory for new admins;
- Discord field/workflow is not needed and should be removed from the intended UI;
- show only fields relevant to the selected billing mode and permissions;
- network assignment belongs in a clear dedicated section;
- resource grants belong in explicit adjustment controls rather than raw hidden magic;
- creation must be substantially faster and easier to understand.

Migration note: making phone required in the API for **new** admins does not require immediately making a legacy DB column `NOT NULL` if old rows have no phone. Handle legacy data deliberately before enforcing a hard DB constraint.

Do not immediately drop legacy Discord data/columns if external compatibility has not been audited. Remove from intended UI first; schema cleanup can be a later safe migration.

### 7.15 Admin dashboard

Add a professional admin dashboard with efficient aggregated queries.

At minimum show useful mode-aware information such as:

- current total users;
- change vs previous week;
- created users over time;
- total/period traffic;
- used traffic for `USED_TRAFFIC`;
- allocated traffic for `ALLOCATED_TRAFFIC`;
- remaining seat/user capacity for `SEAT_CREDIT`;
- Trial usage/remaining Trial quota;
- relevant resource remaining values;
- optionally sub-admin counts/status when enabled.

Do not implement per-card N+1 queries. Use efficient aggregation, indexes, and bounded time windows.

### 7.16 User list pagination

User cards must use real server-side pagination:

- default `10`;
- selectable `10`, `25`, `50`;
- backend hard maximum `50`.

Search/filter/sort should be server-side. Verify query count and payload size. If the frontend merely renders 10 while the backend still fetches 1000, the performance requirement is not met.

### 7.17 Localization and messages

The panel is Persian-focused. Audit warnings/errors/UI text for mixed English or unclear wording.

Preferred architecture:

1. backend emits stable error code + structured details;
2. frontend maps error code to Persian i18n text;
3. raw backend prose is only a developer/debug fallback, not the normal end-user message.

Correct semantic display of Unlimited values. Do not show `0 B` where zero is explicitly the Unlimited sentinel.

### 7.18 Telegram operations log, backup, and alerts

Add a dedicated Telegram integration for:

- detailed admin/resource operation logs;
- scheduled backups;
- backup health/failure alerts;
- near-limit admin warnings.

The owner does not want money/pricing UI; detailed operational charge/grant/reclaim events should instead be visible in Telegram logs.

#### Backup requirements

- default schedule: every **30 minutes**;
- send backups to Telegram;
- backup event/file sends should be traceable individually;
- track health and last successful backup;
- explicitly report failure;
- validate that produced backup is non-empty and structurally plausible;
- record file size/hash when practical;
- retry transient Telegram delivery failures safely;
- never expose bot tokens or secrets in logs;
- avoid duplicate concurrent backup runs in multi-process deployments.

Use the existing Marzban backup mechanism where possible instead of creating a second incompatible backup format.

A successful archive creation plus failed Telegram upload is **not** a successful remote-backup delivery. Track generation and delivery separately.

#### Operation logs

Telegram messages should contain enough detail for forensic/admin review, for example:

- event type;
- actor;
- target admin/user;
- resource type;
- before/delta/after;
- reason;
- operation/correlation ID;
- timestamp;
- result.

Use a durable event/outbox pattern or equivalent reliable mechanism so a successful database transaction is not lost merely because Telegram is temporarily unavailable. Telegram failure must not roll back a valid business transaction unless explicitly designed that way.

#### Near-limit warnings

Warn when an admin approaches configured limits. Thresholds should be configurable or clearly defined. Implement deduplication/hysteresis so a periodic checker does not spam the same warning every run.

### 7.19 Legacy/default Marzban sales bot

Some bulk actions formerly associated with the default bot have been added to the panel. Do not assume the bot is obsolete.

Before removal/disablement:

1. inventory all bot capabilities currently relied on;
2. map each to equivalent panel/API functionality;
3. verify permissions and workflows;
4. list any missing parity;
5. only remove if the owner explicitly approves after parity is proven.

---

## 8. Recommended Backend Design Principles

These are architecture constraints, not mandatory class names.

### 8.1 Strategy/policy layer for billing modes

Do not scatter this everywhere:

```python
if billing_mode == ...
```

Prefer one contract with mode-specific strategies/services, conceptually:

- `SeatCreditPolicy`;
- `UsedTrafficPolicy`;
- `AllocatedTrafficPolicy`.

Creation, update, renewal, delete, and reconciliation should call a consistent domain service that decides accounting effects from explicit operation intent.

### 8.2 Explicit operation intent

Do not classify “renewal” solely from field deltas such as `new_data_limit > old_data_limit`.

If the UI/API/service already knows whether the action is Create, Edit, Renew, Trial Create, Trial Renew, Bulk Adjust, etc., propagate that intent through trusted server-side service boundaries. If current APIs do not expose a safe intent signal, introduce the smallest explicit server-side operation path rather than inferring business meaning from numeric comparisons.

Do not trust an arbitrary client-provided `is_renewal=false` flag as authorization to avoid quota consumption.

### 8.3 Ledger / entitlement adjustments

Use append-only or auditable adjustment records for finite resources. Avoid direct blind overwrites where history matters.

For concurrency-sensitive grants/reclaims/delegation, use transactions and locking/atomic update conditions to prevent double-spend.

### 8.4 Used-traffic accounting checkpoint

`USED_TRAFFIC` must not subtract the same bytes more than once.

Prefer existing persisted authoritative user usage where possible. If a checkpoint/delta mechanism is required, store enough state to compute the incremental charge safely and handle counter resets/restarts without producing negative usage or duplicate charges.

### 8.5 Transactional outbox for Telegram events

Strongly prefer recording a durable notification/outbox event in the same transaction as the business operation, then delivering asynchronously/retriably to Telegram. This decouples business correctness from Telegram availability while preserving auditability.

### 8.6 Stable error contract

Business errors should expose stable codes, for example conceptually:

- `RENEWAL_QUOTA_EXHAUSTED`;
- `TRAFFIC_CREDIT_EXHAUSTED`;
- `TRIAL_QUOTA_EXHAUSTED`;
- `ADMIN_FROZEN`;
- `PLAN_NOT_ALLOWED`;
- `INBOUND_NOT_ALLOWED`;
- `RESOURCE_RECLAIM_EXCEEDS_BALANCE`.

Use existing project error conventions if present instead of inventing an incompatible envelope.

---

## 9. Security and Authorization Invariants

These must have negative API tests, not only UI tests.

1. Non-Owner cannot change another admin’s referral rate/relationship if that action is Owner-only.
2. Restricted admin cannot bypass Plan-only mode by directly calling the raw user-create endpoint.
3. `USED_TRAFFIC` / `ALLOCATED_TRAFFIC` admin cannot inject arbitrary Inbound/Host/device-count fields through API payloads.
4. Child admin cannot receive/delegate resources above the parent’s delegable balance.
5. Child admin cannot receive a Plan/network scope the parent cannot delegate.
6. Legacy `is_sudo` alone does not bypass policy unless that account is the intended real Owner.
7. Frozen admin cannot mutate users/admins/resources through API even if it has a previously issued session/token, according to the finalized freeze policy.
8. Bulk operations must respect target scope and ownership.
9. Telegram secrets must never be returned to ordinary admins or written to operation logs.
10. Internal admin prefix generation cannot be overridden to collide with another admin namespace.

---

## 10. Data Integrity Invariants

1. Every successful finite resource adjustment changes balance exactly once and creates exactly one audit/ledger effect.
2. Retrying the same idempotent operation does not double charge/grant/reclaim/consume Trial quota.
3. Parent-to-child finite resource delegation cannot create resources from nothing.
4. Device-limit auto-delete preserves the accounting data required for deleted users exactly once.
5. Ordinary user edit does not consume Renewal quota unless the operation is explicitly a renewal under the finalized policy.
6. `USED_TRAFFIC` charges only new traffic delta.
7. `ALLOCATED_TRAFFIC` charges the intended allocation delta and never silently refunds without a defined rule.
8. `SEAT_CREDIT` does not automatically return capacity when a user expires.
9. Plan saved state must be sufficient to create a valid user.
10. Plan Host scoping, when configured, must affect actual generated subscriptions.
11. Freeze/unfreeze does not corrupt pre-existing disabled states.
12. Trial cleanup preserves required deleted-user accounting/history.
13. Telegram delivery failure does not silently erase the underlying operation event.
14. Backup health distinguishes “backup generated” from “backup delivered remotely.”

---

# 11. Staged Implementation Plan

The scope has expanded beyond the original nine stages. The final plan uses **13 implementation stages**, plus mandatory Stage 0 preflight. This is deliberate to keep Codex context focused and reduce cross-domain regressions.

---

## Stage 1 — Critical Accounting and Policy Correctness

### Scope

Fix only:

- BUG-04 False Renewal Classification;
- BUG-09 Device Auto-Delete Accounting;
- BUG-10 Legacy Sudo Policy Bypass.

Do not begin the admin redesign yet.

### Required implementation outcome

- Ordinary user volume/time edit is not misclassified as renewal merely because a value increases.
- Actual renewal operations continue to enforce renewal policy.
- Device-limit delete/penalty paths preserve required deleted-user accounting.
- Only the intended Owner gets policy bypass where the business rules require it.

### Required tests

At minimum:

1. Ordinary data-limit increase with `renewal_remaining = 0` and sufficient ordinary allowance: operation succeeds if allowed and Renewal quota remains unchanged.
2. Explicit renewal with exhausted Renewal quota: fails with the correct structured business error.
3. Explicit renewal with available Renewal quota: succeeds and consumes exactly the intended amount.
4. Repeating ordinary edits does not silently decrement Renewal quota.
5. Manual delete and device-limit auto-delete produce equivalent required deleted-user traffic capture.
6. Accounting capture is not duplicated if deletion flow retries or calls shared logic.
7. Actual Owner exemption behaves as intended.
8. Legacy/non-owner `is_sudo=True` admin is still policy-enforced.
9. Existing policy tests are updated so they no longer lock in the incorrect “volume increase == renewal” assumption.

### Definition of Done

- Stage-specific unit/integration tests `PASS`.
- Relevant existing backend regression tests `PASS`.
- DB before/after assertions prove quota/accounting state, not only HTTP status.
- Any MySQL-specific test not run is reported `NOT EXECUTED`.
- No unrelated UI redesign.

Stop after reporting Stage 1.

---

## Stage 2 — Admin Resource Ledger, Credit Editing, and Renewal Management

### Scope

Fix BUG-05 and BUG-06 and establish one safe adjustment mechanism for admin resources.

### Required implementation outcome

- Admin traffic/resource limits are changed through explicit Grant/Reclaim operations.
- Admin detail UI can increase/decrease credit without direct blind mutation.
- Creating a new admin with initial credit uses the same safe accounting path.
- Renewal quota/policy is visible and manageable to the proper authority.
- Adjustment history is inspectable/auditable.

### Required tests

1. `+30 GiB` grant changes target balance exactly once and creates audit/ledger entry.
2. `-30 GiB` reclaim changes target balance exactly once.
3. Reclaim beyond allowed balance fails safely.
4. Parent/child accounting remains balanced where parent-funded credit applies.
5. Duplicate/idempotent request cannot double-grant.
6. Concurrent grants/reclaims cannot create negative/duplicated balances.
7. New admin initial credit is represented by the correct ledger operation rather than magic raw assignment.
8. Unauthorized admin cannot adjust protected resources.
9. Renewal quota management API/UI respects authorization.

### Definition of Done

No direct UI edit path can silently bypass the ledger. Stop after Stage 2.

---

## Stage 3 — Admin Billing-Mode Foundation

### Scope

Introduce a clear billing/accounting-mode model for:

- `SEAT_CREDIT`;
- `USED_TRAFFIC`;
- `ALLOCATED_TRAFFIC`.

Create a clean service/policy boundary. Do not yet complete every UI workflow from later stages.

### Required implementation outcome

- Billing mode is explicit persistent state.
- Migration handles legacy admins safely.
- Existing admins receive a deliberate compatible default; do not guess if current legacy semantics vary.
- Accounting behavior is isolated behind a coherent strategy/service layer.
- Seat capacity is consumable and not automatically restored on expiry.
- Used traffic has a safe incremental accounting basis.
- Allocated traffic has a safe allocation accounting basis.

### Required tests

1. Migration on representative legacy data.
2. Each mode selects the correct accounting strategy.
3. Seat consumption does not return on expiry.
4. Used-traffic repeated reconciliation with unchanged usage charges zero additional traffic.
5. Increased used traffic charges only the delta.
6. Counter reset/restart scenario cannot create negative or duplicate charge.
7. Allocated create charges expected allocation once.
8. Allocated update increase charges only intended delta.
9. No automatic allocated refund on delete/reduction unless explicitly authorized.
10. Mode changes are Owner-only and must not silently reinterpret existing balances.

### Blocking rule

If legacy-admin default mode cannot be determined safely, mark `BLOCKED` and ask. Do not migrate all admins to a guessed commercial model.

Stop after Stage 3.

---

## Stage 4 — Plan, Inbound, Host, and Access-Control Integrity

### Scope

Fix BUG-01, BUG-02, BUG-03, GAP-04.

### Required implementation outcome

- Plan Inbounds are selected from live configured values with multi-select/checkbox UX.
- Backend also validates selections.
- Invalid empty configuration cannot be saved if it cannot produce a valid user.
- Add first-class Plan Host scoping if required by the owner’s desired Plan behavior.
- Host selection is enforced by subscription generation, not only stored.
- Wire `allowed_admin_ids` / `include_subtree` or current equivalent to real UI and authorization.
- Admin-level network access can be represented for later restricted creation flows.

### Required tests

1. Plan UI loads live Inbounds.
2. Unknown inbound rejected server-side.
3. Empty invalid Plan rejected server-side and UI-side.
4. Valid Plan creates a user with valid proxies.
5. Plan Host selection persists.
6. Generated subscription contains only permitted/selected Hosts where scoping applies.
7. Disabled/deleted Host behavior is defined and tested.
8. Unauthorized admin cannot use a Plan outside access scope.
9. Subtree access semantics match `include_subtree` behavior.

Stop after Stage 4.

---

## Stage 5 — Restricted User Creation, Renewal UX, and Username Namespace

### Scope

Implement mode-aware creation/renewal controls and the admin namespace prefix.

### Required behavior

#### `SEAT_CREDIT`

- raw user builder unavailable;
- only allowed Plans/Trials;
- protected fields cannot be injected through API.

#### `USED_TRAFFIC`

Expose only:

- username;
- volume;
- time;
- description.

Do not expose Inbound/Host/device-count. Apply admin network/device policy automatically.

#### `ALLOCATED_TRAFFIC`

Use the same simplified field philosophy unless the existing product model requires a documented exception.

#### Username namespace

Persist a unique stable prefix per admin and generate customer username as:

`prefix_requestedusername`

### Required tests

1. Seat admin raw create endpoint is denied.
2. Seat admin can create from authorized Plan.
3. Used/Allocated admin can use allowed simple fields.
4. API attempts to inject Inbound/Host/device count are ignored/rejected according to explicit contract, never honored.
5. Effective generated user receives only admin-authorized network configuration.
6. Prefix is generated once and remains stable.
7. Prefix uniqueness under concurrent admin creation.
8. Same requested username under two admins produces distinct final usernames.
9. Existing users are not renamed by migration.
10. Renewal path respects the same protected-field rules.

### Blocking decision

Resolve **D-01 Seat renewal charging** before finalizing Seat renewal accounting.

Stop after Stage 5.

---

## Stage 6 — Trial/Test System and Trial Cleanup

### Scope

Implement first-class Trial metadata, Trial Plans, per-admin Trial quota, and safe cleanup.

### Required implementation outcome

- Trial is explicit model state.
- Owner can create Trial Plans including the required examples.
- Admin Trial quota can be granted/reclaimed.
- Trial creation consumes quota exactly once.
- Cleanup uses Trial metadata and supports safe preview/dry-run.

### Required tests

1. 1 GiB / 1 day / 1-device Trial.
2. 2 GiB / 1 day / 1-device Trial.
3. Unlimited 1-day / 1-device Trial under explicitly valid accounting semantics.
4. Unlimited 1-day / 2-device Trial under explicitly valid accounting semantics.
5. Trial quota exhausted error.
6. Idempotent retry consumes quota once.
7. Cleanup preview count is correct.
8. Cleanup deletes only Trial records in scope.
9. Cleanup does not delete normal accounts with “test” in username/note.
10. Deleted-user accounting/history remains correct.

### Blocking rule

If Unlimited Trial can bypass finite admin credit and no policy is defined, mark that scenario `BLOCKED` rather than enabling it unsafely.

Stop after Stage 6.

---

## Stage 7 — Hierarchy Delegation, Referral, and Freeze

### Scope

Implement or refactor:

- optional sub-admin creation;
- delegable resource/permission scope;
- referral relationship/rate controls;
- freeze/unfreeze.

### Required implementation outcome

- Child can never exceed parent’s delegable entitlements/permissions.
- Finite resource delegation is transactional.
- Referral relationship is distinct from hierarchy.
- Only Owner can set referral relationship/rate.
- Freeze is auditable and reversible.
- Frozen admin gets clear contact-support message.

### Required tests

1. Parent delegates valid resources -> parent debited, child credited once.
2. Over-delegation rejected.
3. Concurrent delegation cannot double-spend.
4. Child cannot receive inaccessible Plan/Inbound/Host/permission.
5. Non-Owner cannot change referral config.
6. Freeze blocks management API calls with existing active token/session as required.
7. Freeze user-state effect is correct.
8. Unfreeze restores only freeze-caused user state, not unrelated prior disables.
9. Audit records exist for freeze/unfreeze.
10. Hierarchy behavior under freeze matches finalized cascade rule.

### Blocking decisions

Resolve:

- **D-02 Referral reward unit** before implementing actual referral reward settlement.
- **D-04 Freeze cascade** before implementing subtree effects.

Stop after Stage 7.

---

## Stage 8 — Bulk Admin and Bulk User Actions

### Scope

Implement safe, auditable bulk actions.

Required minimum:

- grant/reclaim `N GiB` to selected admins;
- adjust other real admin resources where supported;
- add volume to all users or users of selected admins;
- add time to all users or users of selected admins;
- combined volume/time adjustment where appropriate;
- Trial cleanup may reuse Stage 6 infrastructure rather than duplicate it.

### Required implementation outcome

- target preview/count before execution where destructive or broad;
- explicit batch semantics;
- per-item result visibility if not atomic;
- idempotency/correlation ID;
- correct accounting effects per billing mode;
- Telegram outbox event hooks may be introduced here if Stage 11 will consume them, but do not require live Telegram for Stage 8 correctness.

### Required tests

1. Correct target selection.
2. No unauthorized cross-scope targets.
3. Idempotent retry.
4. Partial failure behavior matches documented contract.
5. Bulk user volume adjustment does not accidentally consume renewal quota unless explicitly defined.
6. Accounting differs correctly for Used vs Allocated vs Seat modes.
7. Large bounded batch does not cause obvious N+1/excessive transaction issues.

Stop after Stage 8.

---

## Stage 9 — Admin Creation/Management UX and Professional Dashboard

### Scope

Refactor the Admin UX after backend models are stable.

### Required implementation outcome

- simpler create-admin flow;
- mandatory phone number for new admins;
- Discord removed from intended create/manage UI;
- billing mode clearly selected;
- only relevant fields shown;
- network assignment separated cleanly;
- resource changes use Grant/Reclaim UI;
- Trial quota and renewal controls visible where relevant;
- freeze state/control visible to Owner;
- sub-admin/referral controls visible only to authorized roles;
- professional dashboard with week-over-week and mode-specific metrics.

Also audit historically backend-only controls such as current equivalents of:

- Renewal Policy;
- User Creation Mode;
- `can_manage_plans`;
- API token management;
- suspend/resume;
- reparent;
- credit ledger history;
- hierarchy bulk actions.

Do not expose every backend endpoint just because it exists. Expose what is useful and consistent with the simplified model.

### Required tests

1. Create-admin happy path for each billing mode.
2. Phone required for new admin.
3. Legacy admin without phone can still be handled safely until backfilled.
4. Irrelevant fields hidden by mode.
5. Direct API still validates required fields/permissions.
6. Dashboard aggregates are numerically correct on seeded fixtures.
7. Week-over-week calculations correct at date boundaries/timezone handling.
8. Query count bounded; no per-admin/per-card N+1.
9. Freeze warning UX visible and actions blocked.

Stop after Stage 9.

---

## Stage 10 — Localization, Error Contract, and User Pagination/Performance

### Scope

Fix BUG-07, BUG-08, PERF-01 and perform a dashboard text/performance audit.

### Required implementation outcome

- stable backend error codes for relevant business errors;
- Persian frontend mapping;
- eliminate exposed raw English in normal Persian workflows;
- clean generic fallback;
- Unlimited displays correctly;
- user cards use server-side pagination with default 10, options 10/25/50, hard max 50;
- search/filter/sort server-side;
- review query counts and indexes.

### Required tests

1. Representative business error codes -> correct Persian messages.
2. Unknown error -> controlled Persian fallback while preserving developer diagnostics safely.
3. Unlimited semantic fields render correctly.
4. `page_size=10`.
5. `page_size=25`.
6. `page_size=50`.
7. `page_size=500` is rejected or clamped according to an explicit API contract; hard maximum must remain 50.
8. Search/filter/sort return correct total/page results.
9. Query count does not scale linearly per rendered card due to avoidable N+1.
10. Payload size matches requested page rather than loading entire dataset.

Stop after Stage 10.

---

## Stage 11 — Telegram Operations Logs, 30-Minute Backup, Health, and Limit Alerts

### Scope

Implement the reliable Telegram subsystem.

### Required implementation outcome

- configuration/secrets handled safely;
- detailed operation-log delivery;
- backup every 30 minutes by default;
- backup generation health tracked;
- remote Telegram delivery health tracked separately;
- retries for transient failures;
- non-empty/structural backup checks;
- file size/hash metadata where practical;
- no overlapping duplicate backup jobs;
- near-limit alerts with dedup/hysteresis;
- capability parity review of the legacy/default sales bot.

### Recommended implementation pattern

- business transaction commits -> durable outbox event;
- worker/scheduler delivers Telegram event;
- delivery attempt/result persisted sufficiently for retry/audit;
- backup scheduler uses a lock/lease when multiple app workers are possible.

### Required tests

1. Operation creates outbox event exactly once.
2. Telegram transient failure retries without duplicating business operation.
3. Successful delivery marks event delivered.
4. Secret token never appears in logs/API responses.
5. Backup scheduler interval default is 30 minutes.
6. Backup artifact non-empty validation.
7. Backup generation failure -> health failure event.
8. Telegram upload failure -> delivery failure while local generation remains correctly represented.
9. Retry sends the same backup/event safely, without creating duplicate business state.
10. Concurrent scheduler instances do not produce duplicate same-period backups when locking is required.
11. Near-limit threshold crossing sends alert.
12. Repeated checks inside same warning band do not spam duplicate alerts.
13. Recovery/re-arm behavior for alerts is tested.
14. Build a legacy bot capability parity matrix; mark missing parity explicitly.

### Real-environment evidence

If real Telegram credentials are unavailable, mocked/integration HTTP tests may pass but real delivery must be marked `NOT EXECUTED`. Do not fake a live PASS.

Stop after Stage 11.

---

## Stage 12 — Fork `Marzban-scripts` and Pin Node Installer

### Scope

External GitHub/operations stage. Do not execute unless the owner explicitly says to execute Stage 12 and Codex has authenticated GitHub access.

### Required implementation outcome

- fork `gozargah/Marzban-scripts` into the owner’s GitHub;
- configure/record upstream remote strategy;
- verify the required `marzban-node.sh` exists in the fork;
- update owner-facing install command to the fork;
- prefer stable tag/commit pinning over floating `master` if supported and maintainable;
- do not modify upstream repository.

### Required tests/evidence

1. Fork exists under correct owner account.
2. Upstream relationship/remotes are clear.
3. Raw script URL from fork resolves.
4. Script checksum/content matches intended upstream baseline before custom edits.
5. Node install command tested in a disposable/safe environment if available.
6. If actual node install is not executed, report `NOT EXECUTED`.

Stop after Stage 12.

---

## Stage 13 — Full Regression, Capability Audit, Migration Validation, and Release Gate

### Scope

No new product features unless a regression fix is necessary. This stage decides whether the current code is evidence-ready for release/deployment consideration.

### Required backend coverage

- backend unit tests;
- MarzHelp/accounting integration tests;
- hierarchy/resource delegation tests;
- billing-mode tests;
- Trial tests;
- bulk-action tests;
- freeze tests;
- authorization negative tests;
- API integration tests;
- backup/Telegram integration tests;
- MySQL migration tests on an actual supported MySQL instance.

### Required frontend coverage

- typecheck;
- lint if project uses it;
- unit/component tests;
- production build;
- critical create/edit/renew/admin-management flows;
- pagination/search/filter behavior;
- Persian localization smoke test;
- frozen-admin UX;
- dashboard metrics.

### Required Master/Node/Tunnel coverage

Where environment exists, perform real checks for critical flows involving:

- Master;
- Node;
- Tunnel/network path;
- subscription generation;
- Host/Inbound enforcement;
- device-limit behavior;
- traffic accounting/reconciliation.

If unavailable, mark each concrete scenario `NOT EXECUTED`.

### MySQL migration validation

Use disposable MySQL with representative pre-migration data.

At minimum:

1. upgrade from the expected pre-change revision to head;
2. verify data preservation/transformation;
3. application starts against upgraded schema;
4. critical reads/writes work;
5. downgrade test only if project migration policy supports it safely in disposable DB;
6. test constraints/indexes used by new code.

### Graphify final pass

Rebuild/re-run Graphify after all major changes. Compare blast radius and inspect unexpected new coupling/cycles/hot paths. Graphify is an audit aid, not the release proof.

### Final capability audit — English only

Produce a concise technical list with severity and status for the entire panel. Cover at minimum:

- authentication/session behavior;
- Owner/Admin/Sub-admin permissions;
- user create/edit/delete/renew;
- Plan create/edit/access;
- Inbound/Host behavior;
- subscriptions;
- Nodes/Master/Tunnel;
- device limit;
- traffic accounting;
- admin resource ledger;
- three billing modes;
- Trial creation/quota/cleanup;
- freeze;
- bulk actions;
- pagination/search/filter;
- localization/errors;
- dashboard metrics;
- Telegram logging;
- backups/health;
- near-limit alerts;
- legacy bot parity;
- API tokens and other retained admin-management features.

Use statuses `PASS`, `FAIL`, `NOT EXECUTED`, `UNCERTAINTY` with evidence.

### Release decision

Do not say “bug-free.” Report:

- verified invariants;
- failed invariants;
- tests not executed;
- unresolved uncertainty;
- migration risk;
- deployment prerequisites;
- rollback plan.

Stop after Stage 13.

---

## 12. Master Test Matrix

Codex should maintain tests close to the relevant domain and avoid duplicating the same assertion in many brittle layers.

| Area | Unit | DB integration | API negative | Frontend | Real env |
|---|---:|---:|---:|---:|---:|
| Renewal classification | Required | Required | Required | Useful | No |
| Deleted-user accounting | Required | Required | Useful | No | Device path useful |
| Owner/sudo enforcement | Required | Required | Required | Useful | No |
| Resource ledger | Required | Required | Required | Required | No |
| Billing modes | Required | Required | Required | Required | Traffic mode useful |
| Plan Inbound/Host | Required | Required | Required | Required | Subscription path useful |
| Trial | Required | Required | Required | Required | No |
| Hierarchy/delegation | Required | Required | Required | Required | No |
| Freeze | Required | Required | Required | Required | Session behavior useful |
| Bulk operations | Required | Required | Required | Required | No |
| Pagination | Useful | Required | Required | Required | No |
| Dashboard metrics | Required | Required | N/A | Required | No |
| Telegram outbox | Required | Required | N/A | N/A | Real send optional but distinct |
| Backup | Required | Required | N/A | N/A | Real archive/send strongly useful |
| Node installer | N/A | N/A | N/A | N/A | Required for real PASS |

---

## 13. Migration Discipline

Any schema change must include a deliberate migration plan.

### Before writing migration

- identify current head;
- inspect existing naming/index conventions;
- identify legacy/null data;
- determine safe default/backfill strategy;
- identify whether new enum values are portable across supported DBs;
- confirm MySQL behavior.

### Migration rules

1. Do not drop old columns in the same migration that introduces a replacement unless compatibility is proven and rollback is clear.
2. Prefer additive migration -> backfill -> code switch -> later cleanup for risky fields.
3. New phone requirement may initially be API/UI-required while legacy DB rows remain nullable.
4. Existing usernames must not be mass-renamed without explicit authorization.
5. Billing-mode migration must not assign a guessed commercial model to legacy admins.
6. Outbox/ledger tables need indexes for pending events, target admin, time, idempotency key/correlation ID as appropriate.
7. Any unique prefix must have a DB-level uniqueness guarantee if feasible, not only application-level random generation.
8. Test migration with representative collisions/nulls/legacy flags.

---

## 14. Concurrency and Idempotency Checklist

Explicitly reason about races for:

- two grants to same admin;
- grant + reclaim concurrently;
- parent delegating to two children concurrently;
- two Trial creates using last remaining Trial quota;
- same create/renew request retried;
- two workers reconciling Used Traffic;
- two backup schedulers firing simultaneously;
- two Telegram workers delivering same outbox event;
- random prefix generation collision;
- bulk job retry after partial failure.

Where correctness matters, enforce at DB/transaction level. A frontend disabled button is not concurrency control.

---

## 15. Performance Rules

1. Server-side pagination hard max 50 for user cards.
2. Do not fetch all users just to render 10.
3. Avoid N+1 queries in cards, admin dashboard, Plan/network selectors, bulk previews, and hierarchy trees.
4. Dashboard aggregation should use bounded queries and suitable indexes.
5. Large bulk actions should avoid holding one enormous transaction if the chosen semantics can safely use chunking; if per-item semantics are chosen, make results explicit.
6. Telegram delivery must not block core HTTP requests on slow network if a durable async/outbox path is available.
7. Backup generation must not overlap uncontrollably every 30 minutes.
8. Measure query count or SQL traces for critical list/dashboard flows rather than assuming ORM eager loading is correct.

---

## 16. Telegram Backup/Operations Runbook

This section is both implementation guidance and operational acceptance criteria.

### Configuration

Use the project’s established configuration mechanism. Secrets must come from environment/secret storage, not committed source.

Likely needed concepts:

- bot token;
- destination chat/channel ID;
- backup interval defaulting to 30 minutes;
- alert thresholds;
- retry/backoff settings;
- enable/disable flags only if product requirements permit.

### Backup state to track

At minimum conceptually:

- last attempt time;
- last generation success time;
- last delivery success time;
- last backup filename/ID;
- size;
- hash when practical;
- last error code/message;
- retry count;
- current health state.

### Health semantics

Recommended states:

- `HEALTHY` — recent backup generated and delivered within allowed window;
- `GENERATION_FAILED`;
- `DELIVERY_FAILED`;
- `STALE` — no successful remote backup within expected time window;
- `RUNNING` if useful operationally.

Do not mark healthy solely because a scheduler fired.

### Restore confidence

A non-empty archive is better than nothing but does not prove restore ability. In Stage 13, if practical, perform a restore smoke test in a disposable environment. Otherwise mark restore validation `NOT EXECUTED`.

---

## 17. Open Decisions — Do Not Guess

These are the main known decisions that may block later stages.

### D-01 — Seat renewal charging

When a 2-seat subscription is renewed, does it consume another 2 Seat Credits, a separate Renewal quota, or something else?

### D-02 — Referral reward unit

Referral should generate “profit/credit,” but there must be no cash/payment clutter in the panel. What persistent resource is credited: traffic, seat capacity, another internal credit, or another model?

### D-03 — Username prefix scope

Does `randomprefix_username` apply only to customers created by non-owner admins, or also to Owner-created customers and/or admin login usernames?

### D-04 — Freeze cascade

Does freezing an admin freeze only direct users, or the entire descendant admin subtree and all users below it?

### D-05 — Allocated-credit refund semantics

Current safe assumption is **no automatic refund** on delete/expiry/reduction. Confirm whether Owner-approved explicit refund/reclaim is the only refund mechanism.

### D-06 — Bulk target semantics

For “add time/volume to all users,” define whether expired, disabled, frozen-admin users, and Trial users are included by default or require explicit filters.

Codex should ask only when the relevant stage actually depends on one of these decisions.

---

## 18. Historical Test Evidence — Stale Until Re-Run

The prior review recorded the following historical observations. They are **not current PASS evidence** and must not be copied into a new release report without re-execution:

- a previous Graphify/project-memory report claimed roughly 128 backend tests passed;
- a small Plan-selector test set reportedly passed;
- a production dashboard build reportedly succeeded;
- real Master/Node/Tunnel traffic validation had not been completed;
- MySQL migration tests were not completed in one environment because MySQL was unavailable on the expected local port;
- a later broad backend collection attempt in another environment was blocked by a missing `apscheduler` dependency.

Treat all of these as historical context only. Re-run what matters in the actual implementation environment.

---

## 19. Stage Handoff / Execution Report Template

After each requested stage, append one entry under **Execution Ledger** using this exact structure.

```markdown
### Stage N — <name> — <date/time>

**Scope executed**
- ...

**Baseline**
- Commit before: `<sha>`
- Working tree before: clean / dirty
- Pre-existing local changes preserved: ...

**Changed files**
- `path`: reason

**Schema / migration changes**
- revision: ...
- data migration/backfill: ...

**Invariants addressed**
- ...

**Commands actually executed**
1. `<command>` -> PASS/FAIL
2. `<command>` -> PASS/FAIL

**Test evidence**
- PASS: ...
- FAIL: ...
- NOT EXECUTED: ...
- UNCERTAINTY: ...

**Performance / query evidence**
- ...

**Security negative tests**
- ...

**Known remaining risks**
- ...

**Dependencies / decisions before next stage**
- ...

**Commit/push/deploy status**
- NOT EXECUTED unless explicitly authorized.
```

Do not bury `NOT EXECUTED` items in prose. List them clearly.

---

## 20. Final Release Report Template

Stage 13 should end with a compact report containing:

```markdown
# Release Evidence Summary

## Candidate
- Commit: ...
- Version/tag: ...
- DB migration head: ...

## PASS
- ...

## FAIL
- ...

## NOT EXECUTED
- ...

## UNCERTAINTY
- ...

## Migration evidence
- ...

## Master/Node/Tunnel evidence
- ...

## Security/authorization evidence
- ...

## Accounting invariant evidence
- ...

## Backup/Telegram evidence
- ...

## Rollback prerequisites
- ...

## Recommendation
- READY FOR NEXT ENVIRONMENT / NOT READY
```

Never use “guaranteed bug-free.”

---

## 21. Scope Inventory — Everything Requested in This Conversation

This is a compact cross-check so no requirement disappears during implementation.

### Plans / network

- Inbound selector instead of comma-separated tag typing.
- Automatic live Inbound loading.
- Prevent invalid empty-Inbound Plans.
- Plan-specific Host selection and real subscription enforcement.
- Plan access controls (`allowed_admin_ids`, subtree semantics or current equivalents).
- Unlimited display semantics.

### Trials

- First-class Trial Plans.
- 1 GiB/1 day and 2 GiB/1 day examples.
- Unlimited 1-day Trial variants with 1 or 2 devices when accounting allows.
- Per-admin Trial quota.
- Grant/reclaim Trial quota.
- Idempotent Trial creation.
- Bulk Trial cleanup.

### Admin accounting models

- Seat/User Capacity Credit.
- Used Traffic.
- Allocated/Created Traffic.
- Seat capacity never auto-returns on user expiry.

### Restricted creation

- Seat admin Plan-only.
- Used/Allocated simplified form: username + volume + time + description.
- No admin-controlled Inbound/Host/device-count in restricted modes.
- Server-side enforcement.

### Admin resource management

- Replace raw absolute editing with Grant/Reclaim.
- Editable traffic credit through delta operations.
- Renewal quota management UI/API.
- Admin bulk grant such as `N GiB` gift.
- Auditable history.

### Hierarchy / referral

- Optional sub-admin creation.
- Child bounded by parent’s delegable resources and permissions.
- Referral relation separate from parent relation.
- Owner-only referral rate/config.
- No cash/payment UI subsystem.

### Identity

- Random stable per-admin prefix.
- Customer username format `prefix_requestedusername`.
- Collision prevention server-side.

### Admin UX

- Entire create-admin flow simplified/refactored.
- Mandatory phone for new admins.
- Discord removed from intended workflow.
- Freeze/unfreeze.
- Contact-support warning.
- Professional admin dashboard.
- Week-over-week growth/decline metrics.

### Bulk user operations

- Add volume to all users or selected-admin users.
- Add time to all users or selected-admin users.
- Safe batch semantics.

### Pagination/performance

- User card default 10.
- Options 10/25/50.
- Backend hard max 50.
- Server-side search/filter/sort.
- N+1/query audit.

### Localization

- Clean Persian errors/warnings.
- Stable backend error codes.
- Remove direct raw English normal UX.

### Existing correctness bugs

- False renewal classification.
- Renewal quota exhaustion UX/management.
- Device auto-delete accounting preservation.
- Legacy sudo policy bypass.
- Admin traffic-credit read-only semantics.

### Telegram / backup

- Detailed operation logs.
- 30-minute default backups.
- Send backup files to Telegram.
- Health checking.
- Generation vs delivery status.
- Failure alerts/retries.
- Near-admin-limit alerts with anti-spam.
- Review legacy sales-bot parity before removal.

### External scripts

- Fork `gozargah/Marzban-scripts` to owner GitHub.
- Maintain upstream sync path.
- Use owner fork for node installer.
- Prefer pinned tag/commit over floating master when practical.

### AI/tooling/process

- Use Graphify when helpful.
- Source code/DB/migrations/tests remain source of truth.
- Use Obsidian-compatible Markdown project memory.
- Keep context stage-focused.
- Do not delete files to reduce context.
- Only executed tests may be called PASS.
- Explicit `NOT EXECUTED` / `UNCERTAINTY` reporting.
- Full final panel capability audit in technical English.

---

## 22. Execution Ledger

> Codex: append stage reports here. Do not erase older entries. If this file becomes long, summarize redundant raw logs but keep exact commands/results, decisions, migration IDs, and unresolved risks.

_No implementation stage has been recorded in this consolidated runbook yet._

---

## 23. Current Authorization State at Time of This Runbook

This file itself is a planning/control artifact. Creating it does **not** authorize an implementation stage, database migration, GitHub fork, commit, push, deployment, production restart, or production data change.

When the owner gives this file to Codex and says **“Execute Stage 1”**, that authorizes code/test work necessary for Stage 1 only, subject to the safety rules above. The same applies independently to later stages.
