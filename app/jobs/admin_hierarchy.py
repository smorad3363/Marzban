from app import logger, scheduler, xray
from app.db import GetDB
from app.db.models import Admin, AdminHierarchy, AdminSuspensionEvent, MarzhelpAdminSettings
from app.utils import admin_hierarchy


def enforce_admin_account_limits() -> None:
    """Suspend expired/exhausted accounts and their subtree without OFFSET scans."""

    changed = False
    with GetDB() as db:
        if not admin_hierarchy.hierarchy_enabled(db):
            return
        owner = db.get(Admin, admin_hierarchy.owner_id(db))
        if owner is None:
            logger.error("Admin hierarchy is enabled without a valid Owner")
            return
        candidates = (
            db.query(Admin, MarzhelpAdminSettings)
            .join(MarzhelpAdminSettings, MarzhelpAdminSettings.admin_id == Admin.id)
            .filter(
                Admin.id != owner.id,
                MarzhelpAdminSettings.account_status_id == admin_hierarchy.ACCOUNT_STATUS_IDS[admin_hierarchy.ACTIVE],
            )
            .order_by(Admin.id)
            .all()
        )
        covered_admin_ids: set[int] = set()
        for target, settings in candidates:
            if target.id in covered_admin_ids:
                continue
            reason_id = admin_hierarchy.automatic_suspension_reason(db, settings)
            if reason_id is None:
                continue
            admin_hierarchy.suspend_admin(
                db,
                actor=owner,
                target=target,
                reason_id=reason_id,
                include_subtree=True,
                automatic=True,
            )
            covered_admin_ids.update(
                row[0]
                for row in db.query(AdminHierarchy.descendant_id)
                .filter(AdminHierarchy.ancestor_id == target.id)
                .all()
            )
            changed = True
            logger.warning('Admin "%s" was suspended automatically (reason_id=%s)', target.username, reason_id)

        # A replenished or renewed automatically-suspended Admin should not
        # remain frozen indefinitely. Resume only events explicitly marked as
        # automatic: manual suspensions and Owner Freeze remain Owner-controlled.
        candidates_to_resume = (
            db.query(Admin, MarzhelpAdminSettings, AdminSuspensionEvent)
            .join(MarzhelpAdminSettings, MarzhelpAdminSettings.admin_id == Admin.id)
            .join(
                AdminSuspensionEvent,
                AdminSuspensionEvent.id == MarzhelpAdminSettings.suspension_event_id,
            )
            .filter(
                MarzhelpAdminSettings.account_status_id
                == admin_hierarchy.ACCOUNT_STATUS_IDS[admin_hierarchy.SUSPENDED],
                AdminSuspensionEvent.admin_id == Admin.id,
                AdminSuspensionEvent.operation_type == "automatic_suspension",
                AdminSuspensionEvent.status == "complete",
            )
            .order_by(Admin.id).all()
        )
        for target, settings, event in candidates_to_resume:
            if admin_hierarchy.automatic_suspension_reason(db, settings) is not None:
                continue
            try:
                count = admin_hierarchy.resume_admin(db, actor=owner, target=target)
            except admin_hierarchy.HierarchyError as exc:
                if exc.code in {
                    "suspension_condition_active",
                    "no_active_suspension",
                }:
                    # Another limit or an independently frozen descendant is
                    # still blocking recovery; do not modify their state.
                    continue
                raise
            changed = True
            logger.info(
                'Admin "%s" resumed after automatic suspension (event=%s, users=%s)',
                target.username, event.id, count,
            )

    if changed:
        startup_config = xray.config.include_db_users()
        if xray.core.started:
            xray.core.restart(startup_config)
        for node_id, node in list(xray.nodes.items()):
            if node.connected:
                xray.operations.restart_node(node_id, startup_config)


scheduler.add_job(
    enforce_admin_account_limits,
    "interval",
    minutes=1,
    coalesce=True,
    max_instances=1,
)
