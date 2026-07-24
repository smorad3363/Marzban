import ast
import importlib.util
import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def load_redaction_module():
    path = ROOT / "app" / "utils" / "redaction.py"
    spec = importlib.util.spec_from_file_location("phase1a_redaction", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


redaction = load_redaction_module()
REDACTED = redaction.REDACTED
redact_sensitive_data = redaction.redact_sensitive_data
redact_text = redaction.redact_text


def load_function(path, function_name, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    module = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[function_name]


class RedactionTests(unittest.TestCase):
    def test_redacts_direct_and_case_variant_secret_keys(self):
        value = {
            "Password": "plain-password",
            "PASSWORD_HASH": "$2b$12$abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXY",
            "Access_Token": "access-token-value",
            "Authorization": "Bearer authorization-value",
            "username": "alice",
            "client_ip": "198.51.100.8",
        }

        redacted = redact_sensitive_data(value)

        self.assertEqual(redacted["Password"], REDACTED)
        self.assertEqual(redacted["PASSWORD_HASH"], REDACTED)
        self.assertEqual(redacted["Access_Token"], REDACTED)
        self.assertEqual(redacted["Authorization"], REDACTED)
        self.assertEqual(redacted["username"], "alice")
        self.assertEqual(redacted["client_ip"], "198.51.100.8")

    def test_redacts_nested_credentials(self):
        value = {
            "event": "user_created",
            "user": {
                "username": "alice",
                "subscription_url": "https://example.test/sub/token-value",
                "proxies": [
                    {"type": "trojan", "password": "proxy-password"},
                    {"type": "vless", "private_key": "private-value"},
                ],
            },
            "TLS_Secret": "tls-secret-value",
            "webhook_secret": "webhook-secret-value",
        }

        redacted = redact_sensitive_data(value)

        self.assertEqual(redacted["event"], "user_created")
        self.assertEqual(redacted["user"]["username"], "alice")
        self.assertEqual(redacted["user"]["subscription_url"], REDACTED)
        self.assertEqual(redacted["user"]["proxies"][0]["password"], REDACTED)
        self.assertEqual(redacted["user"]["proxies"][1]["private_key"], REDACTED)
        self.assertEqual(redacted["TLS_Secret"], REDACTED)
        self.assertEqual(redacted["webhook_secret"], REDACTED)

    def test_redacts_labeled_jwt_hash_authorization_and_private_key_text(self):
        jwt = (
            "eyJhbGciOiJIUzI1NiJ9."
            "eyJzdWIiOiJhbGljZSJ9."
            "abcdefghijklmnopqrstuvwx"
        )
        password_hash = (
            "$2b$12$abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXY"
        )
        private_key = (
            "-----BEGIN PRIVATE KEY-----\n"
            "private-key-material\n"
            "-----END PRIVATE KEY-----"
        )
        text = (
            f"username=alice password=plain-secret Authorization: Bearer auth-secret "
            f"jwt={jwt} password_hash={password_hash}\n{private_key}"
        )

        redacted = redact_text(text)

        for secret in (
            "plain-secret",
            "auth-secret",
            jwt,
            password_hash,
            "private-key-material",
        ):
            self.assertNotIn(secret, redacted)
        self.assertIn("username=alice", redacted)

    def test_redacts_url_embedded_secrets(self):
        text = (
            "subscription=https://example.test/sub/subscription-token "
            "proxy=http://proxy-user:proxy-pass@proxy.example.test:8080/path "
            "database=mysql://db-user:db-pass@db.example.test/marzban "
            "callback=https://example.test/callback?token=query-token&event=login "
            "webhook=https://discord.com/api/webhooks/123/webhook-token"
        )

        redacted = redact_text(text)

        for secret in (
            "subscription-token",
            "proxy-user",
            "proxy-pass",
            "db-user",
            "db-pass",
            "query-token",
            "webhook-token",
        ):
            self.assertNotIn(secret, redacted)
        self.assertIn("event=login", redacted)

    def test_log_filter_redacts_before_formatting(self):
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg='%s - "%s %s"',
            args=(
                "198.51.100.8",
                "GET",
                "/sub/eyJhbGciOiJIUzI1NiJ9."
                "eyJzdWIiOiJhbGljZSJ9."
                "abcdefghijklmnopqrstuvwx",
            ),
            exc_info=None,
        )

        redaction.RedactingFilter().filter(record)
        rendered = record.getMessage()

        self.assertIn("198.51.100.8", rendered)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", rendered)

    def test_telegram_api_url_is_fully_redacted(self):
        url = "https://api.telegram.org/bot123456:secret-token/sendMessage"

        redacted = redact_text(f"request failed: {url}")

        self.assertNotIn("123456:secret-token", redacted)
        self.assertNotIn("api.telegram.org", redacted)

    def test_log_filter_redacts_exception_traceback(self):
        try:
            raise RuntimeError("Authorization: Bearer exception-secret")
        except RuntimeError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="uvicorn.error",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request failed",
            args=(),
            exc_info=exc_info,
        )

        redaction.RedactingFilter().filter(record)

        self.assertIsNone(record.exc_info)
        self.assertNotIn("exception-secret", record.exc_text)
        self.assertIn(REDACTED, record.exc_text)


class FailedLoginReportingTests(unittest.TestCase):
    def test_router_does_not_forward_submitted_password_to_reporter(self):
        path = ROOT / "app" / "routers" / "admin.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        login_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "report"
            and node.func.attr == "login"
        ]

        self.assertEqual(len(login_calls), 2)
        for call in login_calls:
            self.assertEqual(len(call.args), 3)
            self.assertNotIn("form_data.password", ast.unparse(call))

    def test_login_adapters_receive_only_safe_context(self):
        telegram = Mock()
        discord = Mock()
        login = load_function(
            ROOT / "app" / "utils" / "report.py",
            "login",
            {
                "NOTIFY_LOGIN": True,
                "telegram": telegram,
                "discord": discord,
            },
        )

        login("alice", "198.51.100.8", False)

        expected = {
            "username": "alice",
            "client_ip": "198.51.100.8",
            "status": "❌ Failed",
        }
        telegram.report_login.assert_called_once_with(**expected)
        discord.report_login.assert_called_once_with(**expected)

    def test_login_reporting_signatures_have_no_password_parameter(self):
        paths = (
            ROOT / "app" / "utils" / "report.py",
            ROOT / "app" / "telegram" / "handlers" / "report.py",
            ROOT / "app" / "discord" / "handlers" / "report.py",
        )

        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            login_function = next(
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name in {"login", "report_login"}
            )
            argument_names = [argument.arg for argument in login_function.args.args]
            self.assertNotIn("password", argument_names)

    def test_admin_list_does_not_print_raw_webhook_url(self):
        source = (ROOT / "cli" / "admin.py").read_text(encoding="utf-8")

        self.assertIn("redact_sensitive_data", source)
        self.assertNotIn("str(admin.discord_webhook or", source)

    def test_xray_startup_exception_uses_filtered_logger(self):
        source = (
            ROOT / "app" / "jobs" / "0_xray_core.py"
        ).read_text(encoding="utf-8")

        self.assertIn('logger.exception("Unable to start main Xray core")', source)
        self.assertNotIn("traceback.print_exc", source)


if __name__ == "__main__":
    unittest.main()
