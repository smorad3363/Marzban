# Stage 11 Legacy Bot Capability Parity

| Capability | Existing path | Stage 11 durable path | Result |
|---|---|---|---|
| User operation notifications | webhook/Telegram report handlers | transactional audit outbox | Covered |
| Usage and expiry thresholds | `review_users` + `NotificationReminder` | existing hysteresis retained; audit/outbox independent | Covered |
| Node availability | node watchdog | existing watchdog retained | Covered |
| MySQL backup | manual installer/script paths | 30-minute encrypted scheduled artifact + Telegram delivery | Covered |
| Delivery retry | process-local queue | persistent bounded exponential retry/dead-letter | Improved |
| Duplicate prevention | process-local only | unique idempotency key + InnoDB locking | Improved |
| Backup restore | manual | explicit disposable restore verification; never automatic production restore | Covered |

Live Telegram delivery depends on deployment credentials and remains separately
verifiable. No legacy bot or historical audit data is deleted by Stage 11.
