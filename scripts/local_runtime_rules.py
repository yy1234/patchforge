import json
from pathlib import Path


DEFAULT_LOCAL_RULES_PATH = Path(__file__).resolve().parent.parent / 'data' / 'local_runtime_rules.json'


def load_local_runtime_rules(path: Path = DEFAULT_LOCAL_RULES_PATH) -> dict:
    if not path.exists():
        return {'version': 1, 'projects': {}}
    return json.loads(path.read_text())


def _active_source_text(repo_path: str, entry_file: str) -> str:
    path = Path(repo_path) / entry_file
    if not path.exists():
        return ''
    active_lines = []
    for line in path.read_text().splitlines():
        if line.strip().startswith('//'):
            continue
        active_lines.append(line)
    return '\n'.join(active_lines)


def detect_current_environment(repo_path: str, rule: dict) -> str:
    entry_file = rule.get('entryFile')
    if not entry_file:
        return 'unknown'

    active_text = _active_source_text(repo_path, entry_file)
    markers = rule.get('environment', {}).get('activeProfileMarkers', {})
    for profile, values in markers.items():
        if any(value in active_text for value in values):
            return profile
    return 'unknown'


def enrich_task_with_runtime_rules(task: dict, rules: dict) -> dict:
    project_id = task.get('repoCandidate')
    if not project_id:
        return task

    project_rule = (rules.get('projects') or {}).get(project_id)
    if not project_rule:
        return task

    current_environment = detect_current_environment(task.get('repoPath', ''), project_rule)
    preferred_environment = project_rule.get('environment', {}).get('preferredForAutomation')
    auto_switch = project_rule.get('environment', {}).get('autoSwitchRule', {})
    switch_required = (
        current_environment != 'unknown'
        and auto_switch.get('ifCurrentProfile') == current_environment
        and auto_switch.get('switchTo') == preferred_environment
    )

    runtime_rules = {
        'entryFile': project_rule.get('entryFile'),
        'currentEnvironment': current_environment,
        'preferredEnvironment': preferred_environment,
        'switchRequired': switch_required,
        'credentialPolicy': 'remarks -> local default',
        'defaultUsername': project_rule.get('credentials', {}).get('localDefault', {}).get('username', ''),
        'hasDefaultPassword': bool(project_rule.get('credentials', {}).get('localDefault', {}).get('password')),
        'backendRequiredWhenBlocked': project_rule.get('backendCollaboration', {}).get('requiredWhenBlocked', []),
    }

    enriched = dict(task)
    enriched['runtimeRules'] = runtime_rules
    return enriched


def apply_runtime_rules_to_workspace(task: dict, workspace_path: Path) -> dict:
    runtime_rules = dict(task.get('runtimeRules') or {})
    if not runtime_rules.get('switchRequired'):
        runtime_rules['switchPerformed'] = False
        return runtime_rules

    entry_file = runtime_rules.get('entryFile')
    markers = runtime_rules.get('profileMarkers') or {}
    current_environment = runtime_rules.get('currentEnvironment')
    preferred_environment = runtime_rules.get('preferredEnvironment')
    source_markers = markers.get(current_environment) or []
    target_markers = markers.get(preferred_environment) or []

    if not entry_file or not source_markers or not target_markers or len(source_markers) != len(target_markers):
        raise ValueError('Automatic environment switching is not fully configured')

    path = workspace_path / entry_file
    content = path.read_text().splitlines()
    updated_lines = []
    for line in content:
        stripped = line.lstrip()
        if stripped.startswith('//'):
            updated_lines.append(line)
            continue
        updated = line
        for source, target in zip(source_markers, target_markers):
            updated = updated.replace(source, target)
        updated_lines.append(updated)

    path.write_text('\n'.join(updated_lines) + '\n')
    runtime_rules['currentEnvironment'] = preferred_environment
    runtime_rules['switchRequired'] = False
    runtime_rules['switchPerformed'] = True
    return runtime_rules
