# Phase 1D Persistence, Identity, and Version Baselines

Status: confirmed architecture and evidence baseline only. This phase changes no
application behavior, database schema, migration, pool setting, index, version,
tag, or release.

## Authoritative decisions

### Database authority and production topology

- MySQL is the authoritative production database and every production table
  must use InnoDB.
- SQLite is limited to development, lightweight installations, and fast
  compatibility tests. It is not evidence for production locking, concurrency,
  migration, quota, billing, or capacity behavior.
- The application and MySQL communicate over a private or local trusted
  network. The checked-in Compose topology binds MySQL to `127.0.0.1`.
- The initial topology has one Marzban application instance and one
  authoritative scheduler/usage-job worker.
- Multiple API replicas are permitted only after every shared job uses
  database-backed claims, leases, or distributed locking.
- No application replica may independently execute the same billing or usage
  job without coordination.

MySQL 8.0 uses InnoDB as its default storage engine, but production acceptance
must still verify `@@default_storage_engine` and every application table through
`information_schema.tables`. The project must not rely only on the server
default. See the [MySQL 8.0 InnoDB documentation](https://dev.mysql.com/doc/refman/8.0/en/innodb-introduction.html).

### Environment SUDOERS identity policy

- Every configured SUDOERS username maps one-to-one to its own durable `Admin`
  database identity.
- Each mapped identity initially receives the `owner` role.
- Multiple SUDOERS must never share an anonymous or common actor.
- Environment-managed passwords and secrets remain environment-managed and
  must not be copied into database password fields or audit data.
- The durable database identity supplies ownership, audit, and actor
  references.
- A username collision between an environment SUDOER and an existing database
  admin is an explicit conflict. It must be reported and must never be silently
  merged.
- A SUDOERS-backed database identity cannot be deleted while its username
  remains active in environment configuration.
- Phase 2 backfill must stop if any configured SUDOER lacks a unique durable
  identity or if any conflict remains unresolved.

### Version authority

- `app/__init__.py` declares `0.8.4`; this remains the authoritative current
  application version.
- No version, tag, or release changes are authorized by Phase 1D.
- Repository tags `v1`, `v2`, and `v3` remain historical/deployment labels
  until release governance is resolved.

## Repository connection and driver evidence

### URL and driver

- `config.py` defaults `SQLALCHEMY_DATABASE_URL` to
  `sqlite:///db.sqlite3`; the inspected checkout has no local `.env`, so its
  effective local URL is that SQLite default.
- `scripts/marzban.sh` provisions production MySQL with the URL shape
  `mysql+pymysql://marzban:<redacted>@127.0.0.1:3306/marzban`.
- The SQLAlchemy dialect/DBAPI driver is therefore `mysql+pymysql`.
- `requirements.txt` pins `PyMySQL==1.1.1`, `SQLAlchemy==2.0.36`, and
  `alembic==1.14.0`.
- No password or complete credential-bearing URL was copied into this
  evidence document.

### MySQL version evidence

- `docker-compose.yml` and the approved installer path use `mysql:8.0`.
- This is a floating MySQL 8.0 tag, not an exact patch version or immutable
  digest.
- This Windows evidence host has no `mysql`, `mysqld`, or `docker` executable,
  so a live server version could not be queried here.
- Before Phase 2 migration testing, capture `SELECT VERSION()` and the image
  digest from the actual MySQL test environment. Pinning a tested patch/digest
  is a later deployment candidate, not a Phase 1D configuration change.

## SQLAlchemy pool and timeout evidence

For non-SQLite URLs, `app/db/base.py` creates the engine with:

- `pool_size=10` from `SQLALCHEMY_POOL_SIZE`;
- `max_overflow=30` from the currently misspelled but established
  `SQLIALCHEMY_MAX_OVERFLOW` setting;
- at most 40 simultaneous checked-out/overflow connections per application
  engine;
- `pool_timeout=10` seconds;
- `pool_recycle=3600` seconds;
- no `pool_pre_ping` argument, so pessimistic pre-ping is not enabled;
- no explicit `pool_use_lifo`.

Alembic online migrations use `NullPool`, independently of the application
pool. SQLAlchemy documents the meaning of the pool parameters and recommends a
recycle or pre-ping strategy for server-side stale-connection timeouts:
[SQLAlchemy connection pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
and [engine configuration](https://docs.sqlalchemy.org/en/20/core/engines.html).

No DBAPI timeout is passed through the URL or `connect_args`. Under the pinned
PyMySQL behavior this leaves:

- `connect_timeout=10` seconds;
- `read_timeout=None`;
- `write_timeout=None`.

The driver defaults are documented by
[PyMySQL Connection](https://pymysql.readthedocs.io/en/latest/modules/connections.html).

Evidence-backed later candidates:

1. Measure pool checkout latency, exhaustion, stale-connection failures, and
   MySQL `max_connections` at the staged workloads before changing pool size,
   overflow, timeout, recycle, or pre-ping.
2. Define bounded connect/read/write timeouts from observed request/job
   durations and failure tests; do not select values without those results.
3. Account for the configured pool independently in every future API or worker
   process before allowing replicas.

## Transaction isolation and deadlock evidence

- Neither the SQLAlchemy engine nor the MySQL Compose command sets transaction
  isolation.
- The effective production isolation therefore comes from the MySQL server.
  MySQL 8.0 documents InnoDB's default as `REPEATABLE READ`.
- The exact production value must be captured with
  `SELECT @@transaction_isolation` before Phase 2 tests.
- `app/jobs/record_usages.py::safe_execute` contains a maximum of three
  immediate retries for driver error code `1213`, limited to that usage-write
  helper.
- There is no central transaction-level retry for deadlock `1213` or lock wait
  timeout `1205`, no jitter/backoff policy, and no shared idempotency contract.
- The helper catches `pymysql.err.OperationalError` around SQLAlchemy
  execution; later fault tests must confirm whether SQLAlchemy's wrapped
  exception reaches that handler. This must not be assumed.

InnoDB detects a deadlock and rolls back a victim by default, and applications
must be prepared to retry the complete transaction. See
[MySQL InnoDB deadlocks](https://dev.mysql.com/doc/mysql/8.0/en/innodb-deadlocks.html)
and [deadlock handling](https://dev.mysql.com/doc/refman/8.0/en/innodb-deadlocks-handling.html).

Evidence-backed later candidates:

1. Keep a fixed lock order and short transactions.
2. Retry the entire idempotent transaction with a strict bound and measured
   backoff for `1213` and, if approved by fault evidence, `1205`.
3. Record retry count, terminal failure, transaction type, and run/request ID
   without query parameters or secrets.
4. Verify `@@innodb_deadlock_detect`, `@@innodb_lock_wait_timeout`, and deadlock
   logs in the production-like MySQL test environment.
5. Do not change isolation until concurrency tests compare correctness,
   locking, deadlocks, and throughput.

## Slow-query evidence

The checked-in MySQL Compose service specifies:

- `slow_query_log=1`;
- `slow_query_log_file=/var/lib/mysql/slow.log`;
- `long_query_time=2`;
- `general_log=0`.

The effective values and `log_output` still require a live server query. MySQL
documents that the slow log captures statements exceeding `long_query_time`
when the effective log destination permits it:
[MySQL slow query log](https://dev.mysql.com/doc/refman/8.0/en/slow-query-log.html).

Later phases may use sanitized slow-log summaries and `EXPLAIN`/query-plan
evidence. They must not log credentials, complete subscription URLs, tokens, or
secret-bearing query parameters.

## Current index evidence

The current model metadata and migration head declare:

- `admins`: primary key `id`; unique index `ix_admins_username(username)`.
- `users`: primary key `id`; unique index `ix_users_username(username)`.
- `users.admin_id`: ownership foreign key with no explicit model index.
- `users.status`, `expire`, `data_limit_reset_strategy`,
  `last_status_change`, and `auto_delete_in_days`: no explicit model indexes.
- `admin_usage_logs.admin_id` and `user_usage_logs.user_id`: foreign keys with
  no explicit model indexes.
- `node_user_usages`: primary key `id`; unique constraint
  `(created_at, user_id, node_id)`.
- `node_usages`: primary key `id`; unique constraint
  `(created_at, node_id)`.
- `notification_reminders.user_id`: foreign key with no explicit model index;
  reminder lookups also filter `type` and optionally `threshold`.

MySQL may create supporting indexes for foreign keys, so model declarations are
not sufficient proof of the live schema. Before proposing an index, capture
`SHOW INDEX`, the relevant query shape, `EXPLAIN`/`EXPLAIN ANALYZE`, and staged
before/after results.

Evidence-backed index investigations for later phases, not approved indexes:

1. ownership-scoped user list/count/status queries using `admin_id`, `status`,
   and ordering;
2. lifecycle/reset jobs filtering status, reset strategy, expiry, and
   last-status-change fields;
3. per-user and per-node usage queries filtering user/node plus time ranges;
4. notification reminder lookup and expiry cleanup;
5. usage-job duplicate detection and update predicates.

No index is added or changed in Phase 1D.

## Alembic evidence

The deterministic Gate G1D command returned exactly one head:

`63fbd07b9f14 (head)`

The command used the Phase 1B isolated Python environment and a synthetic
SQLite URL only to load repository migration metadata. No migration was
created or applied.

## Production verification capture

Run these read-only queries against the production-like MySQL 8.0 test
environment before Phase 2 migration execution:

```sql
SELECT VERSION();
SELECT @@version_comment;
SELECT @@transaction_isolation;
SELECT @@default_storage_engine;
SELECT @@innodb_deadlock_detect;
SELECT @@innodb_lock_wait_timeout;
SELECT @@max_connections;
SELECT @@slow_query_log;
SELECT @@slow_query_log_file;
SELECT @@long_query_time;
SELECT @@log_output;

SELECT table_name, engine
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY table_name;
```

Also capture sanitized `SHOW INDEX` output for the tables listed above. These
commands collect evidence; they do not authorize configuration changes.

## Gate G1D acceptance

Gate G1D passes when all of the following hold:

1. exactly one Alembic head is recorded as `63fbd07b9f14`;
2. MySQL/InnoDB production authority and the limited SQLite role are explicit;
3. the single-instance/single-authoritative-worker initial topology and the
   future replica coordination boundary are explicit;
4. current URL/driver, pool, timeout, isolation, deadlock, slow-query, index,
   and MySQL version evidence is recorded with unknown live values identified;
5. the one-to-one durable SUDOERS identity policy is explicit;
6. version `0.8.4` remains authoritative and tags/releases are unchanged;
7. no database, migration, application behavior, pool, or index mutation is
   present.

## Decisions and evidence required before Phase 2

The topology and SUDOERS identity policies are now decided. Phase 2 still
requires:

1. an approved destination for legacy users whose `admin_id` is null;
2. an approved immutable-creator backfill rule and provenance marker;
3. a production-like MySQL 8.0 test instance with exact patch/image digest and
   the read-only server/schema capture above;
4. confirmation that every configured SUDOERS username has a conflict-free
   durable identity mapping.

Items 3 and 4 are evidence/preconditions rather than permission to implement
Phase 2. Phase 2 must not start without a new explicit instruction.
