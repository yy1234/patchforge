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


if __name__ == '__main__':
    unittest.main()
