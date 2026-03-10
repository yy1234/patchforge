import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.codex_worker import load_worker_report
from scripts.feishu_task_bridge import reply_matches_task

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
ASCII_KEYWORD_PATTERN = re.compile(r'^[a-z0-9_.-]+$')


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


def normalize_project_entry(entry: dict) -> dict:
    if 'repoPath' in entry and 'testCommand' in entry:
        normalized = dict(entry)
        normalized['keywords'] = list(dict.fromkeys(entry.get('keywords', [])))
        return normalized

    root_path = entry.get('rootPath')
    commands = entry.get('commands') or {}
    aliases = entry.get('aliases') or []

    keywords = []
    for value in [entry.get('name'), *aliases, *(entry.get('keywords') or [])]:
        if isinstance(value, str) and value.strip():
            keywords.append(value.strip())

    normalized = {
        'id': entry['id'],
        'repoPath': root_path or '',
        'testCommand': commands.get('test', ''),
        'keywords': list(dict.fromkeys(keywords)),
    }
    normalized.update(entry)
    normalized['repoPath'] = root_path or normalized['repoPath']
    normalized['testCommand'] = commands.get('test', normalized['testCommand'])
    normalized['keywords'] = list(dict.fromkeys(keywords))
    return normalized


def load_project_registry(path: Path) -> list[dict]:
    raw = json.loads(path.read_text())
    if isinstance(raw, list):
        registry = raw
    elif isinstance(raw, dict) and isinstance(raw.get('projects'), list):
        registry = [
            normalize_project_entry(entry)
            for entry in raw['projects']
            if entry.get('role') == 'app' and entry.get('matchEnabled', True)
        ]
    else:
        raise ValueError('Project registry must be a list or an object with a projects list')

    for entry in registry:
        validate_project_entry(entry)

    return registry


def keyword_matches(keyword: str, haystack: str) -> bool:
    normalized = keyword.strip().lower()
    if not normalized:
        return False

    if ASCII_KEYWORD_PATTERN.fullmatch(normalized):
        pattern = rf'(?<![a-z0-9_]){re.escape(normalized)}(?![a-z0-9_])'
        return re.search(pattern, haystack) is not None

    return normalized in haystack


def match_project(subject: str, body: str, registry: list[dict]) -> Optional[dict]:
    haystack = f'{subject}\n{body}'.lower()
    best_match = None
    best_score = 0

    for entry in registry:
        score = sum(1 for keyword in entry['keywords'] if keyword_matches(keyword, haystack))
        if score > best_score:
            best_match = entry
            best_score = score

    return best_match


def write_task_files(run_dir: Path, task: dict, context_text: str) -> None:
    validate_task(task)
    (run_dir / 'task.json').write_text(json.dumps(task, ensure_ascii=False, indent=2) + '\n')
    (run_dir / 'context.md').write_text(context_text.rstrip() + '\n')


def write_task_state(run_dir: Path, task_id: str, status: str) -> dict:
    return write_task_state_with_metadata(run_dir, task_id, status)


def write_task_state_with_metadata(
    run_dir: Path,
    task_id: str,
    status: str,
    metadata: Optional[dict] = None,
) -> dict:
    if status not in VALID_TASK_STATES:
        raise ValueError(f'Unsupported task status: {status}')

    state = {
        'taskId': task_id,
        'status': status,
        'updatedAt': datetime.now(timezone.utc).isoformat(),
    }
    if metadata:
        state.update(metadata)
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


def read_task_state(run_dir: Path) -> dict:
    return json.loads((run_dir / 'state.json').read_text())


def mark_task_awaiting_user(run_dir: Path, session_id: str, missing_items: list[str]) -> dict:
    task = json.loads((run_dir / 'task.json').read_text())
    next_state = write_task_state_with_metadata(
        run_dir,
        task['id'],
        'awaiting_user',
        metadata={
            'sessionId': session_id,
            'missingItems': missing_items,
        },
    )
    append_timeline_event(run_dir, task['id'], 'awaiting_user')
    return next_state


def resume_task_from_reply(run_dir: Path, reply: dict) -> dict:
    task = json.loads((run_dir / 'task.json').read_text())
    state = read_task_state(run_dir)

    if state['status'] != 'awaiting_user':
        raise ValueError('Task is not waiting for user input')

    if not reply_matches_task(reply, task['id'], state.get('sessionId')):
        raise ValueError('Reply does not match task context')

    context_path = run_dir / 'context.md'
    context_text = context_path.read_text().rstrip()
    reply_text = reply.get('message', '').strip()
    context_path.write_text(f'{context_text}\n\nUser reply:\n{reply_text}\n')

    next_state = write_task_state_with_metadata(
        run_dir,
        task['id'],
        'queued',
        metadata={
            'sessionId': state.get('sessionId'),
            'lastUserReply': reply_text,
            'missingItems': [],
        },
    )
    append_timeline_event(run_dir, task['id'], 'queued')
    return next_state


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
