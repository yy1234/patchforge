import json
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / 'templates' / 'bugfix_worker_prompt.md'
REQUIRED_REPORT_KEYS = [
    'taskId',
    'status',
    'reproduced',
    'filesChanged',
    'testCommand',
    'testExitCode',
    'risks',
    'summary',
]
REQUIRED_WORKER_ARTIFACTS = {
    'worker-report.json',
    'patch.diff',
    'test-report.txt',
    'notes.md',
}


def render_worker_prompt(task: dict, context_text: str) -> str:
    template = TEMPLATE_PATH.read_text()
    return (
        f"{template}\n\n"
        f"Task ID: {task['id']}\n"
        f"Bug: {task['bugDescription']}\n"
        f"Test command: {task['testCommand']}\n"
        f"Done definition: {task['doneDefinition']}\n"
        f"Context:\n{context_text}\n"
    )


def build_codex_command(worktree_path: str, prompt_file: str) -> list[str]:
    return ['codex', '--add-dir', worktree_path, 'exec', prompt_file]


def load_worker_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    missing = [key for key in REQUIRED_REPORT_KEYS if key not in report]
    if missing:
        raise ValueError(f'Missing report keys: {missing}')
    return report


def classify_worker_run(
    exit_code,
    timed_out: bool,
    stalled: bool,
    artifacts_present: list[str],
) -> dict:
    artifact_set = set(artifacts_present)

    if timed_out:
        return {'status': 'timeout', 'retryable': True}

    if stalled:
        return {'status': 'stalled', 'retryable': True}

    if exit_code == 0 and not REQUIRED_WORKER_ARTIFACTS.issubset(artifact_set):
        return {'status': 'artifact_missing', 'retryable': True}

    if exit_code == 0:
        return {'status': 'passed', 'retryable': False}

    return {'status': 'failed', 'retryable': False}


def should_retry_worker(outcome: dict, attempt_count: int, max_retries: int) -> bool:
    return bool(outcome.get('retryable')) and attempt_count < max_retries
