# Authorization Entry-Point and Bypass-Risk Inventory

Phase: `1C`

Status: inventory only; no authorization enforcement is implemented here.

## Policy vocabulary

- Current callers are `anonymous`, `subscription bearer`, `admin bearer`, `environment sudo`, `local operator`, `Telegram chat`, `dashboard admin`, and `scheduler`.
- Current guards are `public`, `get_validated_sub`, `Admin.get_current`, `get_validated_user`, `Admin.check_sudo_admin`, manual WebSocket token validation, Telegram `is_admin`, or `none`.
- Target permissions are the roadmap catalog. Operations without a precise catalog permission are marked `owner/system policy`; Phase `1D` must decide whether to add explicit core/system permissions.
- Target ownership rule `owned` means the caller may access only users in its centrally resolved scope. `global` means owner-only, unless an explicit scoped system policy is approved.
- Future test owners identify the suite that must prove enforcement in later phases. They are not current enforcement.

## REST and WebSocket entry points

| Entry point | Caller | Current guard | Bypass or authorization risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| `admin_token` — `POST /api/admin/token` | anonymous credentials | password validation against environment or database | environment and database identities have different lifecycle; brute-force policy is outside this guard | public authentication policy | identity only | `tests/security/test_authentication.py` |
| `create_admin` — `POST /api/admin` | admin bearer | `Admin.check_sudo_admin` | coarse sudo boolean; no named permission or audit reason | `admin.create` | global | `tests/security/test_admin_authorization.py` |
| `modify_admin` — `PUT /api/admin/{username}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | coarse sudo; can change password, sudo flag and notification credentials | `admin.update`; `admin.suspend` when activation exists | global; protected owner invariants | `tests/security/test_admin_authorization.py` |
| `remove_admin` — `DELETE /api/admin/{username}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | hard delete; ownership consequences and last-owner invariant are not centralized | `admin.suspend` initially; owner-only deletion policy | global; owned users require explicit reassignment | `tests/security/test_admin_authorization.py` |
| `get_current_admin` — `GET /api/admin` | admin bearer | `Admin.get_current` | returns current identity but has no active/suspended permission evaluation | `admin.read` for self | self | `tests/security/test_admin_authorization.py` |
| `get_admins` — `GET /api/admins` | admin bearer | `Admin.check_sudo_admin` | coarse sudo; exposes all admin metadata | `admin.read` | global | `tests/security/test_admin_authorization.py` |
| `disable_all_active_users` — `POST /api/admin/{username}/users/disable` | admin bearer | target lookup plus `Admin.check_sudo_admin` | bulk mutation uses target admin but no per-item result, reason, or central scope | `user.bulk_update` and `user.change_status` | users owned by selected admin | `tests/security/test_bulk_authorization.py` |
| `activate_all_disabled_users` — `POST /api/admin/{username}/users/activate` | admin bearer | target lookup plus `Admin.check_sudo_admin` | same bulk bypass class; manual and future billing states can be conflated | `user.bulk_update` and `user.change_status` | users owned by selected admin | `tests/security/test_bulk_authorization.py` |
| `reset_admin_usage` — `POST /api/admin/usage/reset/{username}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | aggregate mutation lacks reason/audit and named accounting policy | `admin.adjust_balance` | global target admin | `tests/security/test_admin_accounting_authorization.py` |
| `get_admin_usage` — `GET /api/admin/usage/{username}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | coarse sudo; no self-scoped reseller view | `quota.read` | self, or global owner | `tests/security/test_admin_accounting_authorization.py` |
| `core_logs` — `WS /api/core/logs` | token in query/header | manual `Admin.get_admin` plus `is_sudo` | query token may leak; guard is duplicated outside dependencies | owner/system policy | global | `tests/security/test_websocket_authorization.py` |
| `get_core_stats` — `GET /api/core` | admin bearer | `Admin.get_current` | any authenticated admin receives core data | owner/system policy | global unless explicitly safe | `tests/security/test_core_authorization.py` |
| `restart_core` — `POST /api/core/restart` | admin bearer | `Admin.check_sudo_admin` | coarse sudo; high-impact operation lacks reason/audit | owner/system policy | global | `tests/security/test_core_authorization.py` |
| `get_core_config` — `GET /api/core/config` | admin bearer | `Admin.check_sudo_admin` | configuration can contain operational secrets and all-user topology | owner/system policy | global | `tests/security/test_core_authorization.py` |
| `modify_core_config` — `PUT /api/core/config` | admin bearer | `Admin.check_sudo_admin` | file write plus global restart; no named permission or audit reason | owner/system policy | global | `tests/security/test_core_authorization.py` |
| `get_node_settings` — `GET /api/node/settings` | admin bearer | `Admin.check_sudo_admin` | TLS and node settings are globally exposed to sudo | `node.read` | global | `tests/security/test_node_authorization.py` |
| `get_watchdog_settings` — `GET /api/node/watchdog/settings` | admin bearer | `Admin.check_sudo_admin` | settings include Telegram destination/secret-bearing fields | `node.read` | global | `tests/security/test_node_authorization.py` |
| `set_watchdog_settings` — `PUT /api/node/watchdog/settings` | admin bearer | `Admin.check_sudo_admin` | global monitoring credentials and behavior can be replaced | `node.manage` | global | `tests/security/test_node_authorization.py` |
| `test_watchdog_notification` — `POST /api/node/watchdog/test` | admin bearer | `Admin.check_sudo_admin` | causes an external message with no audit event | `node.manage` | global | `tests/security/test_node_authorization.py` |
| `add_node` — `POST /api/node` | admin bearer | `Admin.check_sudo_admin` | creates infrastructure and background connection | `node.manage` | global | `tests/security/test_node_authorization.py` |
| `get_node` — `GET /api/node/{node_id}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | duplicated coarse role check | `node.read` | global | `tests/security/test_node_authorization.py` |
| `node_logs` — `WS /api/node/{node_id}/logs` | token in query/header | manual `Admin.get_admin` plus `is_sudo` | duplicated guard and query-token leakage risk | `node.read` | global | `tests/security/test_websocket_authorization.py` |
| `get_nodes` — `GET /api/nodes` | admin bearer | `Admin.check_sudo_admin` | no scoped node assignment model | `node.read` | global | `tests/security/test_node_authorization.py` |
| `modify_node` — `PUT /api/node/{node_id}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | infrastructure mutation and reconnect are one coarse privilege | `node.manage` | global | `tests/security/test_node_authorization.py` |
| `reconnect_node` — `POST /api/node/{node_id}/reconnect` | admin bearer | target lookup plus `Admin.check_sudo_admin` | high-impact action lacks reason/audit | `node.manage` | global | `tests/security/test_node_authorization.py` |
| `remove_node` — `DELETE /api/node/{node_id}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | removes infrastructure and usage context | `node.manage` | global | `tests/security/test_node_authorization.py` |
| `get_usage` — `GET /api/nodes/usage` | admin bearer | `Admin.check_sudo_admin` | global node usage has no billing/audit scope distinction | `node.read` and `billing.read` | global | `tests/security/test_node_authorization.py` |
| `get_system_stats` — `GET /api/system` | admin bearer | `Admin.get_current`; some user counts filter non-sudo | mixed global and caller-scoped aggregates can leak cross-owner data | `quota.read`; owner/system policy for global fields | owned aggregates; global only for owner | `tests/security/test_system_authorization.py` |
| `get_inbounds` — `GET /api/inbounds` | admin bearer | `Admin.get_current` | all inbounds visible without assignment scope | `template.read` or owner/system policy | assigned inbounds; owner global | `tests/security/test_system_authorization.py` |
| `get_hosts` — `GET /api/hosts` | admin bearer | `Admin.check_sudo_admin` | coarse global read | `node.read` | global | `tests/security/test_system_authorization.py` |
| `modify_hosts` — `PUT /api/hosts` | admin bearer | `Admin.check_sudo_admin` | global host rewrite lacks named permission/audit | `node.manage` | global | `tests/security/test_system_authorization.py` |
| `add_user` — `POST /api/user` | admin bearer | `Admin.get_current`; owner assigned in handler | custom creation is allowed to every authenticated admin and validation is call-site local | `user.create_custom` or `user.create_from_template` | new user owned by caller; owner override only with transfer permission | `tests/security/test_user_write_authorization.py` |
| `get_user` — `GET /api/user/{username}` | admin bearer | `get_validated_user` | ownership is embedded in one dependency and uses legacy `admin_id` | `user.read` | owned | `tests/security/test_user_read_authorization.py` |
| `modify_user` — `PUT /api/user/{username}` | admin bearer | `get_validated_user` plus `Admin.get_current` | one endpoint combines limits, status, proxies and inbounds without operation permissions | `user.update`; also `user.change_status` when status changes | owned | `tests/security/test_user_write_authorization.py` |
| `remove_user` — `DELETE /api/user/{username}` | admin bearer | `get_validated_user` plus `Admin.get_current` | hard delete with no reason/audit | `user.delete` | owned | `tests/security/test_user_write_authorization.py` |
| `reset_user_data_usage` — `POST /api/user/{username}/reset` | admin bearer | `get_validated_user` plus `Admin.get_current` | reset is not separately authorized or reasoned | `user.reset_usage` | owned | `tests/security/test_user_write_authorization.py` |
| `revoke_user_subscription` — `POST /api/user/{username}/revoke_sub` | admin bearer | `get_validated_user` plus `Admin.get_current` | token rotation is not separately authorized | `user.revoke_subscription` | owned | `tests/security/test_user_write_authorization.py` |
| `get_users` — `GET /api/users` | admin bearer | `Admin.get_current`; call-site admin filter | an owner query parameter and optional filters make missed-scope/IDOR regressions likely | `user.read` | centrally forced owned scope; owner may request global | `tests/security/test_user_read_authorization.py` |
| `reset_users_data_usage` — `POST /api/users/reset` | admin bearer | `Admin.check_sudo_admin` | global bulk reset has no bounded result or reason | `user.bulk_update` and `user.reset_usage` | global owner only; per-item scope | `tests/security/test_bulk_authorization.py` |
| `get_user_usage` — `GET /api/user/{username}/usage` | admin bearer | `get_validated_user` | usage read depends on legacy ownership check | `user.read` and `billing.read` | owned | `tests/security/test_user_read_authorization.py` |
| `active_next_plan` — `POST /api/user/{username}/active-next` | admin bearer | `get_validated_user` | mutation relies on read-style dependency and has no distinct permission | `user.update` and `user.change_status` | owned | `tests/security/test_user_write_authorization.py` |
| `get_users_usage` — `GET /api/users/usage` | admin bearer | `Admin.get_current`; call-site owner filter | caller-controlled owner filter can become a cross-owner aggregate bypass | `billing.read` | owned aggregate; owner global | `tests/security/test_user_read_authorization.py` |
| `set_owner` — `PUT /api/user/{username}/set-owner` | admin bearer | `get_validated_user` plus `Admin.check_sudo_admin` | direct ownership rewrite has no immutable creator, transfer history, quota lock, reason, or audit | `user.transfer_ownership` | global owner only; source and destination validated | `tests/security/test_ownership_transfer_authorization.py` |
| `get_expired_users` — `GET /api/users/expired` | admin bearer | `Admin.get_current`; helper applies call-site admin filter | scoped list relies on caller passing admin correctly | `user.read` | owned | `tests/security/test_bulk_authorization.py` |
| `delete_expired_users` — `DELETE /api/users/expired` | admin bearer | `Admin.get_current`; helper applies call-site admin filter | bulk hard delete lacks separate permission, reason and per-item result | `user.bulk_update` and `user.delete` | owned | `tests/security/test_bulk_authorization.py` |
| `add_user_template` — `POST /api/user_template` | admin bearer | `Admin.check_sudo_admin` | coarse sudo, no assignment/audit policy | `template.manage` | global owner | `tests/security/test_template_authorization.py` |
| `get_user_template_endpoint` — `GET /api/user_template/{template_id}` | admin bearer | target lookup plus `Admin.get_current` | any admin can read any template; assignment is not checked | `template.read` | assigned template or owner global | `tests/security/test_template_authorization.py` |
| `modify_user_template` — `PUT /api/user_template/{template_id}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | global template mutation lacks version/assignment policy | `template.manage` | global owner | `tests/security/test_template_authorization.py` |
| `remove_user_template` — `DELETE /api/user_template/{template_id}` | admin bearer | target lookup plus `Admin.check_sudo_admin` | hard delete can invalidate creation paths | `template.manage` | global owner | `tests/security/test_template_authorization.py` |
| `get_user_templates` — `GET /api/user_template` | admin bearer | `Admin.get_current` | all templates are returned without assignment scope | `template.read` | assigned templates or owner global | `tests/security/test_template_authorization.py` |
| `base` — `GET /` | browser | public dashboard shell | not a protected data operation; client-side routing is not an authorization boundary | public | none | `tests/api/test_smoke.py` |

## Subscription entry points

| Entry point | Caller | Current guard | Bypass or authorization risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| `user_subscription` — `GET /sub/{token}` and trailing-slash variant | subscription bearer | `get_validated_sub` | bearer URL grants full generated config and updates subscription metadata; URL can leak through clients and proxies | subscription self-service policy | token-bound user only | `tests/security/test_subscription_authorization.py` |
| `user_subscription_info` — `GET /sub/{token}/info` | subscription bearer | `get_validated_sub` | exposes account metadata to any token holder | subscription self-service policy | token-bound user only | `tests/security/test_subscription_authorization.py` |
| `user_get_usage` — `GET /sub/{token}/usage` | subscription bearer | `get_validated_sub` | exposes historical usage to any token holder | subscription self-service policy | token-bound user only | `tests/security/test_subscription_authorization.py` |
| `user_subscription_with_client_type` — `GET /sub/{token}/{client_type}` | subscription bearer | `get_validated_sub` | alternate export path must not bypass revoke/status or disclose another user | subscription self-service policy | token-bound user only | `tests/security/test_subscription_authorization.py` |

## CLI entry points

All CLI commands run as the local process identity and currently have no application-level actor, permission, ownership scope, request ID, or audit context.

| Entry point | Caller | Current guard | Bypass or authorization risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| `list_admins` — `marzban cli admin list` | local operator | none | direct global admin CRUD read, including aggregate data | `admin.read` | global owner | `tests/security/test_cli_authorization.py` |
| `delete_admin` — `marzban cli admin delete` | local operator | optional confirmation only | direct hard delete bypasses REST policy and actor audit | `admin.suspend` plus owner deletion policy | global | `tests/security/test_cli_authorization.py` |
| `create_admin` — `marzban cli admin create` | local operator | none | direct create bypasses permission resolver | `admin.create` | global | `tests/security/test_cli_authorization.py` |
| `update_admin` — `marzban cli admin update` | local operator | interactive prompt only | can change password/sudo/webhook without actor policy | `admin.update` | global | `tests/security/test_cli_authorization.py` |
| `import_from_env` — `marzban cli admin import-from-env` | local operator/environment | optional confirmation | creates/updates sudo and bulk-claims unowned users via direct query | owner/system policy and `user.transfer_ownership` | only approved environment-owner mapping | `tests/security/test_cli_authorization.py` |
| `list_users` — `marzban cli user list` | local operator | none | global user export-like read through direct CRUD | `user.read`; `user.export` for machine-readable output | explicit local actor scope | `tests/security/test_cli_authorization.py` |
| `set_owner` — `marzban cli user set-owner` | local operator | optional confirmation only | direct ownership rewrite bypasses transfer history, quota and audit | `user.transfer_ownership` | global owner; validate both owners | `tests/security/test_cli_authorization.py` |
| `get_link` — `marzban cli subscription get-link` | local operator | none | prints complete bearer subscription URL | `user.export` | owned user | `tests/security/test_cli_authorization.py` |
| `get_config` — `marzban cli subscription get-config` | local operator | none | exports credentials/config to terminal or arbitrary file | `user.export` | owned user | `tests/security/test_cli_authorization.py` |

## Telegram entry points

The `is_admin` filter checks only membership in configured Telegram IDs. It does not map the chat to a database admin, role, permission, ownership scope, or durable actor. Registered next-step handlers do not declare `is_admin` themselves and depend on conversational state.

| Entry point group | Caller | Current guard | Bypass or authorization risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| `help_command`, `system_command` | configured Telegram chat | `is_admin` | coarse environment allowlist; system aggregates are global | `quota.read` plus owner/system policy | owned aggregates; owner global | `tests/security/test_telegram_authorization.py` |
| `restart_command` | configured Telegram chat | `is_admin` | global core restart without mapped admin or audit | owner/system policy | global | `tests/security/test_telegram_authorization.py` |
| `delete_user_command`, `suspend_user_command`, `activate_user_command`, `reset_usage_user_command` | configured Telegram chat | `is_admin` | target username is trusted without ownership context | `user.delete`, `user.change_status`, `user.reset_usage` | owned | `tests/security/test_telegram_authorization.py` |
| `edit_all_command`, `delete_expired_command`, `delete_limited_command`, `add_data_command`, `add_time_command`, `inbound_command`, `delete_expired_confirm_command` | configured Telegram chat | `is_admin` | global bulk paths read/mutate/delete every matching user through direct CRUD | `user.bulk_update` plus operation permission | bounded owned set; per-item results | `tests/security/test_telegram_bulk_authorization.py` |
| `edit_command`, `help_edit_command`, `cancel_command`, `edit_user_command` | configured Telegram chat | `is_admin` | conversational state and target ownership are not centrally revalidated | `user.update` | owned | `tests/security/test_telegram_authorization.py` |
| `users_command`, `edit_note_command`, `user_command`, `search_user` | configured Telegram chat | `is_admin` | global search/list/detail direct CRUD can disclose cross-owner users | `user.read`; `user.update` for note | owned | `tests/security/test_telegram_authorization.py` |
| `revoke_sub_command`, `links_command`, `genqr_command` | configured Telegram chat | `is_admin` | revoke/export paths have no mapped actor or ownership guard | `user.revoke_subscription`; `user.export` | owned | `tests/security/test_telegram_authorization.py` |
| `template_charge_command`, `charge_command` | configured Telegram chat | `is_admin` | template assignment is absent and user ownership is unchecked | `user.update`, `user.reset_usage`, `template.read` | owned user and assigned template | `tests/security/test_telegram_authorization.py` |
| `add_user_from_template_command`, `add_user_from_template`, `random_username` | configured Telegram chat | `is_admin` | single/bulk template creation has no mapped owner, quota or assignment enforcement | `user.create_from_template`, `template.read` | caller owns new users; assigned template | `tests/security/test_telegram_authorization.py` |
| `add_user_command`, `add_user_status_step`, `select_inbounds`, `select_protocols`, `confirm_user_command` | configured Telegram chat | `is_admin` at callback entry | custom and bulk creation continue across stateful steps without central actor context | `user.create_custom`; `user.bulk_update` for bulk | caller owns new users | `tests/security/test_telegram_authorization.py` |
| `add_data_step`, `add_on_hold_timeout`, `add_time_step`, `add_user_bulk_number_step`, `add_user_data_limit_step`, `add_user_expire_step`, `add_user_from_template_username_step`, `add_user_username_step`, `edit_note_step`, `edit_user_data_limit_step`, `edit_user_expire_on_hold_timeout_step`, `edit_user_expire_step` | Telegram next-step message | prior conversation only; no decorator guard | next-step messages can outlive or diverge from the initiating actor/state and directly reach mutations | permission inherited from initiating operation, re-evaluated at execution | re-resolve actor and owned target on every step | `tests/security/test_telegram_next_step_authorization.py` |
| `usage_command` | any Telegram chat | public | arbitrary username reveals status, usage, limit and expiry; no `is_admin` or user binding | `user.read` or explicit user self-service policy | owned/self only | `tests/security/test_telegram_authorization.py` |

## Scheduled jobs and system actors

| Entry point | Caller | Current guard | Bypass or authorization risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| `core_health_check` | scheduler | none; process authority | reconnects core/nodes and changes node state without durable actor/run ID | `node.manage` system capability | global, least-privilege system actor | `tests/security/test_job_authorization.py` |
| `node_watchdog` | scheduler | none; process authority | reads secret settings, reconnects nodes and sends external messages | `node.read`, `node.manage` system capability | global, least-privilege system actor | `tests/security/test_job_authorization.py` |
| `record_user_usages` | scheduler | none; process authority | global usage writes and user traversal lack owner snapshot/system actor | billing ingestion system capability | preserve owner snapshot per event | `tests/security/test_job_authorization.py` |
| `record_node_usages` | scheduler | none; process authority | global aggregate writes with no run identity | billing ingestion system capability | global system actor | `tests/security/test_job_authorization.py` |
| `remove_expired_users` | scheduler | in-memory `SYSTEM_ADMIN` with `is_sudo=True` | fabricated non-database actor performs bulk hard delete; no permission, reason or durable identity | `user.bulk_update` and `user.delete` system capability | policy-bounded users; per-item owner snapshot | `tests/security/test_job_authorization.py` |
| `reset_user_data_usage` | scheduler | none; process authority | global periodic mutation bypasses permission and actor context | `user.reset_usage` system capability | each user's owner scope recorded | `tests/security/test_job_authorization.py` |
| `review` | scheduler | none; process authority | changes status, activates next plans and notifies across all owners | `user.change_status` system capability | each user's owner scope recorded | `tests/security/test_job_authorization.py` |
| `send_notifications` | scheduler | none; process authority | exports user-derived event data to external webhook without an authorization actor | notification-delivery system capability | only events already authorized for configured destination | `tests/security/test_job_authorization.py` |
| `delete_expired_reminders` | scheduler | none; process authority | global reminder deletion has no actor/run identity | notification-maintenance system capability | global system actor | `tests/security/test_job_authorization.py` |

Required future system identities are separate least-privilege actors for usage ingestion, lifecycle review/reset/delete, node health, and notification delivery. The current process identity and the in-memory `SYSTEM_ADMIN` are not acceptable authorization contexts.

## Dashboard callers

The dashboard is only a caller of REST operations. Route visibility, disabled buttons, and client-side state are never authorization guards.

| Dashboard source and calls | Caller | Current guard | Bypass or authorization risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| `Login.tsx`: `/admin/token`; `Router.tsx` and `useGetUser.tsx`: `/admin` | browser/admin | REST authentication | UI assumes returned `is_sudo`; it cannot replace server policy | authentication; `admin.read` self | self | `app/dashboard/src/**/*.test.tsx` and API security tests |
| `DashboardContext.tsx`: `/users`, `/user`, `/user/{username}`, usage, reset, revoke, `/users/reset`, `/inbounds` | dashboard admin | bearer token; REST guards | UI can invoke single and bulk mutations directly; hidden controls are bypassable | corresponding `user.*` permissions | owned | `app/dashboard/src/**/*.test.tsx` and user API security tests |
| `NodesContext.tsx`: `/node`, `/nodes`, `/nodes/usage`, modify, reconnect, delete | dashboard admin | bearer token; REST sudo guards | client-side sudo gating is not authoritative | `node.read`, `node.manage` | global owner | `app/dashboard/src/**/*.test.tsx` and node API security tests |
| `HostsContext.tsx`: `/hosts` read/write | dashboard admin | bearer token; REST sudo guards | global host configuration mutation | `node.read`, `node.manage` | global owner | `app/dashboard/src/**/*.test.tsx` and system API security tests |
| `CoreSettingsContext.tsx`: `/core`, `/core/config`, `/core/restart` | dashboard admin | bearer token; REST guards | configuration and restart are high-impact global operations | owner/system policy | global owner | `app/dashboard/src/**/*.test.tsx` and core API security tests |
| `NodesModal.tsx`: watchdog settings/test; `Statistics.tsx`: `/system` | dashboard admin | bearer token; REST guards | secret-bearing watchdog configuration and mixed-scope aggregates | `node.manage`; `quota.read` | global node policy; owned aggregates | `app/dashboard/src/**/*.test.tsx` and API security tests |

## Export and credential-bearing outputs

| Entry point | Caller | Current guard | Bypass or authorization risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| subscription REST responses | subscription bearer | `get_validated_sub` | full proxy credentials and subscription content leave the service | subscription self-service policy | token-bound user only | `tests/security/test_subscription_authorization.py` |
| CLI `get_link` | local operator | none | complete subscription URL printed to terminal | `user.export` | owned | `tests/security/test_export_authorization.py` |
| CLI `get_config` | local operator | none | proxy configuration printed or written to arbitrary path | `user.export` | owned | `tests/security/test_export_authorization.py` |
| Telegram `links_command` and `genqr_command` | configured Telegram chat | `is_admin` only | proxy links/QR are exported without mapped database actor | `user.export` | owned | `tests/security/test_export_authorization.py` |
| REST user response models | admin bearer | endpoint-dependent | user reads may include subscription URL/proxy credentials; export and ordinary read are not distinguished | `user.read` plus `user.export` for complete secrets | owned | `tests/security/test_export_authorization.py` |

## Bulk-operation inventory

| Bulk path | Caller | Current guard | Bypass or authorization risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| REST admin disable/activate all | admin bearer | sudo | no reason, audit, bounded outcome or per-item authorization | `user.bulk_update`, `user.change_status` | selected owner's users | `tests/security/test_bulk_authorization.py` |
| REST reset all | admin bearer | sudo | global mutation bypasses owned scope | `user.bulk_update`, `user.reset_usage` | global owner only | `tests/security/test_bulk_authorization.py` |
| REST expired list/delete | admin bearer | current admin plus call-site filter | helper/caller coupling can lose scope; delete is hard | `user.read`; `user.bulk_update`, `user.delete` | owned | `tests/security/test_bulk_authorization.py` |
| Telegram bulk create/template create | configured Telegram chat | `is_admin` only | no mapped owner, quota, template assignment or atomicity policy | `user.bulk_update`, creation permission | caller owns every created user | `tests/security/test_telegram_bulk_authorization.py` |
| Telegram edit all/delete expired/delete limited | configured Telegram chat | `is_admin` only | direct global CRUD with no central ownership or per-item result | `user.bulk_update` plus operation permission | owned | `tests/security/test_telegram_bulk_authorization.py` |
| CLI environment import | local operator/environment | optional confirmation | bulk ownership assignment through direct SQL update | `user.transfer_ownership` plus environment-owner policy | approved unowned legacy rows only | `tests/security/test_cli_authorization.py` |
| scheduled lifecycle/reset/delete jobs | scheduler | process authority | implicit global actor and missing owner snapshot | least-privilege system capabilities | policy-selected users with stored owner | `tests/security/test_job_authorization.py` |

## Direct CRUD and repository bypass inventory

Raw functions in `app/db/crud.py` intentionally remain repositories in Phase `1C`; they do not enforce actor permission. Every caller below must eventually enter through a service/policy context before invoking protected CRUD.

| Direct caller | Protected operations reached | Current guard | Bypass risk | Target permission | Ownership rule | Future test owner |
|---|---|---|---|---|---|---|
| `app/routers/admin.py` | admin create/update/delete, bulk user status, usage reset | endpoint-specific sudo | route can call raw CRUD without mandatory policy context | `admin.*`, `user.bulk_update` | global/selected owner | admin and bulk API suites |
| `app/routers/user.py` | user create/read/update/delete/reset/revoke/list/usage/transfer | mixed current admin, validated user and sudo | enforcement is distributed across handlers and optional filters | corresponding `user.*` | owned | user API suites |
| `app/routers/user_template.py` | template CRUD/list | mixed sudo/current admin | template assignment is absent | `template.read`, `template.manage` | assigned/global owner | template API suite |
| `app/routers/node.py`, `app/routers/system.py` | node, watchdog, hosts, global usage/stats | mostly sudo; some current admin | global repositories accept no actor/scope | `node.*`, `quota.read`, `billing.read` | global or owned aggregates | node/system API suites |
| `app/routers/subscription.py` | user lookup/update subscription metadata/usage | subscription token | bearer context is discarded before raw CRUD | subscription self-service policy | token-bound user | subscription suite |
| `cli/admin.py`, `cli/user.py`, `cli/subscription.py` | global admin/user CRUD, ownership, credential exports | none | complete application authorization bypass by local commands | operation permission via explicit CLI actor | explicit local actor scope | CLI suite |
| `app/telegram/handlers/admin.py`, `app/telegram/handlers/user.py` | user/template reads and mutations, bulk operations, exports | Telegram allowlist or public | Telegram identity is not a database actor; next-step handlers lack guards | corresponding `user.*`/`template.*` | owned/self | Telegram suites |
| `app/jobs/*.py` | usage writes, lifecycle/status/reset/delete, node state, notifications | process authority | no durable least-privilege system context | system capabilities | owner snapshot/global by policy | job suite |
| `app/dependencies.py` | raw target lookup and optional ownership comparison | dependency-specific | lookup helpers are mistaken for authorization and can be omitted | central policy required after lookup | owned | policy and IDOR suite |

## System-actor register

| Actor | Current representation | Trust boundary and risk | Required future scope | Future test owner |
|---|---|---|---|---|
| environment sudo | username/password in `SUDOERS`; JWT says `is_sudo` | no database row, suspension, stable owner ID or role assignments | reserved/materialized owner identity decided in Phase `1D` | `tests/security/test_environment_sudo.py` |
| database sudo admin | `admins.is_sudo` boolean | coarse all-or-nothing privilege | owner role plus named permissions | `tests/security/test_permission_resolution.py` |
| local CLI operator | operating-system process | no application identity or audit invocation ID | explicit CLI actor/service context | `tests/security/test_cli_authorization.py` |
| Telegram operator | configured numeric chat/user ID | no durable mapping to admin, role or ownership | mapped active admin plus update/chat IDs | `tests/security/test_telegram_authorization.py` |
| scheduler process | application process | every job implicitly has global database access | distinct durable least-privilege job actors and run IDs | `tests/security/test_job_authorization.py` |
| `SYSTEM_ADMIN` | in-memory `Admin(username="system", is_sudo=True)` | fabricated sudo actor has no durable identity or permission record | durable lifecycle-delete actor | `tests/security/test_job_authorization.py` |
| subscription bearer | token URL resolving to a user | possession is authority; URLs are easily copied/logged | self-service context bound to one user and revocation epoch | `tests/security/test_subscription_authorization.py` |
| dashboard browser | admin bearer stored/used by client | UI state can be bypassed; server remains authoritative | same central REST access context | dashboard plus API suites |

## Gate G1C coverage contract

`tests/security/test_authorization_inventory.py` extracts and verifies:

1. every REST/WebSocket decorated handler under `app/routers`;
2. every Typer command under `cli`;
3. every decorated Telegram handler and every registered next-step target;
4. every scheduled job registered with `scheduler.add_job`;
5. the required dashboard, subscription, export, bulk, direct-CRUD and system-actor sections.

Any new entry point makes the gate fail until this inventory is updated. This is a completeness guard only and must not be treated as authorization enforcement.
