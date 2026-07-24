import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "docs" / "PHASE_1D_PERSISTENCE_IDENTITY_VERSION_BASELINES.md"


def _assignment_value(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {path}")


def _migration_heads():
    revisions = {}
    for path in (ROOT / "app" / "db" / "migrations" / "versions").glob("*.py"):
        revision = _assignment_value(path, "revision")
        down_revision = _assignment_value(path, "down_revision")
        revisions[revision] = down_revision

    referenced = set()
    for down_revision in revisions.values():
        if isinstance(down_revision, (tuple, list)):
            referenced.update(item for item in down_revision if item)
        elif down_revision:
            referenced.add(down_revision)
    return set(revisions) - referenced


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_recorded_alembic_head_matches_repository_graph():
    baseline = BASELINE_PATH.read_text(encoding="utf-8")

    assert _migration_heads() == {"9c2f1a7b4d6e"}
    assert "`63fbd07b9f14 (head)`" in baseline


def test_recorded_version_matches_application_version():
    baseline = BASELINE_PATH.read_text(encoding="utf-8")
    init_tree = ast.parse((ROOT / "app" / "__init__.py").read_text(encoding="utf-8"))
    version = next(
        ast.literal_eval(node.value)
        for node in init_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        )
    )

    assert version == "0.8.4"
    assert "`0.8.4`" in baseline


def test_baseline_matches_current_driver_pool_and_mysql_image():
    baseline = BASELINE_PATH.read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    config = (ROOT / "config.py").read_text(encoding="utf-8")
    engine = (ROOT / "app" / "db" / "base.py").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    installer = (ROOT / "scripts" / "marzban.sh").read_text(encoding="utf-8")

    required_source_fragments = {
        "PyMySQL==1.1.1": requirements,
        "SQLAlchemy==2.0.36": requirements,
        "SQLALCHEMY_POOL_SIZE": config,
        'default=10': config,
        "SQLIALCHEMY_MAX_OVERFLOW": config,
        'default=30': config,
        "pool_recycle=3600": engine,
        "pool_timeout=10": engine,
        "image: mysql:8.0": compose,
        "mysql+pymysql://marzban:": installer,
        "--slow_query_log=1": compose,
        "--long_query_time=2": compose,
    }
    assert all(fragment in source for fragment, source in required_source_fragments.items())

    for recorded in (
        "`mysql+pymysql`",
        "`PyMySQL==1.1.1`",
        "`SQLAlchemy==2.0.36`",
        "`pool_size=10`",
        "`max_overflow=30`",
        "`pool_timeout=10`",
        "`pool_recycle=3600`",
        "`mysql:8.0`",
    ):
        assert recorded in baseline


def test_baseline_contains_approved_topology_and_sudoers_policy():
    baseline = _normalized(BASELINE_PATH.read_text(encoding="utf-8"))

    required = (
        "MySQL is the authoritative production database",
        "every production table",
        "must use InnoDB",
        "SQLite is limited to development",
        "one Marzban application instance",
        "one authoritative scheduler/usage-job worker",
        "database-backed claims, leases, or distributed locking",
        "Every configured SUDOERS username maps one-to-one",
        "initially receives the `owner` role",
        "must not be copied into database password fields",
        "must never be silently merged",
        "cannot be deleted while its username remains active",
    )

    assert all(statement in baseline for statement in required)


def test_baseline_records_required_mysql_investigation_without_mutation():
    baseline = _normalized(BASELINE_PATH.read_text(encoding="utf-8"))

    required = (
        "Transaction isolation and deadlock evidence",
        "`REPEATABLE READ`",
        "`connect_timeout=10`",
        "`read_timeout=None`",
        "`write_timeout=None`",
        "`slow_query_log=1`",
        "Current index evidence",
        "No index is added or changed in Phase 1D",
        "No migration was created or applied",
        "Phase 2 must not start",
    )

    assert all(statement in baseline for statement in required)
