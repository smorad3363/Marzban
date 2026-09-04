# Versioned releases and rollback

Every published release uses an immutable Git tag and two permanent container
references:

- `ghcr.io/smorad3363/marzban:vX.Y.Z`
- `ghcr.io/smorad3363/marzban:sha-<12-character-commit-sha>`

The `latest` tag is only a moving pointer to the newest stable tagged release.
Prereleases never move `latest`. Older version and SHA tags remain available and
are not replaced by a later release.

## v5.1.0 Admin hierarchy, billing, network scope, and reliability

This stable release completes the Owner/Admin hierarchy workflow, reseller Plans
and Toman billing, atomic Host and Inbound synchronization, scoped subscriptions,
native device-limit controls, localized API errors, and Admin dashboard usability.
It also fixes multi-node usage settlement, prepaid zero-crossing suspension, Node
startup state synchronization, MySQL rollback index safety, and dashboard query
count growth.

Update to this release:

```bash
marzban update --version v5.1.0
```

Fresh-install this release with MySQL:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.1.0/scripts/marzban.sh)" @ install --version v5.1.0 --database mysql
```

## v5.0.0-rc.13 Admin simplification and reseller billing candidate

This candidate reduces the product roles to Owner and Admin, simplifies the Admin
form, and derives User creation mode from the commercial billing mode instead of
showing a redundant form control. Actual-usage Admins use custom User creation;
allocated-traffic and account-cap Admins create Users from priced Plans.

It adds Toman wallets, per-GiB and per-Plan reseller pricing, immutable monetary
ledger entries, monotonic lifetime traffic totals, Plan-only edit enforcement, and
read-only access for suspended Admins. Full client IP visibility is always enabled.

```bash
marzban update --version v5.0.0-rc.13
```

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.13/scripts/marzban.sh)" @ install --version v5.0.0-rc.13 --database mysql
```

## v5.0.0-rc.11 Plan-only creation and User-list recovery candidate

This candidate makes `PLAN_ONLY` fail closed in every User creation surface and
routes the Admin to available Plans. The raw User endpoint now rejects an empty
proxy set before commit. User responses tolerate an already-persisted proxyless
row so the User list loads again and the operator can remove or repair that row.

```bash
marzban update --version v5.0.0-rc.11
```

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.11/scripts/marzban.sh)" @ install --version v5.0.0-rc.11 --database mysql
```

## v5.0.0-rc.10 exact committed-dashboard image candidate

This candidate preserves the `rc.9` fixes and makes the release image consume the
exact committed local dashboard build. CI still performs a clean source build in an
isolated temporary directory and rejects any mutation of the committed dashboard.

```bash
marzban update --version v5.0.0-rc.10
```

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.10/scripts/marzban.sh)" @ install --version v5.0.0-rc.10 --database mysql
```

## v5.0.0-rc.9 install, update, Owner bootstrap, and build-parity candidate

This candidate makes `latest` in the installer/updater resolve to the newest
published GitHub release, including prereleases, and then uses that exact immutable
tag for the script, compose files, and application image. Fresh installation now
returns after its health check. `marzban create-owner USERNAME` securely creates or
repairs the first Owner. The dashboard dependency lock and committed build are also
verified by CI, and numeric inputs no longer use the invalid DOM number-selection
combination.

Update to the newest published release:

```bash
marzban update
```

Update to this exact candidate:

```bash
marzban update --version v5.0.0-rc.9
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.9/scripts/marzban.sh)" @ install --version v5.0.0-rc.9 --database mysql
```

Create the first Owner after installation:

```bash
marzban create-owner saji
```

## v5.0.0-rc.1 staging candidate

This prerelease is the staging candidate for the v5 feature set. It is not the
final `v5.0.0` release and does not deploy to any server automatically.

Update a staging server to this exact candidate:

```bash
marzban update --version v5.0.0-rc.1
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.1/scripts/marzban.sh)" @ install --version v5.0.0-rc.1 --database mysql
```

Take and verify a backup before updating. Production database evidence for this
project is MySQL 8.x with InnoDB.

## v5.0.0-rc.2 CI-fix candidate

This candidate keeps all `rc.1` application behavior. It corrects only CI test
orchestration: dedicated Stage 8–11 database tests no longer run against shared
`marzban_test`; each runs against its required isolated MySQL 8.0/InnoDB database.

Update a staging server to this exact candidate:

```bash
marzban update --version v5.0.0-rc.2
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.2/scripts/marzban.sh)" @ install --version v5.0.0-rc.2 --database mysql
```

## v5.0.0-rc.3 Admin usability candidate

This candidate simplifies the Persian Admin and Dashboard text, adds a separate
audited control for granting or reclaiming an Admin's credit, and fixes the public
`marzban set-owner USERNAME` server command in the maintained Marzban-scripts fork.

Update a staging server to this exact candidate:

```bash
marzban update --version v5.0.0-rc.3
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.3/scripts/marzban.sh)" @ install --version v5.0.0-rc.3 --database mysql
```

## v5.0.0-rc.4 Admin workflow and regression repair candidate

This candidate fixes Admin creation authorization, Plan-only user creation,
Trial quota reset, required freeze reasons, Admin bulk actions, Persian audit logs,
compact responsive forms, and the mobile Dashboard. It also adds the black-gold
Dashboard theme and per-Admin branding controls.

Update a staging server to this exact candidate:

```bash
marzban update --version v5.0.0-rc.4
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.4/scripts/marzban.sh)" @ install --version v5.0.0-rc.4 --database mysql
```

## v5.0.0-rc.5 MySQL credit reconciliation candidate

This candidate keeps the `rc.4` Admin and Dashboard changes and restores finite
delegated-credit reconciliation for an unrestricted Owner. Actual-usage parents
remain exempt from upfront delegated-credit charging and are charged from actual
descendant traffic.

Update a staging server to this exact candidate:

```bash
marzban update --version v5.0.0-rc.5
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.5/scripts/marzban.sh)" @ install --version v5.0.0-rc.5 --database mysql
```

## v5.0.0-rc.6 MySQL 8.0 downgrade safety candidate

This candidate keeps all `rc.5` behavior and restores a supporting
`account_status_id` foreign-key index before removing the newer composite index
during MySQL downgrade. This prevents MySQL error `1553` without dropping or
recreating the foreign key.

Update a staging server to this exact candidate:

```bash
marzban update --version v5.0.0-rc.6
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.6/scripts/marzban.sh)" @ install --version v5.0.0-rc.6 --database mysql
```

## v5.0.0-rc.7 Admin and Dashboard usability candidate

This candidate keeps the `rc.6` migration and accounting behavior, fixes Admin
policy persistence and status/credit actions, and ships the compact data-driven
Dashboard and Admin list. The UI uses the existing scoped APIs and preserves
Plan-only creation enforcement.

Update to this exact candidate:

```bash
marzban update --version v5.0.0-rc.7
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.7/scripts/marzban.sh)" @ install --version v5.0.0-rc.7 --database mysql
```

## v5.0.0-rc.8 Immutable prerelease update candidate

This candidate keeps all `rc.7` application behavior. It fixes prerelease update
parity so `marzban update --version` downloads both the container image and the
installed `marzban` script from the same immutable prerelease tag instead of using
the moving `master` branch for the script.

Update to this exact candidate:

```bash
marzban update --version v5.0.0-rc.8
```

Fresh-install this exact candidate from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.8/scripts/marzban.sh)" @ install --version v5.0.0-rc.8 --database mysql
```

## Release process

1. Update `VERSION` and `app.__version__`.
2. Commit and push `master`.
3. Create and push an annotated `vX.Y.Z` tag.
4. Wait for the GitHub `Release` workflow to finish.

The workflow builds multi-architecture images and publishes version and SHA tags.
Stable releases also move `latest`; prereleases do not. It then creates the
matching GitHub Release or prerelease with generated notes.

## Update

Update to the newest tagged release:

```bash
marzban update
```

Install or update to an exact version:

```bash
marzban update --version v4.9.8
```

Fresh-install an exact release directly from GitHub:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v4.9.8/scripts/marzban.sh)" @ install --version v4.9.8 --database mysql
```

The previous release remains directly installable:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v4.9.6/scripts/marzban.sh)" @ install --version v4.9.6 --database mysql
```

## Rollback

Roll back the application image while preserving the current database and data:

```bash
marzban rollback v4.5.2
```

Rollback from `v4.9.8` to the previous published release:

```bash
marzban rollback v4.9.6
```

You can also pin an immutable commit image:

```bash
marzban update --version sha-<12-character-commit-sha>
```

Rollback changes the application container only. It does not automatically
downgrade database migrations. Take a database backup before rolling back
across versions with incompatible schema changes.

The `v4.9.6` release adds nullable plan-category tables and a nullable plan
column. Application-image rollback to `v4.9.3` can leave that additive schema
in place; Alembic downgrade is not required for an emergency application rollback.
The `v4.9.8` repair does not add or change database schema, so an application-image
rollback to `v4.9.6` requires no database downgrade.
MySQL server downgrade is a separate operation and must use the physical backup
created before `marzban mysql-upgrade`; in-place MySQL downgrade is not supported.
