import subprocess
from typing import Callable, Optional


def build_feishu_send_command(session_id: str, message: str, dry_run: bool = False) -> list[str]:
    command = [
        'openclaw',
        'message',
        'send',
        '--channel',
        'feishu',
        '--target',
        session_id,
        '--message',
        message,
    ]
    if dry_run:
        command.append('--dry-run')
    return command


def send_feishu_message(
    session_id: str,
    message: str,
    dry_run: bool = False,
    command_runner: Callable = subprocess.run,
) -> None:
    command_runner(
        build_feishu_send_command(session_id, message, dry_run=dry_run),
        capture_output=True,
        text=True,
        check=True,
    )
