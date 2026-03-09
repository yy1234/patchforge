import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.codex_worker import load_worker_report

REQUIRED_TASK_KEYS = [
    'id',
    'title',
    'repoPath',
    'bugDescription',
    'reproSteps',
    'expectedBehavior',
    'testCommand',
    'doneDefinition',
]
REQUIRED_PROJECT_KEYS = [
    'id',
    'repoPath',
    'testCommand',
    'keywords',
]
VALID_TASK_STATES = {
    'created',
    'awaiting_user',
    'queued',
    'running_coder',
    'coder_retrying',
    'blocked_backend',
    'running_checker',
    'review_retry',
    'review_passed',
    'needs_human',
    'done',
}


def ensure_run_layout(base_dir: Path, task_id: str) -> Path:
    run_dir = base_dir / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def validate_task(task: dict) -> None:
    missing = [key for key in REQUIRED_TASK_KEYS if key not in task]
    if missing:
        raise ValueError(f'Missing task keys: {missing}')


def validate_project_entry(entry: dict) -> None:
    missing = [key for key in REQUIRED_PROJECT_KEYS if key not in entry]
    if missing:
        raise ValueError(f'Missing project keys: {missing}')

    if not entry['keywords']:
        raise ValueError('Project keywords cannot be empty')


def load_project_registry(path: Path) -> list[dict]:
    registry = json.loads(path.read_text())
    if not isinstance(registry, list):
        raise ValueError('Project registry must be a list')

    for entry in registry:
        validate_project_entry(entry)

    return registry


def match_project(subject: str, body: str, registry: list[dict]) -> Optional[dict]:
    haystack = f'{subject}\n{body}'.lower()
    best_match = None
    best_score = 0

    for entry in registry:
        score = sum(1 for keyword in entry['keywords'] if keyword.lower() in haystack)
        if score > best_score:
            best_match = entry
            best_score = score

    return best_match


def write_task_files(run_dir: Path, task: dict, context_text: str) -> None:
    validate_task(task)
    (run_dir / 'task.json').write_text(json.dumps(task, ensure_ascii=False, indent=2) + '\n')
    (run_dir / 'context.md').write_text(context_text.rstrip() + '\n')


def write_task_state(run_dir: Path, task_id: str, status: str) -> dict:
    if status not in VALID_TASK_STATES:
        raise ValueError(f'Unsupported task status: {status}')

    state = {
        'taskId': task_id,
        'status': status,
        'updatedAt': datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    return state


def append_timeline_event(run_dir: Path, task_id: str, status: str) -> None:
    event = {
        'taskId': task_id,
        'status': status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    with (run_dir / 'timeline.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + '\n')


def initialize_task_run(base_dir: Path, task: dict, context_text: str) -> Path:
    run_dir = ensure_run_layout(base_dir, task['id'])
    write_task_files(run_dir, task, context_text)
    write_task_state(run_dir, task['id'], 'created')
    append_timeline_event(run_dir, task['id'], 'created')
    return run_dir


def run_checker_preflight(run_dir: Path) -> dict:
    reasons = []
    patch_path = run_dir / 'patch.diff'
    test_report_path = run_dir / 'test-report.txt'
    worker_report_path = run_dir / 'worker-report.json'

    if not patch_path.exists() or not patch_path.read_text().strip():
        reasons.append('patch.diff is empty')

    if not test_report_path.exists():
        reasons.append('test-report.txt is missing')

    if not worker_report_path.exists():
        reasons.append('worker-report.json is missing')
    else:
        try:
            load_worker_report(worker_report_path)
        except ValueError as err:
            reasons.append(f'worker-report.json invalid: {err}')

    if reasons:
        return {'status': 'review_retry', 'reasons': reasons}

    return {'status': 'review_passed', 'reasons': []}


def build_worktree_add_command(repo_path: str, worktree_path: str, branch_name: str) -> list[str]:
    return ['git', '-C', repo_path, 'worktree', 'add', '-b', branch_name, worktree_path]


def build_worktree_remove_command(repo_path: str, worktree_path: str) -> list[str]:
    return ['git', '-C', repo_path, 'worktree', 'remove', '--force', worktree_path]
