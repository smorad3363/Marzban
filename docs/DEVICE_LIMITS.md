# Native device limits

Marzban `v4.6.0` integrates device-slot and concurrent-IP enforcement directly
into the panel. MarzHelp and V2IpLimit are not required for this feature, and
the standard Marzban node installation command is unchanged.

## Subscription modes and permissions

Sudo administrators can grant each managed admin any combination of these
modes:

- limited traffic and unlimited devices
- unlimited traffic and limited devices
- limited traffic and limited devices
- unlimited traffic and unlimited devices

`concurrent_user_limit: null` means unlimited devices. A positive integer
creates that many persistent device slots. The fully unlimited mode is not
granted to non-sudo admins by default.

Each slot has standard VLESS/VMess UUID or Trojan/Shadowsocks password
credentials and its own subscription URL. Slot 1 preserves the user's existing
credential and subscription URL. Extra slots use independent credentials.
Sharing one slot is detected by concurrent public-IP activity.

## Runtime behavior

The engine reads accepted Xray records directly from the main core and connected
Marzban nodes. Enabling it from the sudo-only Device Limits page applies Xray
`info` logging and restarts the core and connected nodes once. Disabling it does
not restart Xray and releases temporary device-limit penalties.

Accepted records remain in bounded memory. The database stores settings, slots,
current penalty state, audit records and incidents only. Defaults are:

- detector check interval: 60 seconds
- active-IP window: 300 seconds
- minimum accepted records per active IP: 3
- full IP retention: 7 days
- incident retention: 90 days
- admin audit retention: 180 days
- automatic deletion: disabled
- penalties: warning, 5 minutes, 15 minutes, 60 minutes, permanent disable

The rotated JSONL event file is stored under
`/var/lib/marzban/logs/device-limit/events.jsonl`; IP addresses in this file are
masked. Full addresses exist only in retention-managed database incidents.

This mechanism counts public source IPs, not physical hardware identifiers.
Device slots isolate credentials, but copied credentials can still be shared;
the IP detector is the enforcement guard for that case. Tunnels, CGNAT, roaming
and rapidly changing mobile IPs can affect the observed count.

## API and ddbot integration

Existing Marzban endpoints and payloads are unchanged. ddbot should keep using
the normal authenticated user creation endpoint and set the existing field:

```json
{
  "username": "customer-123",
  "data_limit": 0,
  "concurrent_user_limit": 2
}
```

Rules:

- `concurrent_user_limit: null` selects unlimited devices.
- A positive integer selects a finite device count and creates that many slots.
- `data_limit: 0` keeps Marzban's existing unlimited-traffic meaning.
- A positive `data_limit` keeps Marzban's existing limited-traffic meaning.
- A forbidden admin mode or device count returns the existing policy error
  response; ddbot should show its `detail` to the operator.

After creation, ddbot can retrieve all device-slot subscription URLs from the
additive endpoint:

```http
GET /api/device-limit/users/{username}
Authorization: Bearer <admin-token>
```

Only sudo or the owning admin can access that user. Existing API consumers that
do not use device slots continue to work without changes.

Additional native endpoints use only the `/api/device-limit` namespace:

- `GET|PUT /api/device-limit/settings` (sudo)
- `GET|PUT /api/device-limit/penalty-stages` (sudo)
- `GET /api/device-limit/incidents`
- `GET /api/device-limit/users/{username}`
- `PUT /api/device-limit/users/{username}/slots/{slot_index}`
- `POST /api/device-limit/users/{username}/reset-strikes`
- `POST /api/device-limit/users/{username}/unblock`

## Upgrade and rollback

Back up `/var/lib/marzban` before the first upgrade. Upgrade to this exact,
immutable image with:

```bash
marzban update --version v4.6.0
```

After validation, following `latest` is also supported:

```bash
marzban update
```

Application rollback:

```bash
marzban rollback v4.5.2
```

Rollback changes the application image, not the database schema. The new tables
are additive and ignored by `v4.5.2`; keep the backup for a full schema rollback.
