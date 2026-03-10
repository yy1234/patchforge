import argparse
import json
from pathlib import Path

from scripts.bugfix_orchestrator import (
    initialize_task_run,
    load_project_registry,
    mark_task_awaiting_user,
    read_task_state,
)
from scripts.feishu_task_bridge import render_commander_message
from scripts.zentao_intake import normalize_zentao_task

DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / 'runs' / 'tasks'
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'project_registry.json'


def handle_feishu_trigger(
    text: str,
    registry: list[dict],
    base_dir: Path,
    session_id: str,
) -> dict:
    task = normalize_zentao_task(text, registry=registry)
    run_dir = initialize_task_run(base_dir, task, f'Feishu inbound:\n{text}')

    if task.get('needsUserInput'):
        state = mark_task_awaiting_user(run_dir, session_id, ['项目名'])
        response = render_commander_message(
            'awaiting_info',
            task,
            state,
            missing_items=state.get('missingItems'),
        )
    else:
        state = read_task_state(run_dir)
        response = render_commander_message('task_started', task, state)

    return {
        'task': task,
        'runDir': str(run_dir),
        'responseMessage': response,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--text', required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--runs-dir', default=str(DEFAULT_RUNS_DIR))
    parser.add_argument('--registry-path', default=str(DEFAULT_REGISTRY_PATH))
    args = parser.parse_args(argv)

    result = handle_feishu_trigger(
        args.text,
        registry=load_project_registry(Path(args.registry_path)),
        base_dir=Path(args.runs_dir),
        session_id=args.session_id,
    )
    print(json.dumps(
        {
            'runDir': result['runDir'],
            'taskId': result['task']['id'],
            'responseMessage': result['responseMessage'],
        },
        ensure_ascii=False,
    ))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
