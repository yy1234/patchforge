import hashlib
import re
from typing import Optional

URL_PATTERN = re.compile(r"https?://\S+")


def extract_zentao_link(text: str) -> Optional[str]:
    match = URL_PATTERN.search(text)
    if not match:
        return None
    url = match.group(0).rstrip(").,;")
    return url


def build_zentao_task_id(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"zentao-task-{digest}"


def normalize_zentao_task(text: str) -> dict:
    url = extract_zentao_link(text) or ""
    return {
        "id": build_zentao_task_id(url),
        "source": "feishu",
        "title": "Zentao task",
        "zentaoUrl": url,
        "repoCandidate": None,
        "repoPath": "",
        "bugDescription": "",
        "reproSteps": [],
        "expectedBehavior": "",
        "testCommand": "",
        "doneDefinition": ["Triaged from Zentao link"],
        "needsUserInput": True,
    }
