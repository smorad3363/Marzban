from pathlib import Path

from app.db.base import Base


MIGRATION = Path(
    "app/db/migrations/versions/c2f4a8d6e913_add_monetary_reseller_billing.py"
)


def test_monetary_billing_migration_is_additive_and_chained():
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "8b7d3e5f1a24"' in source
    for token in (
        "money_billing_enabled",
        "money_balance_toman",
        "used_traffic_price_per_gib_toman",
        "usage_billing_remainder",
        "price_toman",
        "admin_user_plan_prices",
        "admin_money_transactions",
        "uq_admin_money_operation_admin",
    ):
        assert token in source
    assert "if \"admin_money_transactions\" not in tables" in source
    assert "if \"admin_user_plan_prices\" not in tables" in source


def test_monetary_billing_model_indexes_match_migration_contract():
    settings = Base.metadata.tables["marzhelp_admin_settings"]
    assert {
        "money_billing_enabled",
        "money_balance_toman",
        "used_traffic_price_per_gib_toman",
        "usage_billing_remainder",
    } <= set(settings.c.keys())
    ledger = Base.metadata.tables["admin_money_transactions"]
    assert {index.name for index in ledger.indexes} >= {
        "ix_admin_money_admin_created",
        "ix_admin_money_user_created",
    }
    assert any(
        constraint.name == "uq_admin_money_operation_admin"
        for constraint in ledger.constraints
    )
