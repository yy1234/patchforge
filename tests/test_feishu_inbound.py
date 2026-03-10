import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


class FeishuInboundTests(unittest.TestCase):
    def test_routes_p2p_text_message_into_feishu_trigger(self):
        from scripts.feishu_inbound import handle_feishu_inbound

        payload = {
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
            },
            "event": {
                "sender": {
                    "sender_id": {
                        "open_id": "ou_trigger_123",
                    },
                },
                "message": {
                    "chat_type": "p2p",
                    "message_type": "text",
                    "message_id": "om_trigger_123",
                    "content": json.dumps(
                        {
                            "text": "禅道: https://zentao.example.com/bug-view-321.html",
                        },
                        ensure_ascii=False,
                    ),
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = handle_feishu_inbound(payload, base_dir=Path(tmp))

        self.assertEqual(result["eventType"], "triggered")
        self.assertEqual(result["sessionId"], "ou_trigger_123")
        self.assertEqual(result["messageId"], "om_trigger_123")
        self.assertIn("需要你补充信息", result["responseMessage"])
        self.assertTrue(result["taskId"].startswith("zentao-task-"))

    def test_returns_challenge_for_url_verification_payload(self):
        from scripts.feishu_inbound import handle_feishu_inbound

        result = handle_feishu_inbound(
            {
                "type": "url_verification",
                "challenge": "challenge-token-123",
            },
            base_dir=Path("."),
        )

        self.assertEqual(
            result,
            {
                "eventType": "url_verification",
                "challenge": "challenge-token-123",
            },
        )

    def test_ignores_non_zentao_text_message(self):
        from scripts.feishu_inbound import handle_feishu_inbound

        payload = {
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
            },
            "event": {
                "sender": {
                    "sender_id": {
                        "open_id": "ou_trigger_123",
                    },
                },
                "message": {
                    "chat_type": "p2p",
                    "message_type": "text",
                    "message_id": "om_ignore_123",
                    "content": json.dumps(
                        {
                            "text": "帮我看看这个问题，但我还没贴链接",
                        },
                        ensure_ascii=False,
                    ),
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = handle_feishu_inbound(payload, base_dir=Path(tmp))

        self.assertEqual(result["eventType"], "ignored")
        self.assertEqual(result["reason"], "not_a_zentao_trigger")
        self.assertEqual(result["sessionId"], "ou_trigger_123")
        self.assertEqual(result["messageId"], "om_ignore_123")

    def test_ignores_text_message_with_invalid_json_content(self):
        from scripts.feishu_inbound import handle_feishu_inbound

        payload = {
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
            },
            "event": {
                "sender": {
                    "sender_id": {
                        "open_id": "ou_trigger_789",
                    },
                },
                "message": {
                    "chat_type": "p2p",
                    "message_type": "text",
                    "message_id": "om_invalid_json",
                    "content": "{not-json",
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            result = handle_feishu_inbound(payload, base_dir=Path(tmp))

        self.assertEqual(result["eventType"], "ignored")
        self.assertEqual(result["reason"], "unsupported_message")

    def test_main_reads_payload_file_and_prints_json_result(self):
        from scripts.feishu_inbound import main

        payload = {
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
            },
            "event": {
                "sender": {
                    "sender_id": {
                        "open_id": "ou_trigger_456",
                    },
                },
                "message": {
                    "chat_type": "p2p",
                    "message_type": "text",
                    "message_id": "om_trigger_456",
                    "content": json.dumps(
                        {
                            "text": "禅道: https://zentao.example.com/bug-view-456.html",
                        },
                        ensure_ascii=False,
                    ),
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            payload_path = Path(tmp) / "payload.json"
            payload_path.write_text(json.dumps(payload, ensure_ascii=False))

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--payload-file",
                        str(payload_path),
                        "--runs-dir",
                        tmp,
                    ]
                )

        result = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["eventType"], "triggered")
        self.assertEqual(result["sessionId"], "ou_trigger_456")
        self.assertIn("responseMessage", result)

    def test_loads_default_registry_when_registry_not_passed(self):
        from scripts.feishu_inbound import handle_feishu_inbound

        payload = {
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
            },
            "event": {
                "sender": {
                    "sender_id": {
                        "open_id": "ou_trigger_789",
                    },
                },
                "message": {
                    "chat_type": "p2p",
                    "message_type": "text",
                    "message_id": "om_trigger_789",
                    "content": json.dumps(
                        {
                            "text": "禅道: https://zentao.example.com/bug-view-789.html 北京首钢登录白屏",
                        },
                        ensure_ascii=False,
                    ),
                },
            },
        }

        registry = {
            "version": 1,
            "roots": [{"id": "flutterProject", "path": "/Volumes/data_apfs/flutterProject"}],
            "projects": [
                {
                    "id": "snmis_bjsg",
                    "name": "北京首钢",
                    "aliases": ["snmis_bjsg", "北京首钢"],
                    "role": "app",
                    "projectType": "flutter_app",
                    "matchEnabled": True,
                    "rootPath": "/Volumes/data_apfs/flutterProject/snmis_bjsg",
                    "keywords": ["北京首钢"],
                    "commands": {"test": "flutter test"},
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "project_registry.json"
            registry_path.write_text(json.dumps(registry, ensure_ascii=False))

            with mock.patch("scripts.feishu_inbound.DEFAULT_REGISTRY_PATH", registry_path):
                result = handle_feishu_inbound(payload, base_dir=Path(tmp))

        self.assertEqual(result["eventType"], "triggered")
        self.assertIn("开始处理任务", result["responseMessage"])
        self.assertNotIn("需要你补充信息", result["responseMessage"])


if __name__ == "__main__":
    unittest.main()
