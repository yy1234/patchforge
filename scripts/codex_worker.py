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
