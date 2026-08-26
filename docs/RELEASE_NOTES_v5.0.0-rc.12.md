# Marzban `v5.0.0-rc.12`

- Product roles are reduced to Owner and Admin; legacy `SUPER_ADMIN` rows remain migration-compatible.
- Admin creation and editing use one compact centered form without a role selector, advanced accordion, or User-creation-method display.
- User creation mode is derived from billing mode: actual usage allows custom creation; allocated traffic and account-cap billing require priced Plans.
- Toman wallets support parent-to-child credit transfer, per-GiB actual-usage pricing, per-Plan reseller prices, resale-floor validation, and immutable ledger entries.
- Owner sees monotonic lifetime consumed and created traffic totals even after a User is deleted.
- Plan-only Admins cannot directly increase User traffic, expiry, or device limits; Owner retains full control.
- Suspended Admins can sign in and inspect their Users and freeze reason, but all mutations stay blocked.
- Full client IP visibility is always enabled.

Update this exact candidate:

```bash
marzban update --version v5.0.0-rc.12
```

Fresh-install this exact candidate:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban/v5.0.0-rc.12/scripts/marzban.sh)" @ install --version v5.0.0-rc.12 --database mysql
```
