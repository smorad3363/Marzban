# Stage 4 device-limit integration evidence

Status: `IN PROGRESS — REAL TRAFFIC NOT EXECUTED`

This checklist covers `MRZ-DL-005` and the live integration proof for
`MRZ-DL-004`. It does not change the Marzban-node installer, plan UI, credit
policy, Xray inbound transport, firewall, routing, or database schema.

## Known versions

- Marzban: `v4.9.8`, commit `b45e3af663cd16d6dcca8492a6520b7e39db9d80`
- Stage 3 fixture Xray: `26.7.28`, commit `5ca6f4b`
- Installed Marzban-node: `NOT RECORDED`
- Installed node Xray: `NOT RECORDED`
- Service protocol: expected `rest`; runtime value `NOT RECORDED`
- Inbound transport: `NOT RECORDED`

Record runtime versions without changing the services:

```bash
docker compose -f /opt/marzban/docker-compose.yml exec -T marzban cat /code/VERSION
docker inspect marzban-node --format '{{.Config.Image}} {{.Image}}'
docker exec marzban-node xray version
docker inspect marzban-node --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^SERVICE_PROTOCOL='
```

Do not publish certificates, tokens, complete access logs, or full client IPs.

## Read-only preflight

1. Confirm master and node health in the panel.
2. Confirm the official node uses `SERVICE_PROTOCOL=rest` and its configured
   service/API ports.
3. Confirm Xray is started on master and node.
4. As Owner/sudo, snapshot:

```text
GET /api/core
GET /api/nodes
GET /api/device-limit/settings
GET /api/device-limit/diagnostics
GET /api/device-limit/users/<test-username>
GET /api/device-limit/incidents?username=<test-username>
```

The diagnostic baseline must show `runtime_enabled=true`,
`ip_detection_enabled=true`, and collectors for the tested path: `master` for
the main core or `node:<id>` for a node. Counters are process-local, so record
them before and after each scenario.

## Controlled test

Use one dedicated disposable user with `concurrent_user_limit=1`. Do not reuse a
production user. Use successful accepted traffic above
`min_successful_connections`.

### Scenario A — one public egress IP

1. Connect only client A.
2. Generate accepted traffic until the hit threshold is exceeded.
3. Capture a redacted raw access-log sample showing its source field and email.
4. Capture diagnostics and user summary.

Pass conditions:

- `recorded_events` increases;
- `live_active_ip_count=1`;
- correct `live_source_nodes` value;
- no new penalty incident;
- user remains active and can connect.

### Scenario B — two public egress IPs

1. Keep client A active.
2. Connect client B through a genuinely different public egress IP.
3. Generate accepted traffic from both clients.
4. Wait the configured check interval and handoff grace, while both remain
   active.
5. Capture the same evidence plus incident/audit and DB status.

Pass conditions:

- `live_active_ip_count=2` before enforcement;
- a pending handoff appears before grace expiry;
- configured penalty appears only after grace expiry;
- incident contains the correct `source_nodes` and observed count;
- actual connectivity matches the stored user status.

Repeat A and B first on `master`, then on one official node.

## Database evidence

Run read-only queries only. Substitute the test username using a bound parameter
in the DB client or ORM; do not build SQL from untrusted input.

```sql
SELECT id, username, status, concurrent_user_limit, admin_id
FROM users
WHERE username = ?;

SELECT user_id, violation_count, current_stage, penalty_status, blocked_until,
       active_ip_count, last_reason, pending_handoff_started_at,
       pending_source_nodes
FROM device_limit_user_states
WHERE user_id = ?;

SELECT id, user_id, admin_id, username, stage, action, configured_limit,
       observed_count, source_nodes, event_state, risk_score, reason,
       resolved_at, created_at
FROM device_limit_incidents
WHERE user_id = ?
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

These predicates use primary/foreign-key paths and the existing incident
user/time index. No migration or new index is justified for this test.

## Observed tunnel configuration

The operator-provided topology note contains WireGuard plus `ip6gre`, and these
source-changing rules:

```text
iptables -t nat -A POSTROUTING -o ens34 -j MASQUERADE
iptables -t nat -A POSTROUTING -s 172.16.0.0/24 -j SNAT --to-source 192.168.13.1
iptables -t nat -A POSTROUTING -j MASQUERADE
```

Static conclusion: forwarded packets matching these rules lose their original
source address. This does not prove which address the production Xray inbound
actually sees. Capture the Xray access-log source field through the real path.

If Xray sees `192.168.13.1`, another private/tunnel address, or one shared proxy
address, IP concurrency cannot distinguish end users on that path. Marzban must
not infer the original IP from the destination or an arbitrary
`X-Forwarded-For` value.

Only evaluate PROXY protocol after recording exact Xray version, inbound
transport, and a trusted upstream that sends PROXY protocol v1/v2. Use a
dedicated compatible listener. Enabling `acceptProxyProtocol=true` without a
matching sender rejects ordinary connections.

## Installer decision

`NODE INSTALLER CHANGE: NOT REQUIRED`

Current panel code consumes REST-node log batches from the node `/logs`
WebSocket, and local integration tests cover that batch boundary. The installer
decision gate remains unmet until a correctly configured official node produces
valid local Xray logs but its supported REST API fails to deliver them to the
panel.

## Evidence still required for PASS

- real accepted traffic on master from one and two public egress IPs;
- same test on an official Marzban Node;
- installed node/Xray versions and exact transport;
- before/after diagnostics, state, incident, audit and connectivity evidence;
- redacted source-field observation through the production tunnel.
