import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from scripts.bugfix_orchestrator import load_project_registry
from scripts.feishu_trigger import handle_feishu_trigger
from scripts.zentao_intake import extract_zentao_link

DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / 'runs' / 'tasks'
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / 'data' / 'project_registry.json'


def extract_text_message(payload: dict) -> Optional[dict]:
    event = payload.get('event') or {}
    message = event.get('message') or {}

    if payload.get('header', {}).get('event_type') != 'im.message.receive_v1':
        return None

    if message.get('chat_type') != 'p2p' or message.get('message_type') != 'text':
        return None

    content = message.get('content') or '{}'
    try:
        content_data = json.loads(content)
    except json.JSONDecodeError:
        return None

    text = content_data.get('text', '').strip()
    if not text:
        return None

    sender = event.get('sender', {}).get('sender_id', {})
    session_id = (
        sender.get('open_id')
        or sender.get('user_id')
        or sender.get('union_id')
        or ''
    )
    if not session_id:
        return None

    return {
        'sessionId': session_id,
        'messageId': message.get('message_id', ''),
        'text': text,
    }


def should_trigger_zentao_flow(text: str) -> bool:
    return text.startswith('禅道:') or extract_zentao_link(text) is not None


def handle_feishu_inbound(
    payload: dict,
    base_dir: Path,
    registry: Optional[list[dict]] = None,
) -> dict:
    if payload.get('challenge'):
        return {
            'eventType': 'url_verification',
            'challenge': payload['challenge'],
        }

    inbound = extract_text_message(payload)
    if not inbound:
        return {
            'eventType': 'ignored',
            'reason': 'unsupported_message',
        }

    if not should_trigger_zentao_flow(inbound['text']):
        return {
            'eventType': 'ignored',
            'reason': 'not_a_zentao_trigger',
            'sessionId': inbound['sessionId'],
            'messageId': inbound['messageId'],
        }

    if registry is None:
        registry = load_project_registry(DEFAULT_REGISTRY_PATH)

    result = handle_feishu_trigger(
        inbound['text'],
        registry=registry,
        base_dir=base_dir,
        session_id=inbound['sessionId'],
    )
    return {
        'eventType': 'triggered',
        'sessionId': inbound['sessionId'],
        'messageId': inbound['messageId'],
        'taskId': result['task']['id'],
        'runDir': result['runDir'],
        'responseMessage': result['responseMessage'],
    }


def load_payload(payload_file: Optional[str]) -> dict:
    if payload_file:
        return json.loads(Path(payload_file).read_text())
    return json.loads(sys.stdin.read())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--payload-file')
    parser.add_argument('--runs-dir', default=str(DEFAULT_RUNS_DIR))
    parser.add_argument('--registry-path', default=str(DEFAULT_REGISTRY_PATH))
    args = parser.parse_args(argv)

    result = handle_feishu_inbound(
        load_payload(args.payload_file),
        base_dir=Path(args.runs_dir),
        registry=load_project_registry(Path(args.registry_path)),
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
