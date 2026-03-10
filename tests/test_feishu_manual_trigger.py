import json
import tempfile
import unittest
from pathlib import Path


class FeishuManualTriggerTests(unittest.TestCase):
    def test_creates_task_and_marks_awaiting_user(self):
        from scripts.feishu_trigger import handle_feishu_trigger

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            result = handle_feishu_trigger(
                "禅道: https://zentao.example.com/bug-view-321.html",
                registry=[],
                base_dir=base_dir,
                session_id="feishu-dm-001",
            )

            run_dir = Path(result["runDir"])
            state = json.loads((run_dir / "state.json").read_text())
            task = json.loads((run_dir / "task.json").read_text())
            timeline = (run_dir / "timeline.jsonl").read_text().strip().splitlines()

            self.assertEqual(state["status"], "awaiting_user")
            self.assertEqual(state["sessionId"], "feishu-dm-001")
            self.assertIn("项目名", state["missingItems"])
            self.assertEqual(task["zentaoUrl"], "https://zentao.example.com/bug-view-321.html")
            self.assertEqual(json.loads(timeline[-1])["status"], "awaiting_user")
            self.assertIn("需要你补充信息", result["responseMessage"])

    def test_starts_task_immediately_when_project_matches_registry(self):
        from scripts.feishu_trigger import handle_feishu_trigger

        registry = [
            {
                'id': 'igmis-sx',
                'repoPath': '/repos/igmis_sx',
                'testCommand': 'xcodebuild test',
                'keywords': ['绍兴环卫监管', 'igmis_sx', 'sx'],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            result = handle_feishu_trigger(
                "禅道: https://zentao.example.com/bug-view-321.html 绍兴环卫监管登录白屏",
                registry=registry,
                base_dir=base_dir,
                session_id="feishu-dm-001",
            )

            run_dir = Path(result["runDir"])
            state = json.loads((run_dir / "state.json").read_text())
            task = json.loads((run_dir / "task.json").read_text())

            self.assertEqual(state["status"], "created")
            self.assertEqual(task["repoCandidate"], "igmis-sx")
            self.assertEqual(task["repoPath"], "/repos/igmis_sx")
            self.assertEqual(task["testCommand"], "xcodebuild test")
            self.assertIn("开始处理任务", result["responseMessage"])
            self.assertNotIn("需要你补充信息", result["responseMessage"])


if __name__ == "__main__":
    unittest.main()
