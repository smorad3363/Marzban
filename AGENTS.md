## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

Before broad source exploration, query Graphify first for architecture, symbols, imports,
dependencies, control/call flow, impact analysis, related code, and unfamiliar areas. Use
`graphify explain` for a known concept and `graphify path` for relationships, then inspect
only the source files identified by the graph. Compare the graph freshness commit with
`git rev-parse HEAD`; if stale, run `graphify update .` before relying on it. Do not load
the whole repository into context when a scoped graph query can narrow the work.

## UI and UX

- Use `$ui-ux-pro-max` as the primary and authoritative design skill for every UI/UX,
  frontend visual design, responsive layout, typography, color, spacing, motion,
  accessibility, and interaction decision in this project.
- Read `.codex/skills/ui-ux-pro-max/SKILL.md` before visual work and query its local
  scripts, data, and references when choosing or changing a design system.
- Do not use `design-taste-frontend` or any other UI/design skill in this project unless
  the user explicitly requests it.
- Preserve the existing framework, routes, API contracts, business logic, required
  libraries, and functional behavior while applying UI/UX Pro Max guidance.

## Mandatory session startup and release baseline

These rules apply at the start of every new chat, resumed chat, agent session, and
recovery after interruption. Complete them before editing source code, schema,
migrations, installer behavior, or release metadata.

1. Read `docs/ADMIN_HIERARCHY_ROADMAP_FA.md`, especially `وضعیت`, `نقطه دقیق ادامه`,
   `لاگ پیشرفت`, and the migration compatibility sections.
2. Inspect `git status --short --branch`, current HEAD, tags, remotes, and recent log.
   Preserve all user changes and never assume an untracked file is disposable.
3. Verify the remote state instead of remembering or guessing the latest version.
   Distinguish and record all of these separately:
   - newest immutable Git tag intended for installation;
   - commit referenced by that tag;
   - GitHub Release marked `Latest`;
   - GHCR image tag and immutable digest;
   - current branch/HEAD and rollback tag.
4. Use `git ls-remote --tags origin` or the GitHub tags page before selecting a
   baseline. If network verification fails, log the failure and stop release-sensitive
   work; never substitute a remembered version.
5. Before each meaningful change, update the roadmap's exact resume point. After the
   change, append affected files, tests, migration evidence, commit, errors, and next
   step to its progress log.

The snapshot verified on `2026-08-18` is Git tag `v4.8.0` at commit `fd73e03`; tag
`v4.7.1` points to commit `447d926`. This snapshot is historical context only and must
be reverified at the next session.

## Mandatory upgrade and database compatibility

Every new version must support in-place update through the existing Marzban update
command from all supported published database states, including an empty/fresh
database and databases containing legacy or partially populated data.

- Treat backward-compatible migration as a release blocker, not an optional test.
- Test fresh database to head, every schema-changing supported release to head, the
  latest install tag to head, and recovery from a partially applied MySQL migration.
- Preserve primary keys, Admin/User ownership, traffic/accounting values, credits,
  audit history, templates/plans, nodes, and configuration unless an explicitly logged
  migration rule says otherwise.
- Use expand/backfill/verify/contract. Add nullable columns and new tables first,
  backfill in bounded batches, verify invariants, and postpone destructive cleanup or
  stricter constraints to a later release after the rollback window.
- Because application rollback does not downgrade database migrations, the previous
  application image must continue to run against the upgraded schema. Do not drop,
  rename, narrow, or repurpose old columns in the same release that introduces their
  replacement.
- Migrations must be rerunnable or safely recoverable after MySQL partial DDL. Never
  assume transactional rollback reverted DDL.
- Never fabricate missing hierarchy data. Record how each backfilled relationship was
  chosen and expose the summary in the user-facing progress log.

For legacy Admin hierarchy, use this transition strategy unless the user changes it:

1. Schema migration adds nullable hierarchy/role fields and compatibility tables but
   does not require an Owner or parent immediately.
2. If no Owner has been explicitly selected, keep hierarchy enforcement disabled and
   preserve legacy `is_sudo` behavior so `marzban update` can complete successfully.
3. `marzban set-owner <username>` performs the ownership backfill atomically:
   - selected Admin becomes Owner;
   - every other legacy sudo becomes a direct Owner child with role Super Admin;
   - every legacy regular Admin without a valid parent becomes a direct Owner child
     with role Admin;
   - a missing, self-referencing, cyclic, or nonexistent parent is replaced by Owner
     and logged with a reason code;
   - Users with `admin_id=NULL` are assigned to Owner;
   - existing Admin IDs, User IDs, `users.admin_id` values that already reference a
     valid Admin, credits, and usage data are preserved.
4. Validate one Owner, no cycles, no orphan Admins, closure-table consistency, row
   counts, credit totals, and User ownership before enabling hierarchy enforcement.
5. On any failed invariant, rollback the data transaction, keep compatibility mode,
   start the application safely, and show the exact remediation in the progress log.

Every migration progress report shown to the user must include:

- source tag/commit and target tag/commit;
- source and target Alembic heads;
- backup path, timestamp, size/checksum, and restore-test status;
- database engine/version and fresh/existing/partial-data scenario;
- row counts before/after for affected tables;
- counts and reason codes for Owner/parent/User backfills;
- preserved IDs, orphan/cycle/null checks, credit/usage reconciliation;
- tests run, failures, operational risk, rollback compatibility, and exact next step.
