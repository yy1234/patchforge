import argparse
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.bugfix_orchestrator import initialize_task_run, load_project_registry
from scripts.mail_intake import normalize_mail_task

DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / 'runs' / 'tasks'
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'project_registry.example.json'
DRY_RUN_MESSAGE = {
    'messageId': '<dry-run@example.com>',
    'subject': 'Fix white screen in sample app',
    'from': 'dry-run@example.com',
    'bodyText': 'The login page shows a white screen after release.',
}


def load_mailbox_config(env: dict) -> dict:
    required = ['MAIL_HOST', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD']
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise ValueError(f'Missing mailbox env vars: {missing}')

    return {
        'host': env['MAIL_HOST'],
        'port': int(env['MAIL_PORT']),
        'username': env['MAIL_USERNAME'],
        'password': env['MAIL_PASSWORD'],
        'folder': env.get('MAIL_FOLDER', 'INBOX'),
    }


def poll_mailbox_once(imap_client, registry: list[dict], on_task) -> int:
    processed = 0
    for message in imap_client.fetch_unseen_messages():
        task = normalize_mail_task(message, registry)
        on_task(task)
        processed += 1
    return processed


def emit_task_run(base_dir: Path, task: dict) -> Path:
    context = (
        f"Mail source: {task.get('rawFrom', 'unknown')}\n"
        f"Mail subject: {task.get('rawSubject', task['title'])}\n"
        f"Mail task type: {task.get('taskType', 'task')}\n"
    )
    return initialize_task_run(base_dir, task, context)


def run_dry_mode(registry_path: Path = DEFAULT_REGISTRY_PATH, base_dir: Path = DEFAULT_RUNS_DIR) -> Path:
    registry = load_project_registry(registry_path)
    task = normalize_mail_task(DRY_RUN_MESSAGE, registry)
    return emit_task_run(base_dir, task)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--registry-path', default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument('--runs-dir', default=str(DEFAULT_RUNS_DIR))
    args = parser.parse_args(argv)

    registry_path = Path(args.registry_path)
    runs_dir = Path(args.runs_dir)

    if args.dry_run:
        run_dir = run_dry_mode(registry_path=registry_path, base_dir=runs_dir)
        print(json.dumps({'mode': 'dry-run', 'runDir': str(run_dir)}, ensure_ascii=False))
        return 0

    load_mailbox_config(os.environ)
    print(json.dumps({'mode': 'configured'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
