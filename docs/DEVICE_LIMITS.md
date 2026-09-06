# Native device limits

Marzban `1.0.6` integrates device-slot and concurrent public-IP enforcement
directly into the panel. MarzHelp and V2IpLimit are not required for this
feature.

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

For a finite device limit, both rules are enforced:

1. the total number of concurrently active public IPs must not exceed
   `concurrent_user_limit`;
2. one device-slot credential may be active from only one public IP at a time.

The second rule is important. For example, if a user has a limit of `2`, sharing
slot 1 between two IPs is still a violation even when slot 2 is unused. Older
implementations that checked only the total number of unique IPs missed this
case.

## Runtime behavior

The engine reads accepted Xray records directly from the main core and connected
Marzban nodes. Enabling it from the sudo-only Device Limits page applies Xray
`info` logging and restarts the core and connected nodes once. Disabling it does
not restart Xray and releases temporary device-limit penalties.

The log parser accepts the common main-core and node source formats, including
IPv4, IPv6 and IPv4-mapped IPv6. IPv4-mapped addresses are canonicalized to IPv4
before counting so the same client is not counted twice only because two Xray
runtimes formatted the address differently.

The finite-user cache refreshes every 10 seconds. When the feature is newly
enabled or changed from slots-only mode, the collector records activity while
the cache warms instead of silently dropping those first records.

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
Tunnels, CGNAT, roaming and rapidly changing mobile IPs can affect the observed
count.

## Recommended node installation

Use the fork's multi-instance-safe installer on every node server:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/smorad3363/Marzban-scripts/master/install-node.sh)"
```

The installer asks for a unique instance name, Client Certificate,
`SERVICE_PORT`, `XRAY_API_PORT`, and REST protocol selection. It rejects ports
that are currently listening as well as ports reserved by other installed node
compose files. This means a stopped node cannot accidentally have its ports
reused by another instance.

If more than one node is installed on the same server, the suggested names are
`marzban-node`, `marzban-node2`, `marzban-node3`, and so on. Each instance gets
its own `/opt/<instance>`, `/var/lib/<instance>`, container name and management
command.

After installation, add the reported IP, `SERVICE_PORT` and `XRAY_API_PORT` to
the main panel. The panel's device-limit collector consumes accepted Xray log
records from connected nodes, so keep Device Limits enabled in `hybrid` or `ip`
mode when concurrent-IP enforcement is required.

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

Back up `/var/lib/marzban` before upgrading. The source version for this fix is
`1.0.6`. Once the corresponding immutable image/tag is published, deployments
that pin release images should use that `1.0.6` tag rather than an older device
limit build.

Following `latest` remains possible where the deployment workflow publishes
master builds:

```bash
marzban update
```

Application rollback changes the application image, not the database schema.
Keep the data backup for a full schema rollback.
