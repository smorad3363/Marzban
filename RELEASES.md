# Versioned releases and rollback

Every published release uses an immutable Git tag and two permanent container
references:

- `ghcr.io/smorad3363/marzban:vX.Y.Z`
- `ghcr.io/smorad3363/marzban:sha-<12-character-commit-sha>`

The `latest` tag is only a moving pointer to the newest stable tagged release.
Prereleases never move `latest`. Older version and SHA tags remain available and
are not replaced by a later release.

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
