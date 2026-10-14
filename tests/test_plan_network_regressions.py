"""Focused standard-library regressions for production Plan/network bugs.

Run without a database or Xray process:
    python -m unittest discover -s tests -p test_plan_network_regressions.py
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLANS_SOURCE = (ROOT / "app/utils/admin_plans.py").read_text()
SYSTEM_SOURCE = (ROOT / "app/routers/system.py").read_text()
CORE_SOURCE = (ROOT / "app/routers/core.py").read_text()


def extracted_function(source: str, name: str, namespace: dict):
    """Execute only the named function, with explicit lightweight test doubles."""
    module = ast.parse(source)
    node = next(
        part for part in module.body
        if isinstance(part, (ast.FunctionDef, ast.AsyncFunctionDef))
        and part.name == name
    )
    fragment = ast.get_source_segment(source, node)
    exec("from __future__ import annotations\n" + fragment, namespace)
    return namespace[name]


class Version:
    version_number = 1
    plan_id = 1

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.id = None


class Inbound:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Host:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Query:
    def filter(self, *args):
        return self

    def scalar(self):
        return 0


class PendingWrites:
    """Simulates Session(autoflush=False), including unflushed association rows."""
    def __init__(self):
        self.pending = []
        self.flushed = []
        self.flush_calls = 0

    def query(self, *args):
        return Query()

    def add(self, item):
        self.pending.append(item)

    def add_all(self, items):
        self.pending.extend(items)

    def flush(self):
        self.flush_calls += 1
        for item in self.pending:
            if isinstance(item, Version) and item.id is None:
                item.id = 101
        self.flushed.extend(self.pending)
        self.pending.clear()


class PlanNetworkRegressions(unittest.TestCase):
    def test_created_version_relations_are_flushed_before_return(self):
        fake_func = SimpleNamespace(max=lambda _: None)
        namespace = {
            "func": fake_func,
            "AdminUserPlanVersion": Version,
            "AdminUserPlanInbound": Inbound,
            "AdminUserPlanHost": Host,
        }
        create = extracted_function(PLANS_SOURCE, "_add_version", namespace)
        db = PendingWrites()
        plan = SimpleNamespace(id=1, is_trial=False, current_version_id=None)
        actor = SimpleNamespace(id=3)
        values = SimpleNamespace(
            price_toman=50000, data_limit=1024, duration_days=30,
            concurrent_user_limit=2, reset_strategy="no_reset",
            renewal_volume_strategy="replace", renewal_time_strategy="extend_max",
            inbounds=["fastly"], hosts={"fastly": [121]},
        )
        version = create(db, plan, actor, values)
        self.assertEqual(plan.current_version_id, version.id)
        self.assertGreaterEqual(db.flush_calls, 2)
        self.assertEqual(len([x for x in db.flushed if isinstance(x, Inbound)]), 1)
        self.assertEqual(len([x for x in db.flushed if isinstance(x, Host)]), 1)
        self.assertEqual(db.pending, [])

    def test_network_edit_never_deletes_existing_proxy_credentials(self):
        vless = SimpleNamespace(
            type="vless", settings={"id": "keep-uuid"}, excluded_inbounds=[]
        )
        shadowsocks = SimpleNamespace(
            type="shadowsocks", settings={"password": "keep-password"},
            excluded_inbounds=[],
        )
        user = SimpleNamespace(proxies=[vless, shadowsocks])
        config = SimpleNamespace(
            inbounds_by_tag={"fastly": {"protocol": "vless"}},
            inbounds_by_protocol={
                "vless": [{"tag": "fastly"}],
                "shadowsocks": [{"tag": "ss-other"}],
            },
        )
        crud = SimpleNamespace(
            get_or_create_inbound=lambda db, tag: SimpleNamespace(tag=tag),
        )
        class DB:
            def delete(self, obj):
                raise AssertionError("Proxy credentials must never be deleted")

        namespace = {
            "ProxyTypes": lambda protocol: protocol,
            "xray": SimpleNamespace(config=config),
            "crud": crud,
        }
        apply_network = extracted_function(
            PLANS_SOURCE, "_apply_plan_network_to_user", namespace,
        )
        apply_network(DB(), user, {"fastly"})
        self.assertEqual(user.proxies, [vless, shadowsocks])
        self.assertEqual(vless.settings["id"], "keep-uuid")
        self.assertEqual(shadowsocks.settings["password"], "keep-password")
        self.assertEqual(
            [tag.tag for tag in shadowsocks.excluded_inbounds], ["ss-other"],
        )

    def test_empty_network_fails_before_mutating_users(self):
        user = SimpleNamespace(proxies=[SimpleNamespace(type="vless")])
        apply_network = extracted_function(
            PLANS_SOURCE, "_apply_plan_network_to_user",
            {"ProxyTypes": lambda protocol: protocol},
        )
        with self.assertRaises(RuntimeError):
            apply_network(None, user, set())
        self.assertEqual(len(user.proxies), 1)

    def test_sync_keeps_financial_purchase_assignments(self):
        module = ast.parse(PLANS_SOURCE)
        fn = next(node for node in module.body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "sync_active_users_to_network_revision")
        calls = [
            node for node in ast.walk(fn) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "UserPlanAssignment"
        ]
        self.assertFalse(calls, "Do not rewrite purchase versions during network sync")
        fn_text = ast.get_source_segment(PLANS_SOURCE, fn)
        self.assertNotIn("UserPlanAssignment.version_id == previous_version.id", fn_text)

    def test_live_scope_uses_current_plan_version_not_purchase_version(self):
        fn = next(node for node in ast.parse(PLANS_SOURCE).body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "subscription_host_scope")
        text = ast.get_source_segment(PLANS_SOURCE, fn)
        self.assertIn("plan.current_version_id", text)
        self.assertNotIn("assignment.version_id", text)

    def test_host_save_updates_global_scope_even_without_affected_host_ids(self):
        fn = next(node for node in ast.parse(SYSTEM_SOURCE).body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "modify_hosts")
        code = ast.get_source_segment(SYSTEM_SOURCE, fn)
        self.assertIn("sync_tracking_plans_to_global_network", code)
        self.assertIn("if auto_sync and plan_id in tracking_plan_ids:", code)
        self.assertIn("crud.update_hosts", code)

    def test_core_edits_also_follow_network(self):
        fn = next(node for node in ast.parse(CORE_SOURCE).body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "modify_core_config")
        code = ast.get_source_segment(CORE_SOURCE, fn)
        self.assertIn("sync_tracking_plans_to_global_network", code)
        self.assertIn("removed_tags", code)
        self.assertIn("old_payload_text", code)


if __name__ == "__main__":
    unittest.main()
