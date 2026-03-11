import json
import subprocess
from pathlib import Path
from typing import Optional

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


def render_worker_prompt(
    task: dict,
    context_text: str,
    run_dir: Optional[Path] = None,
    worktree_path: Optional[str] = None,
) -> str:
    template = TEMPLATE_PATH.read_text()
    location_block = ''
    if run_dir is not None:
        location_block += f'Run directory: {run_dir}\n'
    if worktree_path is not None:
        location_block += f'Worktree path: {worktree_path}\n'
    return (
        f"{template}\n\n"
        f"Task ID: {task['id']}\n"
        f"Bug: {task['bugDescription']}\n"
        f"Test command: {task['testCommand']}\n"
        f"Done definition: {task['doneDefinition']}\n"
        f"{location_block}"
        f"Context:\n{context_text}\n"
    )


def build_codex_command(worktree_path: str, prompt_file: str) -> list[str]:
    return ['codex', '--add-dir', worktree_path, 'exec', prompt_file]


def write_worker_prompt(
    run_dir: Path,
    task: dict,
    context_text: str,
    worktree_path: str,
) -> Path:
    prompt_path = run_dir / 'prompt.md'
    prompt_path.write_text(
        render_worker_prompt(
            task=task,
            context_text=context_text,
            run_dir=run_dir,
            worktree_path=worktree_path,
        )
    )
    return prompt_path


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


def execute_codex_worker(
    run_dir: Path,
    task: dict,
    context_text: str,
    worktree_path: str,
    exec_runner=subprocess.run,
    timeout: int = 1800,
) -> dict:
    prompt_path = write_worker_prompt(
        run_dir=run_dir,
        task=task,
        context_text=context_text,
        worktree_path=worktree_path,
    )
    command = build_codex_command(worktree_path, str(prompt_path))
    timed_out = False
    try:
        result = exec_runner(
            command,
            cwd=str(run_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = 124

    artifacts_present = [path.name for path in run_dir.iterdir() if path.is_file()]
    return {
        'exit_code': exit_code,
        'timed_out': timed_out,
        'stalled': False,
        'artifacts_present': artifacts_present,
    }
