from html import escape
from time import time

from app import logger, scheduler, xray
from app.db import GetDB, crud
from app.models.node import NodeStatus
from app.utils.node_watchdog import send_telegram_message


last_check = 0
fail_count = {}
next_try = {}
last_remind = {}
outage_notified = set()


def notify(settings, message: str) -> None:
    try:
        send_telegram_message(
            settings.telegram_bot_token, settings.telegram_chat_id, message
        )
    except RuntimeError as exc:
        logger.warning("Node watchdog Telegram notification failed: %s", exc)


def node_watchdog() -> None:
    global last_check
    now = int(time())

    with GetDB() as db:
        settings = crud.get_node_watchdog_settings(db)
        if not settings.enabled or not settings.telegram_bot_token or not settings.telegram_chat_id:
            return
        if now - last_check < settings.check_interval:
            return
        last_check = now
        nodes = crud.get_nodes(db)

        for node in nodes:
            node_id = node.id
            status = node.status
            if not node.watchdog_enabled or status == NodeStatus.disabled:
                fail_count.pop(node_id, None)
                next_try.pop(node_id, None)
                outage_notified.discard(node_id)
                continue

            if status == NodeStatus.connected:
                if node_id in outage_notified:
                    notify(
                        settings,
                        f"🟢 <b>{escape(node.name)}</b> (id {node_id}) is connected again.",
                    )
                fail_count[node_id] = 0
                next_try[node_id] = 0
                last_remind[node_id] = 0
                outage_notified.discard(node_id)
                continue

            if now < next_try.get(node_id, 0):
                continue

            attempts = fail_count.get(node_id, 0) + 1
            fail_count[node_id] = attempts
            backoff = min(
                settings.check_interval * (2 ** min(attempts, 20)),
                settings.backoff_cap,
            )
            next_try[node_id] = now + backoff

            if node_id not in outage_notified:
                detail = f" — {escape(node.message)}" if node.message else ""
                notify(
                    settings,
                    f"🔴 <b>{escape(node.name)}</b> (id {node_id}) is "
                    f"<b>{escape(status.value)}</b>{detail}\n✅ Reconnect triggered.",
                )
                outage_notified.add(node_id)

            xray.operations.connect_node(node_id)

            if attempts > 3 and now - last_remind.get(node_id, 0) >= settings.remind_every:
                notify(
                    settings,
                    f"🔴 <b>{escape(node.name)}</b> (id {node_id}) is still "
                    f"<b>{escape(status.value)}</b> after {attempts} reconnect attempts. "
                    f"Next retry in {backoff}s.",
                )
                last_remind[node_id] = now

        existing_ids = {node.id for node in nodes}
        for state in (fail_count, next_try, last_remind):
            for node_id in set(state) - existing_ids:
                state.pop(node_id, None)
        outage_notified.intersection_update(existing_ids)


scheduler.add_job(
    node_watchdog,
    "interval",
    seconds=5,
    coalesce=True,
    max_instances=1,
    id="node-watchdog",
    replace_existing=True,
)
