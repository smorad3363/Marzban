import ast
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def load_redaction_module():
    path = ROOT / "app" / "utils" / "redaction.py"
    spec = importlib.util.spec_from_file_location("phase1a_redaction_notifications", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


redaction = load_redaction_module()


def load_function(path, function_name, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    module = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[function_name]


class NotificationRedactionTests(unittest.TestCase):
    def test_discord_payload_is_redacted_before_request(self):
        response = Mock()
        response.raise_for_status.return_value = None
        requests = SimpleNamespace(
            post=Mock(return_value=response),
            exceptions=SimpleNamespace(HTTPError=Exception),
        )
        send_webhook = load_function(
            ROOT / "app" / "discord" / "handlers" / "report.py",
            "send_webhook",
            {
                "requests": requests,
                "logger": Mock(),
                "redact_sensitive_data": redaction.redact_sensitive_data,
                "redact_text": redaction.redact_text,
            },
        )
        payload = {
            "content": "event=user_created",
            "nested": {
                "Password": "plain-password",
                "subscription_url": "https://example.test/sub/token-value",
            },
        }

        send_webhook(
            payload,
            "https://discord.com/api/webhooks/123/destination-secret",
        )

        sent = requests.post.call_args.kwargs["json"]
        self.assertEqual(sent["nested"]["Password"], redaction.REDACTED)
        self.assertEqual(
            sent["nested"]["subscription_url"],
            redaction.REDACTED,
        )
        self.assertEqual(payload["nested"]["Password"], "plain-password")

    def test_notification_payload_is_redacted_before_request(self):
        response = Mock(ok=True)
        session = Mock()
        session.post.return_value = response
        send_req = load_function(
            ROOT / "app" / "jobs" / "send_notifications.py",
            "send_req",
            {
                "session": session,
                "headers": {"x-webhook-secret": "header-secret"},
                "logger": Mock(),
                "redact_sensitive_data": redaction.redact_sensitive_data,
                "redact_text": redaction.redact_text,
            },
        )
        payload = [
            {
                "username": "alice",
                "user": {
                    "subscription_url": "https://example.test/sub/token-value",
                    "proxies": {"trojan": {"password": "proxy-password"}},
                },
            }
        ]

        result = send_req("https://notify.example.test/hook", payload)

        self.assertTrue(result)
        sent = session.post.call_args.kwargs["json"]
        self.assertEqual(sent[0]["username"], "alice")
        self.assertEqual(
            sent[0]["user"]["subscription_url"],
            redaction.REDACTED,
        )
        self.assertEqual(
            sent[0]["user"]["proxies"]["trojan"]["password"],
            redaction.REDACTED,
        )

    def test_telegram_text_is_redacted_before_send(self):
        bot = Mock()
        report = load_function(
            ROOT / "app" / "telegram" / "handlers" / "report.py",
            "report",
            {
                "bot": bot,
                "TELEGRAM_ADMIN_ID": [123],
                "TELEGRAM_LOGGER_CHANNEL_ID": None,
                "ApiTelegramException": Exception,
                "logger": Mock(),
                "redact_text": redaction.redact_text,
            },
        )

        report(
            "username=alice password=plain-password",
            parse_mode="html",
        )

        sent_text = bot.send_message.call_args.args[1]
        self.assertIn("username=alice", sent_text)
        self.assertNotIn("plain-password", sent_text)


if __name__ == "__main__":
    unittest.main()
