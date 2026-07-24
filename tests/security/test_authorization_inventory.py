import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "docs" / "SECURITY_AUTHORIZATION_ENTRYPOINT_INVENTORY.md"


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return ""


def _trees(paths):
    for path in paths:
        yield path, ast.parse(path.read_text(encoding="utf-8"))


def _decorated_functions(paths, decorator_predicate):
    functions = set()
    for _, tree in _trees(paths):
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and decorator_predicate(_call_name(decorator.func))
                ):
                    functions.add(node.name)
    return functions


def _registered_call_targets(paths, suffix):
    targets = set()
    for _, tree in _trees(paths):
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and _call_name(node.func).endswith(suffix)
                and node.args
            ):
                target = _call_name(node.args[0])
                if target:
                    targets.add(target)
    return targets


def _missing(names, inventory):
    return sorted(name for name in names if f"`{name}`" not in inventory)


def test_inventory_covers_all_rest_and_websocket_handlers():
    inventory = INVENTORY_PATH.read_text(encoding="utf-8")
    handlers = _decorated_functions(
        sorted((ROOT / "app" / "routers").glob("*.py")),
        lambda name: name.startswith("router."),
    )

    assert not _missing(handlers, inventory)


def test_inventory_covers_all_cli_commands():
    inventory = INVENTORY_PATH.read_text(encoding="utf-8")
    commands = _decorated_functions(
        sorted((ROOT / "cli").glob("*.py")),
        lambda name: name.endswith(".command"),
    )

    assert not _missing(commands, inventory)


def test_inventory_covers_all_telegram_handlers_and_next_steps():
    inventory = INVENTORY_PATH.read_text(encoding="utf-8")
    paths = sorted((ROOT / "app" / "telegram" / "handlers").glob("*.py"))
    handlers = _decorated_functions(
        paths,
        lambda name: name
        in {
            "bot.message_handler",
            "bot.callback_query_handler",
            "bot.inline_handler",
        },
    )
    next_steps = set()
    for _, tree in _trees(paths):
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and _call_name(node.func).endswith("register_next_step_handler")
                and len(node.args) >= 2
            ):
                target = _call_name(node.args[1])
                if target:
                    next_steps.add(target)

    assert not _missing(handlers | next_steps, inventory)


def test_inventory_covers_all_scheduled_jobs():
    inventory = INVENTORY_PATH.read_text(encoding="utf-8")
    jobs = _registered_call_targets(
        sorted((ROOT / "app" / "jobs").glob("*.py")),
        "scheduler.add_job",
    )

    assert not _missing(jobs, inventory)


def test_inventory_has_every_required_surface_and_matrix_field():
    inventory = INVENTORY_PATH.read_text(encoding="utf-8")
    required_sections = {
        "REST and WebSocket entry points",
        "Subscription entry points",
        "CLI entry points",
        "Telegram entry points",
        "Scheduled jobs and system actors",
        "Dashboard callers",
        "Export and credential-bearing outputs",
        "Bulk-operation inventory",
        "Direct CRUD and repository bypass inventory",
        "System-actor register",
    }
    required_fields = {
        "Caller",
        "Current guard",
        "Bypass",
        "Target permission",
        "Ownership rule",
        "Future test owner",
    }

    assert all(f"## {section}" in inventory for section in required_sections)
    assert all(field in inventory for field in required_fields)
