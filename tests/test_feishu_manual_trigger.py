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

        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / 'repo'
            app_dir = repo_dir / 'lib' / 'app'
            app_dir.mkdir(parents=True)
            (app_dir / 'app.dart').write_text("static String baseUrl = 'http://192.168.100.72:10062/uia/';\n")
            registry = [
                {
                    'id': 'igmis-sx',
                    'repoPath': str(repo_dir),
                    'testCommand': 'xcodebuild test',
                    'keywords': ['绍兴环卫监管', 'igmis_sx', 'sx'],
                }
            ]
            local_rules = {
                'projects': {
                    'igmis-sx': {
                        'entryFile': 'lib/app/app.dart',
                        'environment': {
                            'preferredForAutomation': 'test',
                            'activeProfileMarkers': {
                                'test': ['http://192.168.100.72:10062/uia/'],
                                'prod': ['http://10.1.120.241:9180/serverUia/'],
                            },
                            'autoSwitchRule': {'ifCurrentProfile': 'prod', 'switchTo': 'test'},
                        },
                        'credentials': {
                            'sourcePriority': ['remarks', 'local_default'],
                            'localDefault': {'username': 'root', 'password': '123456'},
                        },
                        'backendCollaboration': {'requiredWhenBlocked': ['后端接口地址']},
                    }
                }
            }
            base_dir = Path(tmp)
            result = handle_feishu_trigger(
                "禅道: https://zentao.example.com/bug-view-321.html 绍兴环卫监管登录白屏",
                registry=registry,
                base_dir=base_dir,
                session_id="feishu-dm-001",
                local_rules=local_rules,
            )

            run_dir = Path(result["runDir"])
            state = json.loads((run_dir / "state.json").read_text())
            task = json.loads((run_dir / "task.json").read_text())

            self.assertEqual(state["status"], "created")
            self.assertEqual(task["repoCandidate"], "igmis-sx")
            self.assertEqual(task["repoPath"], str(repo_dir))
            self.assertEqual(task["testCommand"], "xcodebuild test")
            self.assertEqual(task["runtimeRules"]["currentEnvironment"], "test")
            self.assertEqual(task["runtimeRules"]["defaultUsername"], "root")
            self.assertIn("开始处理任务", result["responseMessage"])
            self.assertNotIn("需要你补充信息", result["responseMessage"])

    def test_reports_switch_to_test_when_runtime_rules_detect_prod(self):
        from scripts.feishu_trigger import handle_feishu_trigger

        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / 'repo'
            app_dir = repo_dir / 'lib' / 'app'
            app_dir.mkdir(parents=True)
            (app_dir / 'app.dart').write_text("static String baseUrl = 'http://10.1.120.241:9180/serverUia/';\n")
            registry = [
                {
                    'id': 'snmis_bjsg',
                    'repoPath': str(repo_dir),
                    'testCommand': 'flutter test',
                    'keywords': ['北京首钢'],
                }
            ]
            local_rules = {
                'projects': {
                    'snmis_bjsg': {
                        'entryFile': 'lib/app/app.dart',
                        'environment': {
                            'preferredForAutomation': 'test',
                            'activeProfileMarkers': {
                                'test': ['http://192.168.100.72:10062/uia/'],
                                'prod': ['http://10.1.120.241:9180/serverUia/'],
                            },
                            'autoSwitchRule': {'ifCurrentProfile': 'prod', 'switchTo': 'test'},
                        },
                        'credentials': {
                            'sourcePriority': ['remarks', 'local_default'],
                            'localDefault': {'username': 'root', 'password': '123456'},
                        },
                        'backendCollaboration': {'requiredWhenBlocked': ['后端接口地址']},
                    }
                }
            }

            result = handle_feishu_trigger(
                "禅道: https://zentao.example.com/bug-view-321.html 北京首钢登录白屏",
                registry=registry,
                base_dir=Path(tmp),
                session_id="feishu-dm-001",
                local_rules=local_rules,
            )

            run_dir = Path(result["runDir"])
            state = json.loads((run_dir / "state.json").read_text())
            self.assertEqual(state["triageDecision"], "run")
            self.assertIn("生产环境", state["triageNote"])
            self.assertIn("将切到 test", result["responseMessage"])

    def test_reuses_active_run_for_same_bug_and_session(self):
        from scripts.feishu_trigger import handle_feishu_trigger

        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / 'repo'
            repo_dir.mkdir()
            registry = [
                {
                    'id': 'igmis-sx',
                    'repoPath': str(repo_dir),
                    'testCommand': 'xcodebuild test',
                    'keywords': ['绍兴环卫监管', 'igmis_sx', 'sx'],
                }
            ]
            base_dir = Path(tmp)
            first = handle_feishu_trigger(
                "禅道: https://zentao.example.com/bug-view-321.html 绍兴环卫监管登录白屏",
                registry=registry,
                base_dir=base_dir,
                session_id="feishu-dm-001",
            )
            second = handle_feishu_trigger(
                "禅道: https://zentao.example.com/bug-view-321.html 不对，把按钮文案改成B",
                registry=registry,
                base_dir=base_dir,
                session_id="feishu-dm-001",
            )

            self.assertEqual(first["runDir"], second["runDir"])
            run_dir = Path(first["runDir"])
            context = (run_dir / "context.md").read_text()
            self.assertIn("把按钮文案改成B", context)

    def test_queues_fourth_distinct_ready_run(self):
        from scripts.feishu_trigger import handle_feishu_trigger

        urls = [
            'https://zentao.example.com/bug-view-101.html',
            'https://zentao.example.com/bug-view-102.html',
            'https://zentao.example.com/bug-view-103.html',
            'https://zentao.example.com/bug-view-104.html',
        ]

        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / 'repo'
            repo_dir.mkdir()
            registry = [
                {
                    'id': 'snmis-bjsg',
                    'repoPath': str(repo_dir),
                    'testCommand': 'flutter test',
                    'keywords': ['北京首钢'],
                }
            ]
            base_dir = Path(tmp)
            results = []
            for url in urls:
                results.append(handle_feishu_trigger(
                    f"禅道: {url} 北京首钢登录白屏",
                    registry=registry,
                    base_dir=base_dir,
                    session_id="feishu-dm-001",
                ))

            queued_run = Path(results[-1]["runDir"])
            state = json.loads((queued_run / "state.json").read_text())

            self.assertEqual(state["status"], "queued")
            self.assertIn("已进入队列", results[-1]["responseMessage"])

    def test_reports_blocked_when_triage_fails(self):
        from scripts.feishu_trigger import handle_feishu_trigger

        registry = [
            {
                'id': 'snmis-bjsg',
                'repoPath': '/path/does/not/exist',
                'testCommand': 'flutter test',
                'keywords': ['北京首钢'],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            result = handle_feishu_trigger(
                "禅道: https://zentao.example.com/bug-view-105.html 北京首钢登录白屏",
                registry=registry,
                base_dir=Path(tmp),
                session_id="feishu-dm-001",
            )

            run_dir = Path(result["runDir"])
            state = json.loads((run_dir / "state.json").read_text())
            self.assertEqual(state["status"], "needs_human")
            self.assertEqual(state["triageDecision"], "blocked")
            self.assertIn("当前无法自动处理", result["responseMessage"])


if __name__ == "__main__":
    unittest.main()
