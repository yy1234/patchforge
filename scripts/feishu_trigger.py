import argparse
import json
from pathlib import Path
from typing import Optional

from scripts.bugfix_orchestrator import (
    append_context_entry,
    find_active_run,
    initialize_task_run,
    load_project_registry,
    maybe_queue_run,
    merge_task_updates,
    queue_position,
    read_task,
    read_task_state,
    triage_task,
    write_task,
)
from scripts.feishu_task_bridge import render_commander_message
from scripts.local_runtime_rules import load_local_runtime_rules, enrich_task_with_runtime_rules
from scripts.zentao_intake import normalize_zentao_task

DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / 'runs' / 'tasks'
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'project_registry.json'
DEFAULT_LOCAL_RULES_PATH = Path(__file__).resolve().parent.parent / 'data' / 'local_runtime_rules.json'


def render_task_response(task: dict, state: dict, base_dir: Path, run_dir: Path) -> str:
    if state['status'] == 'awaiting_user':
        return render_commander_message(
            'awaiting_info',
            task,
            state,
            missing_items=state.get('missingItems'),
        )

    if state['status'] == 'needs_human':
        return render_commander_message(
            'task_blocked',
            task,
            state,
            note=state.get('triageReason'),
        )

    if state['status'] == 'queued':
        position = queue_position(base_dir, run_dir)
        note = '等待空闲槽位'
        if position:
            note = f'前方还有 {max(position - 1, 0)} 个任务'
        return render_commander_message('task_queued', task, state, note=note)

    return render_commander_message('task_started', task, state, note=state.get('triageNote'))


def handle_feishu_trigger(
    text: str,
    registry: list[dict],
    base_dir: Path,
    session_id: str,
    local_rules: Optional[dict] = None,
) -> dict:
    if local_rules is None:
        local_rules = load_local_runtime_rules(DEFAULT_LOCAL_RULES_PATH)
    task = normalize_zentao_task(text, registry=registry)
    task = enrich_task_with_runtime_rules(task, local_rules)
    existing_run = find_active_run(base_dir, session_id, task['sourceTaskId'])
    if existing_run:
        append_context_entry(existing_run, 'Feishu follow-up', text)
        existing_task = read_task(existing_run)
        merged_task = merge_task_updates(existing_task, task)
        write_task(existing_run, merged_task)
        state = read_task_state(existing_run)

        if state['status'] == 'awaiting_user' and not merged_task.get('needsUserInput'):
            state = maybe_queue_run(
                base_dir,
                existing_run,
                merged_task,
                session_id=session_id,
                target_status='created',
            )

        response = render_task_response(merged_task, state, base_dir, existing_run)
        return {
            'task': merged_task,
            'runDir': str(existing_run),
            'responseMessage': response,
        }

    run_dir = initialize_task_run(base_dir, task, f'Feishu inbound:\n{text}')
    triage = triage_task(task)

    if triage['decision'] == 'awaiting_info':
        state = maybe_queue_run(
            base_dir,
            run_dir,
            task,
            session_id=session_id,
            target_status='awaiting_user',
            missing_items=triage['missingItems'],
        )
        state['triageDecision'] = 'awaiting_info'
        (run_dir / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    elif triage['decision'] == 'blocked':
        state = maybe_queue_run(
            base_dir,
            run_dir,
            task,
            session_id=session_id,
            target_status='needs_human',
        )
        state['triageDecision'] = 'blocked'
        state['triageReason'] = triage['reason']
        (run_dir / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    else:
        state = maybe_queue_run(
            base_dir,
            run_dir,
            task,
            session_id=session_id,
            target_status='created',
        )
        state['triageDecision'] = 'run'
        if triage.get('note'):
            state['triageNote'] = triage['note']
        (run_dir / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')

    response = render_task_response(task, state, base_dir, run_dir)

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
    parser.add_argument('--local-rules-path', default=str(DEFAULT_LOCAL_RULES_PATH))
    args = parser.parse_args(argv)

    result = handle_feishu_trigger(
        args.text,
        registry=load_project_registry(Path(args.registry_path)),
        base_dir=Path(args.runs_dir),
        session_id=args.session_id,
        local_rules=load_local_runtime_rules(Path(args.local_rules_path)),
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
