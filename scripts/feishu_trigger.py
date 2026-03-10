from pathlib import Path

from scripts.bugfix_orchestrator import initialize_task_run, mark_task_awaiting_user
from scripts.zentao_intake import normalize_zentao_task


def handle_feishu_trigger(
    text: str,
    registry: list[dict],
    base_dir: Path,
    session_id: str,
) -> dict:
    task = normalize_zentao_task(text)
    run_dir = initialize_task_run(base_dir, task, f'Feishu inbound:\n{text}')

    if task.get('needsUserInput'):
        mark_task_awaiting_user(run_dir, session_id, ['项目名'])

    return {
        'task': task,
        'runDir': str(run_dir),
    }
