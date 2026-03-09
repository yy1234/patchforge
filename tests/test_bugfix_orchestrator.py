import json
import tempfile
import unittest
from pathlib import Path


class RunLayoutTests(unittest.TestCase):
    def test_run_directory_layout_is_created(self):
        from scripts.bugfix_orchestrator import ensure_run_layout
        base = Path('tmp-test-runs')
        run_dir = ensure_run_layout(base, 'bugfix-001')
        self.assertTrue((run_dir / 'task.json').parent.exists())


class TaskArtifactTests(unittest.TestCase):
    def test_task_files_are_written(self):
        from scripts.bugfix_orchestrator import write_task_files
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            task = {
                'id': 'bugfix-001',
                'title': 'Fix sample bug',
                'repoPath': '/tmp/repo',
                'bugDescription': 'Sample',
                'reproSteps': ['pytest test_sample.py -q'],
                'expectedBehavior': 'Passes',
                'testCommand': 'pytest test_sample.py -q',
                'doneDefinition': ['tests pass'],
            }
            write_task_files(run_dir, task, 'extra context')
            self.assertEqual(json.loads((run_dir / 'task.json').read_text())['id'], 'bugfix-001')
            self.assertIn('extra context', (run_dir / 'context.md').read_text())

    def test_task_state_artifacts_are_initialized(self):
        from scripts.bugfix_orchestrator import initialize_task_run

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            task = {
                'id': 'bugfix-001',
                'title': 'Fix sample bug',
                'repoPath': '/tmp/repo',
                'bugDescription': 'Sample',
                'reproSteps': ['pytest test_sample.py -q'],
                'expectedBehavior': 'Passes',
                'testCommand': 'pytest test_sample.py -q',
                'doneDefinition': ['tests pass'],
            }

            run_dir = initialize_task_run(base_dir, task, 'extra context')
            state = json.loads((run_dir / 'state.json').read_text())
            timeline = (run_dir / 'timeline.jsonl').read_text().strip().splitlines()

            self.assertEqual(state['taskId'], 'bugfix-001')
            self.assertEqual(state['status'], 'created')
            self.assertTrue((run_dir / 'task.json').exists())
            self.assertTrue((run_dir / 'context.md').exists())
            self.assertEqual(json.loads(timeline[0])['status'], 'created')


class WorktreeCommandTests(unittest.TestCase):
    def test_build_worktree_add_command(self):
        from scripts.bugfix_orchestrator import build_worktree_add_command
        cmd = build_worktree_add_command('/repo', '/repo/.worktrees/bugfix-001', 'bugfix/bugfix-001')
        self.assertEqual(
            cmd,
            ['git', '-C', '/repo', 'worktree', 'add', '-b', 'bugfix/bugfix-001', '/repo/.worktrees/bugfix-001'],
        )


class CheckerPreflightTests(unittest.TestCase):
    def test_rejects_empty_diff(self):
        from scripts.bugfix_orchestrator import run_checker_preflight

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / 'patch.diff').write_text('')
            (run_dir / 'test-report.txt').write_text('passed')
            (run_dir / 'worker-report.json').write_text(json.dumps({
                'taskId': 'bugfix-001',
                'status': 'passed',
                'reproduced': True,
                'filesChanged': ['src/a.py'],
                'testCommand': 'pytest -q',
                'testExitCode': 0,
                'risks': [],
                'summary': 'ok',
            }))

            result = run_checker_preflight(run_dir)
            self.assertEqual(result['status'], 'review_retry')
            self.assertIn('patch.diff is empty', result['reasons'])

    def test_rejects_missing_test_report(self):
        from scripts.bugfix_orchestrator import run_checker_preflight

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / 'patch.diff').write_text('diff --git a/foo b/foo')
            (run_dir / 'worker-report.json').write_text(json.dumps({
                'taskId': 'bugfix-001',
                'status': 'passed',
                'reproduced': True,
                'filesChanged': ['src/a.py'],
                'testCommand': 'pytest -q',
                'testExitCode': 0,
                'risks': [],
                'summary': 'ok',
            }))

            result = run_checker_preflight(run_dir)
            self.assertEqual(result['status'], 'review_retry')
            self.assertIn('test-report.txt is missing', result['reasons'])

    def test_rejects_invalid_worker_report(self):
        from scripts.bugfix_orchestrator import run_checker_preflight

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / 'patch.diff').write_text('diff --git a/foo b/foo')
            (run_dir / 'test-report.txt').write_text('passed')
            (run_dir / 'worker-report.json').write_text(json.dumps({
                'taskId': 'bugfix-001',
                'status': 'passed',
            }))

            result = run_checker_preflight(run_dir)
            self.assertEqual(result['status'], 'review_retry')
            self.assertTrue(any(reason.startswith('worker-report.json invalid:') for reason in result['reasons']))


if __name__ == '__main__':
    unittest.main()
