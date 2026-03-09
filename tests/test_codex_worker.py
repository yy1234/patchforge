import json
import tempfile
import unittest
from pathlib import Path


class WorkerPromptTests(unittest.TestCase):
    def test_prompt_contains_required_sections(self):
        from scripts.codex_worker import render_worker_prompt
        prompt = render_worker_prompt(
            task={
                'id': 'bugfix-001',
                'bugDescription': 'Fix sample',
                'testCommand': 'pytest -q',
                'doneDefinition': ['tests pass'],
            },
            context_text='extra context',
        )
        self.assertIn('You must reproduce the bug', prompt)
        self.assertIn('Write worker-report.json', prompt)
        self.assertIn('pytest -q', prompt)


class WorkerCommandTests(unittest.TestCase):
    def test_build_codex_command(self):
        from scripts.codex_worker import build_codex_command
        cmd = build_codex_command('/repo/worktree', '/runs/bugfix-001/prompt.md')
        self.assertEqual(cmd[:3], ['codex', '--add-dir', '/repo/worktree'])
        self.assertEqual(cmd[-1], '/runs/bugfix-001/prompt.md')


class WorkerReportTests(unittest.TestCase):
    def test_load_worker_report(self):
        from scripts.codex_worker import load_worker_report
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / 'worker-report.json'
            report_path.write_text(json.dumps({
                'taskId': 'bugfix-001',
                'status': 'passed',
                'reproduced': True,
                'filesChanged': ['src/a.py'],
                'testCommand': 'pytest -q',
                'testExitCode': 0,
                'risks': [],
                'summary': 'ok'
            }))
            report = load_worker_report(report_path)
            self.assertEqual(report['status'], 'passed')


class WorkerWatchdogTests(unittest.TestCase):
    def test_classifies_timeout_as_retryable(self):
        from scripts.codex_worker import classify_worker_run

        outcome = classify_worker_run(exit_code=124, timed_out=True, stalled=False, artifacts_present=['worker-report.json'])

        self.assertEqual(outcome['status'], 'timeout')
        self.assertTrue(outcome['retryable'])

    def test_classifies_stall_as_retryable(self):
        from scripts.codex_worker import classify_worker_run

        outcome = classify_worker_run(exit_code=None, timed_out=False, stalled=True, artifacts_present=[])

        self.assertEqual(outcome['status'], 'stalled')
        self.assertTrue(outcome['retryable'])

    def test_classifies_missing_artifacts_as_retryable(self):
        from scripts.codex_worker import classify_worker_run

        outcome = classify_worker_run(exit_code=0, timed_out=False, stalled=False, artifacts_present=['worker-report.json'])

        self.assertEqual(outcome['status'], 'artifact_missing')
        self.assertTrue(outcome['retryable'])

    def test_classifies_success_when_required_artifacts_exist(self):
        from scripts.codex_worker import classify_worker_run

        outcome = classify_worker_run(
            exit_code=0,
            timed_out=False,
            stalled=False,
            artifacts_present=['worker-report.json', 'patch.diff', 'test-report.txt', 'notes.md'],
        )

        self.assertEqual(outcome['status'], 'passed')
        self.assertFalse(outcome['retryable'])

    def test_caps_retries_for_retryable_failures(self):
        from scripts.codex_worker import should_retry_worker

        self.assertTrue(should_retry_worker({'retryable': True}, attempt_count=1, max_retries=2))
        self.assertFalse(should_retry_worker({'retryable': True}, attempt_count=2, max_retries=2))
        self.assertFalse(should_retry_worker({'retryable': False}, attempt_count=0, max_retries=2))


if __name__ == '__main__':
    unittest.main()
