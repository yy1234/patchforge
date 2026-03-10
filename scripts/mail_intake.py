import hashlib

from scripts.bugfix_orchestrator import match_project

BUGFIX_KEYWORDS = (
    'bug',
    'fix',
    'error',
    'issue',
    'white screen',
    'blank',
    '报错',
    '白屏',
)


def classify_task_type(subject: str, body: str) -> str:
    haystack = f'{subject}\n{body}'.lower()
    return 'bugfix' if any(keyword in haystack for keyword in BUGFIX_KEYWORDS) else 'task'


def build_mail_task_id(message_id: str) -> str:
    digest = hashlib.sha1(message_id.encode('utf-8')).hexdigest()[:12]
    return f'mail-task-{digest}'


def normalize_mail_task(message: dict, registry: list[dict]) -> dict:
    subject = message.get('subject', '').strip()
    body = message.get('bodyText', '').strip()
    message_id = message.get('messageId') or f"{message.get('from', 'unknown')}:{subject}"
    matched_project = match_project(subject, body, registry) if registry else None

    return {
        'id': build_mail_task_id(message_id),
        'source': 'mail',
        'mailMessageId': message_id,
        'title': subject,
        'rawSubject': subject,
        'rawFrom': message.get('from'),
        'taskType': classify_task_type(subject, body),
        'bugDescription': body,
        'repoPath': matched_project['repoPath'] if matched_project else '',
        'reproSteps': [],
        'expectedBehavior': '',
        'testCommand': matched_project['testCommand'] if matched_project else '',
        'doneDefinition': ['Triaged from email'],
        'repoCandidate': matched_project['id'] if matched_project else None,
        'needsUserInput': matched_project is None,
    }
