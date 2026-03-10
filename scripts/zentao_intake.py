import hashlib
import re
from typing import Optional

from scripts.bugfix_orchestrator import match_project

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


def normalize_zentao_task(text: str, registry: Optional[list[dict]] = None) -> dict:
    url = extract_zentao_link(text) or ""
    matched_project = match_project(text, text, registry or []) if registry else None
    return {
        "id": build_zentao_task_id(url),
        "source": "feishu",
        "title": "Zentao task",
        "zentaoUrl": url,
        "repoCandidate": matched_project["id"] if matched_project else None,
        "repoPath": matched_project["repoPath"] if matched_project else "",
        "bugDescription": "",
        "reproSteps": [],
        "expectedBehavior": "",
        "testCommand": matched_project["testCommand"] if matched_project else "",
        "doneDefinition": ["Triaged from Zentao link"],
        "needsUserInput": matched_project is None,
    }
