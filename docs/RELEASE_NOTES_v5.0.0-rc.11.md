# Marzban `v5.0.0-rc.11`

- `PLAN_ONLY` Admins now see only the Plan-based User creation path.
- Custom User creation stays hidden until the account policy explicitly allows `FREE_FORM`.
- `/api/user` rejects an empty proxy set before any User row is committed.
- Existing proxyless rows remain readable so `/api/users` recovers and operators can remove or repair the invalid User.
- No schema, migration, index, billing, credit, traffic, or ownership data changes are included.
