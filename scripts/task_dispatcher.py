import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from scripts.bugfix_orchestrator import (
    ACTIVE_READY_TASK_STATES,
    iter_run_dirs,
    promote_next_queued_run,
    read_task,
    read_task_state,
    run_checker_preflight,
    write_task_state_with_metadata,
    append_timeline_event,
)
from scripts.codex_worker import classify_worker_run, execute_codex_worker
from scripts.feishu_notifier import send_feishu_message
from scripts.feishu_task_bridge import render_commander_message
from scripts.local_runtime_rules import apply_runtime_rules_to_workspace
from scripts.bugfix_orchestrator import write_task

RUNNABLE_STATUSES = {'created', 'coder_retrying', 'review_retry'}


def _copy_ignore(_src, names):
    ignored = {'.git', '.svn', '.dart_tool', 'build', 'DerivedData', 'DerivedData-Sim', 'output', 'temp'}
    return [name for name in names if name in ignored]


def prepare_task_workspace(
    run_dir: Path,
    task: dict,
    command_runner=subprocess.run,
) -> Path:
    repo_path = Path(task['repoPath'])
    workspace_path = run_dir / 'workspace'
    if workspace_path.exists():
        return workspace_path

    if (repo_path / '.git').exists():
        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        branch_name = f"bugfix/{task['id']}"
        command_runner(
            ['git', '-C', str(repo_path), 'worktree', 'add', '-b', branch_name, str(workspace_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return workspace_path

    shutil.copytree(
        repo_path,
        workspace_path,
        ignore=_copy_ignore,
        symlinks=True,
        ignore_dangling_symlinks=True,
    )
    return workspace_path


def _find_next_runnable_run(base_dir: Path) -> Optional[Path]:
    candidates = []
    for run_dir in iter_run_dirs(base_dir):
        state_path = run_dir / 'state.json'
        if not state_path.exists():
            continue
        state = read_task_state(run_dir)
        if state.get('status') in RUNNABLE_STATUSES:
            candidates.append((state.get('updatedAt', ''), run_dir))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


def _read_context(run_dir: Path) -> str:
    return (run_dir / 'context.md').read_text()


def _write_status(run_dir: Path, task: dict, status: str, metadata: Optional[dict] = None) -> dict:
    state = write_task_state_with_metadata(run_dir, task['id'], status, metadata=metadata)
    append_timeline_event(run_dir, task['id'], status)
    return state


def notify_dispatch_result(task: dict, state: dict, dry_run: bool = False) -> None:
    session_id = state.get('sessionId')
    if not session_id:
        return

    event = None
    note = None
    if state['status'] == 'done':
        event = 'task_completed'
        note = '自动调度执行完成'
    elif state['status'] in {'review_retry', 'coder_retrying'}:
        event = 'task_retrying'
        if state['status'] == 'review_retry':
            reasons = state.get('checkerReasons') or []
            note = '；'.join(reasons) if reasons else 'checker 未通过，等待重试'
        else:
            note = 'worker 执行未完成，等待重试'
    elif state['status'] == 'needs_human':
        event = 'blocked_backend'
        note = '自动执行未完成，需要人工介入'

    if event is None:
        return

    message = render_commander_message(event, task, state, note=note)
    send_feishu_message(session_id, message, dry_run=dry_run)


def simulate_success_workspace(run_dir: Path, task: dict) -> Path:
    workspace = run_dir / 'workspace-simulated'
    workspace.mkdir(exist_ok=True)
    return workspace


def simulate_success_worker(run_dir: Path, task: dict, context_text: str, worktree_path: str) -> dict:
    for name, content in {
        'worker-report.json': json.dumps({
            'taskId': task['id'],
            'status': 'passed',
            'reproduced': True,
            'filesChanged': [],
            'testCommand': task['testCommand'],
            'testExitCode': 0,
            'risks': [],
            'summary': 'simulated success',
        }),
        'patch.diff': 'diff --git a/README b/README',
        'test-report.txt': 'simulated success',
        'notes.md': 'simulated success',
    }.items():
        (run_dir / name).write_text(content)
    return {
        'exit_code': 0,
        'timed_out': False,
        'stalled': False,
        'artifacts_present': ['worker-report.json', 'patch.diff', 'test-report.txt', 'notes.md'],
    }


def dispatch_once(
    base_dir: Path,
    worker_runner: Callable = execute_codex_worker,
    checker_runner: Callable = run_checker_preflight,
    workspace_preparer: Callable = prepare_task_workspace,
    notifier: Optional[Callable] = None,
) -> Optional[dict]:
    promote_next_queued_run(base_dir)
    run_dir = _find_next_runnable_run(base_dir)
    if run_dir is None:
        return None

    task = read_task(run_dir)
    state = read_task_state(run_dir)
    workspace_path = workspace_preparer(run_dir, task)
    if task.get('runtimeRules'):
        try:
            task['runtimeRules'] = apply_runtime_rules_to_workspace(task, workspace_path)
            write_task(run_dir, task)
        except ValueError as err:
            final_state = _write_status(
                run_dir,
                task,
                'needs_human',
                metadata={
                    'sessionId': state.get('sessionId'),
                    'sourceTaskId': task.get('sourceTaskId'),
                    'workspacePath': str(workspace_path),
                    'switchReason': str(err),
                },
            )
            return final_state
    metadata = {
        'sessionId': state.get('sessionId'),
        'sourceTaskId': task.get('sourceTaskId'),
        'workspacePath': str(workspace_path),
    }
    if task.get('runtimeRules', {}).get('switchPerformed'):
        metadata['environmentSwitchedTo'] = task['runtimeRules'].get('currentEnvironment')
    _write_status(run_dir, task, 'running_coder', metadata=metadata)

    worker_result = worker_runner(
        run_dir=run_dir,
        task=task,
        context_text=_read_context(run_dir),
        worktree_path=str(workspace_path),
    )
    outcome = classify_worker_run(
        exit_code=worker_result['exit_code'],
        timed_out=worker_result['timed_out'],
        stalled=worker_result['stalled'],
        artifacts_present=worker_result['artifacts_present'],
    )

    if outcome['status'] != 'passed':
        next_status = 'coder_retrying' if outcome.get('retryable') else 'needs_human'
        final_state = _write_status(run_dir, task, next_status, metadata=metadata)
        if notifier:
            notifier(task, final_state)
        return final_state

    _write_status(run_dir, task, 'running_checker', metadata=metadata)
    checker_result = checker_runner(run_dir)
    if checker_result['status'] == 'review_passed':
        final_state = _write_status(run_dir, task, 'done', metadata=metadata)
        if notifier:
            notifier(task, final_state)
        return final_state

    final_state = _write_status(
        run_dir,
        task,
        checker_result['status'],
        metadata={**metadata, 'checkerReasons': checker_result.get('reasons', [])},
    )
    if notifier:
        notifier(task, final_state)
    return final_state


def main(
    argv=None,
    worker_runner: Callable = execute_codex_worker,
    checker_runner: Callable = run_checker_preflight,
    workspace_preparer: Callable = prepare_task_workspace,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs-dir', required=True)
    parser.add_argument('--simulate-success', action='store_true')
    parser.add_argument('--notify', action='store_true')
    parser.add_argument('--notify-dry-run', action='store_true')
    args = parser.parse_args(argv)

    if args.simulate_success:
        worker_runner = simulate_success_worker
        workspace_preparer = simulate_success_workspace

    notifier = None
    if args.notify or args.notify_dry_run:
        notifier = lambda task, state: notify_dispatch_result(task, state, dry_run=args.notify_dry_run)

    result = dispatch_once(
        Path(args.runs_dir),
        worker_runner=worker_runner,
        checker_runner=checker_runner,
        workspace_preparer=workspace_preparer,
        notifier=notifier,
    )
    print(json.dumps(result or {'status': 'idle'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
