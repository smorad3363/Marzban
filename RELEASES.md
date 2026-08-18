# Versioned releases and rollback

Every published release uses an immutable Git tag and two permanent container
references:

- `ghcr.io/smorad3363/marzban:vX.Y.Z`
- `ghcr.io/smorad3363/marzban:sha-<12-character-commit-sha>`

The `latest` tag is only a moving pointer to the newest tagged release. Older
version and SHA tags remain available and are not replaced by a later release.

## Release process

1. Update `VERSION` and `app.__version__`.
2. Commit and push `master`.
3. Create and push an annotated `vX.Y.Z` tag.
4. Wait for the GitHub `Release` workflow to finish.

The workflow builds multi-architecture images, publishes the version, SHA and
`latest` tags, then creates a GitHub Release with generated notes.

## Update

Update to the newest tagged release:

```bash
marzban update
```

Install or update to an exact version:

```bash
marzban update --version v4.6.1
```

Fresh-install an exact release directly from GitHub:

```bash
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/smorad3363/Marzban/master/scripts/marzban.sh)" @ install --version v4.9.0 --database mysql
```

The previous release remains directly installable:

```bash
sudo bash -c "$(curl -sL https://raw.githubusercontent.com/smorad3363/Marzban/master/scripts/marzban.sh)" @ install --version v4.8.0 --database mysql
```

## Rollback

Roll back the application image while preserving the current database and data:

```bash
marzban rollback v4.5.2
```

Rollback from `v4.9.0` to the previous release:

```bash
marzban rollback v4.8.0
```

You can also pin an immutable commit image:

```bash
marzban update --version sha-<12-character-commit-sha>
```

Rollback changes the application container only. It does not automatically
downgrade database migrations. Take a database backup before rolling back
across versions with incompatible schema changes.

The `v4.9.0` migration only adds compatible columns/indexes and preserves the
legacy quota columns used by `v4.8.0`, so application-image rollback to
`v4.8.0` does not require a schema downgrade.
