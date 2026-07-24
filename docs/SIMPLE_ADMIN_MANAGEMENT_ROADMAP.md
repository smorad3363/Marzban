# Simple Admin Management Roadmap

This is the active implementation plan for `feature/simple-admin-management`.
Every milestone requires narrow scope, focused tests, one commit, one push, a clean working tree, and a mandatory stop before the next milestone.
New work is MySQL 8.0/InnoDB only; SQLite compatibility is not required.

## Milestone 0 — Project pivot

- Isolated branch
- New repository instructions
- New roadmap
- New state file
- Old roadmap deferred
- MySQL-only policy for new work

## Milestone 1 — Admin identity foundation

- `owner` and `reseller` roles
- `active` and `suspended` statuses
- Simple JSON permission overrides
- Existing sudo admins map to owner
- Existing non-sudo admins map to reseller
- Existing `is_sudo` compatibility remains
- Small deny-by-default permission helper
- Final active owner protection
- One MySQL-compatible migration
- Focused tests

## Milestone 2 — User read isolation

- Owner reads all users
- Reseller reads only users matching `owner_admin_id`
- Protect user detail, list, count, statistics, and usage
- Out-of-scope detail returns concealed `404`

## Milestone 3 — User mutation permissions

Protect only:

- Create
- Edit
- Delete
- Reset usage
- Revoke subscription
- Unlimited-user creation
- On-hold-user creation

## Milestone 4 — Admin management API

Minimal owner-only endpoints for:

- List admins
- Create admin
- Change password
- Change role
- Change status
- Change permissions
- Delete admin when safe

## Milestone 5 — Simple admin limits

Only:

- Maximum total users
- Maximum active users
- Maximum traffic per user
- Maximum expiration days
- Maximum unlimited users

## Milestone 6 — Minimal frontend

Only:

- Admin list
- Create/edit admin modal
- Role selector
- Status selector
- Permission toggles
- Limit fields

## Milestone 7 — Final validation

- MySQL migration validation
- Backend regressions
- Frontend build
- Test-server deployment
- Compatibility report

## Milestone gate

For each milestone:

- Keep scope narrow.
- Add and run focused tests.
- Create exactly one milestone commit.
- Push that commit once to `origin`.
- Leave a clean working tree.
- Stop before starting the next milestone.
