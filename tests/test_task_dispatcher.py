import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


class TaskDispatcherTests(unittest.TestCase):
    def build_task(self, task_id='bugfix-001'):
        return {
            'id': task_id,
            'sourceTaskId': f'source-{task_id}',
            'title': 'Fix sample bug',
            'repoPath': '/tmp/repo',
            'bugDescription': 'Sample',
            'reproSteps': ['pytest test_sample.py -q'],
            'expectedBehavior': 'Passes',
            'testCommand': 'pytest test_sample.py -q',
            'doneDefinition': ['tests pass'],
        }

    def test_dispatches_created_run_to_done_when_worker_and_checker_pass(self):
        from scripts.bugfix_orchestrator import initialize_task_run
        from scripts.task_dispatcher import dispatch_once

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = self.build_task()
            task['runtimeRules'] = {
                'entryFile': 'lib/app/app.dart',
                'currentEnvironment': 'prod',
                'preferredEnvironment': 'test',
                'switchRequired': True,
                'profileMarkers': {
                    'test': ['http://192.168.100.72:10062/uia/'],
                    'prod': ['http://10.1.120.241:9180/serverUia/'],
                },
            }
            run_dir = initialize_task_run(base_dir, task, 'extra context')

            def fake_prepare(run_dir, task):
                workspace = run_dir / 'workspace'
                app_dir = workspace / 'lib' / 'app'
                app_dir.mkdir(parents=True)
                (app_dir / 'app.dart').write_text("static String baseUrl = 'http://10.1.120.241:9180/serverUia/';\n")
                return workspace

            def fake_worker(run_dir, task, context_text, worktree_path):
                for name, content in {
                    'worker-report.json': json.dumps({
                        'taskId': task['id'],
                        'status': 'passed',
                        'reproduced': True,
                        'filesChanged': ['lib/a.dart'],
                        'testCommand': task['testCommand'],
                        'testExitCode': 0,
                        'risks': [],
                        'summary': 'ok',
                    }),
                    'patch.diff': 'diff --git a/lib/a.dart b/lib/a.dart',
                    'test-report.txt': 'ok',
                    'notes.md': 'notes',
                }.items():
                    (run_dir / name).write_text(content)
                return {
                    'exit_code': 0,
                    'timed_out': False,
                    'stalled': False,
                    'artifacts_present': ['worker-report.json', 'patch.diff', 'test-report.txt', 'notes.md'],
                }

            notifications = []

            result = dispatch_once(
                base_dir,
                worker_runner=fake_worker,
                workspace_preparer=fake_prepare,
                notifier=lambda task, state: notifications.append((task['id'], state['status'])),
            )

            state = json.loads((run_dir / 'state.json').read_text())
            updated_task = json.loads((run_dir / 'task.json').read_text())
            self.assertEqual(result['status'], 'done')
            self.assertEqual(state['status'], 'done')
            self.assertEqual(updated_task['runtimeRules']['currentEnvironment'], 'test')
            self.assertTrue(updated_task['runtimeRules']['switchPerformed'])
            self.assertEqual(notifications, [('bugfix-001', 'done')])

    def test_dispatches_retryable_worker_outcome_to_coder_retrying(self):
        from scripts.bugfix_orchestrator import initialize_task_run
        from scripts.task_dispatcher import dispatch_once

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = self.build_task()
            run_dir = initialize_task_run(base_dir, task, 'extra context')

            def fake_prepare(run_dir, task):
                workspace = run_dir / 'workspace'
                workspace.mkdir()
                return workspace

            def fake_worker(run_dir, task, context_text, worktree_path):
                return {
                    'exit_code': 0,
                    'timed_out': False,
                    'stalled': False,
                    'artifacts_present': ['worker-report.json'],
                }

            result = dispatch_once(
                base_dir,
                worker_runner=fake_worker,
                workspace_preparer=fake_prepare,
            )

            state = json.loads((run_dir / 'state.json').read_text())
            self.assertEqual(result['status'], 'coder_retrying')
            self.assertEqual(state['status'], 'coder_retrying')

    def test_dispatches_failed_checker_to_review_retry(self):
        from scripts.bugfix_orchestrator import initialize_task_run
        from scripts.task_dispatcher import dispatch_once

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = self.build_task()
            run_dir = initialize_task_run(base_dir, task, 'extra context')

            def fake_prepare(run_dir, task):
                workspace = run_dir / 'workspace'
                workspace.mkdir()
                return workspace

            def fake_worker(run_dir, task, context_text, worktree_path):
                for name, content in {
                    'worker-report.json': json.dumps({
                        'taskId': task['id'],
                        'status': 'passed',
                        'reproduced': True,
                        'filesChanged': ['lib/a.dart'],
                        'testCommand': task['testCommand'],
                        'testExitCode': 0,
                        'risks': [],
                        'summary': 'ok',
                    }),
                    'patch.diff': '',
                    'test-report.txt': 'ok',
                    'notes.md': 'notes',
                }.items():
                    (run_dir / name).write_text(content)
                return {
                    'exit_code': 0,
                    'timed_out': False,
                    'stalled': False,
                    'artifacts_present': ['worker-report.json', 'patch.diff', 'test-report.txt', 'notes.md'],
                }

            notifications = []

            result = dispatch_once(
                base_dir,
                worker_runner=fake_worker,
                workspace_preparer=fake_prepare,
                notifier=lambda task, state: notifications.append((task['id'], state['status'])),
            )

            state = json.loads((run_dir / 'state.json').read_text())
            self.assertEqual(result['status'], 'review_retry')
            self.assertEqual(state['status'], 'review_retry')
            self.assertEqual(notifications, [('bugfix-001', 'review_retry')])

    def test_promotes_queued_run_before_dispatch(self):
        from scripts.bugfix_orchestrator import initialize_task_run, write_task_state_with_metadata
        from scripts.task_dispatcher import dispatch_once

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = self.build_task()
            run_dir = initialize_task_run(base_dir, task, 'extra context')
            write_task_state_with_metadata(
                run_dir,
                task['id'],
                'queued',
                metadata={'queuedForStatus': 'created', 'sessionId': 'feishu-dm-001'},
            )

            def fake_prepare(run_dir, task):
                workspace = run_dir / 'workspace'
                workspace.mkdir()
                return workspace

            def fake_worker(run_dir, task, context_text, worktree_path):
                for name, content in {
                    'worker-report.json': json.dumps({
                        'taskId': task['id'],
                        'status': 'passed',
                        'reproduced': True,
                        'filesChanged': ['lib/a.dart'],
                        'testCommand': task['testCommand'],
                        'testExitCode': 0,
                        'risks': [],
                        'summary': 'ok',
                    }),
                    'patch.diff': 'diff --git a/lib/a.dart b/lib/a.dart',
                    'test-report.txt': 'ok',
                    'notes.md': 'notes',
                }.items():
                    (run_dir / name).write_text(content)
                return {
                    'exit_code': 0,
                    'timed_out': False,
                    'stalled': False,
                    'artifacts_present': ['worker-report.json', 'patch.diff', 'test-report.txt', 'notes.md'],
                }

            result = dispatch_once(
                base_dir,
                worker_runner=fake_worker,
                workspace_preparer=fake_prepare,
            )

            state = json.loads((run_dir / 'state.json').read_text())
            self.assertEqual(result['status'], 'done')
            self.assertEqual(state['status'], 'done')

    def test_prepares_copy_workspace_for_non_git_repo(self):
        from scripts.task_dispatcher import prepare_task_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'repo'
            repo.mkdir()
            (repo / '.svn').mkdir()
            (repo / 'lib').mkdir()
            (repo / 'lib' / 'a.dart').write_text('ok')
            run_dir = root / 'run'
            run_dir.mkdir()

            workspace = prepare_task_workspace(
                run_dir,
                {
                    'id': 'bugfix-001',
                    'repoPath': str(repo),
                },
            )

            self.assertTrue(workspace.exists())
            self.assertTrue((workspace / 'lib' / 'a.dart').exists())
            self.assertFalse((workspace / '.svn').exists())

    def test_prepares_copy_workspace_ignores_dangling_symlinks(self):
        from scripts.task_dispatcher import prepare_task_workspace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'repo'
            (repo / 'ios' / '.symlinks' / 'plugins').mkdir(parents=True)
            (repo / 'lib').mkdir()
            (repo / 'lib' / 'a.dart').write_text('ok')
            broken_link = repo / 'ios' / '.symlinks' / 'plugins' / 'broken_plugin'
            broken_link.symlink_to('/path/does/not/exist')
            run_dir = root / 'run'
            run_dir.mkdir()

            workspace = prepare_task_workspace(
                run_dir,
                {
                    'id': 'bugfix-001',
                    'repoPath': str(repo),
                },
            )

            self.assertTrue(workspace.exists())
            self.assertTrue((workspace / 'lib' / 'a.dart').exists())

    def test_main_prints_json_result(self):
        from scripts.bugfix_orchestrator import initialize_task_run
        from scripts.task_dispatcher import main

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = self.build_task()
            initialize_task_run(base_dir, task, 'extra context')

            def fake_prepare(run_dir, task):
                workspace = run_dir / 'workspace'
                workspace.mkdir()
                return workspace

            def fake_worker(run_dir, task, context_text, worktree_path):
                for name, content in {
                    'worker-report.json': json.dumps({
                        'taskId': task['id'],
                        'status': 'passed',
                        'reproduced': True,
                        'filesChanged': ['lib/a.dart'],
                        'testCommand': task['testCommand'],
                        'testExitCode': 0,
                        'risks': [],
                        'summary': 'ok',
                    }),
                    'patch.diff': 'diff --git a/lib/a.dart b/lib/a.dart',
                    'test-report.txt': 'ok',
                    'notes.md': 'notes',
                }.items():
                    (run_dir / name).write_text(content)
                return {
                    'exit_code': 0,
                    'timed_out': False,
                    'stalled': False,
                    'artifacts_present': ['worker-report.json', 'patch.diff', 'test-report.txt', 'notes.md'],
                }

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    ['--runs-dir', tmp],
                    worker_runner=fake_worker,
                    workspace_preparer=fake_prepare,
                )

            result = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(result['status'], 'done')

    def test_main_supports_simulate_success_mode(self):
        from scripts.bugfix_orchestrator import initialize_task_run
        from scripts.task_dispatcher import main

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = self.build_task()
            run_dir = initialize_task_run(base_dir, task, 'extra context')

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(['--runs-dir', tmp, '--simulate-success'])

            result = json.loads(stdout.getvalue())
            state = json.loads((run_dir / 'state.json').read_text())
            self.assertEqual(exit_code, 0)
            self.assertEqual(result['status'], 'done')
            self.assertEqual(state['status'], 'done')

    def test_main_supports_notify_dry_run_mode(self):
        from scripts.bugfix_orchestrator import initialize_task_run
        from scripts.task_dispatcher import main

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = self.build_task()
            initialize_task_run(base_dir, task, 'extra context')

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(['--runs-dir', tmp, '--simulate-success', '--notify-dry-run'])

            result = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(result['status'], 'done')

    def test_marks_run_needs_human_when_switch_configuration_is_incomplete(self):
        from scripts.bugfix_orchestrator import initialize_task_run
        from scripts.task_dispatcher import dispatch_once

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = self.build_task()
            task['runtimeRules'] = {
                'entryFile': 'lib/app/app.dart',
                'currentEnvironment': 'prod',
                'preferredEnvironment': 'test',
                'switchRequired': True,
                'profileMarkers': {
                    'test': ['http://192.168.100.72:10062/uia/'],
                    'prod': [],
                },
            }
            run_dir = initialize_task_run(base_dir, task, 'extra context')

            def fake_prepare(run_dir, task):
                workspace = run_dir / 'workspace'
                app_dir = workspace / 'lib' / 'app'
                app_dir.mkdir(parents=True)
                (app_dir / 'app.dart').write_text("static String baseUrl = 'http://10.1.120.241:9180/serverUia/';\n")
                return workspace

            result = dispatch_once(
                base_dir,
                workspace_preparer=fake_prepare,
            )

            state = json.loads((run_dir / 'state.json').read_text())
            self.assertEqual(result['status'], 'needs_human')
            self.assertEqual(state['status'], 'needs_human')
            self.assertIn('switchReason', state)


if __name__ == '__main__':
    unittest.main()
