from typing import List, Optional


def render_commander_message(
    event: str,
    task: dict,
    state: dict,
    missing_items: Optional[List[str]] = None,
    note: Optional[str] = None,
) -> str:
    task_id = task['id']
    title = task['title']
    repo = task.get('repoCandidate') or '未识别'
    status = state['status']

    if event == 'task_started':
        message = (
            f'开始处理任务\n'
            f'任务ID：{task_id}\n'
            f'标题：{title}\n'
            f'项目：{repo}\n'
            f'当前阶段：{status}'
        )
        if note:
            message += f'\n说明：{note}'
        return message

    if event == 'awaiting_info':
        fields = '、'.join(missing_items or [])
        return (
            f'需要你补充信息\n'
            f'任务ID：{task_id}\n'
            f'标题：{title}\n'
            f'缺失项：{fields}\n'
            f'当前阶段：{status}'
        )

    if event == 'task_queued':
        return (
            f'任务已进入队列\n'
            f'任务ID：{task_id}\n'
            f'标题：{title}\n'
            f'项目：{repo}\n'
            f'当前阶段：{status}\n'
            f'说明：{note or "等待空闲槽位"}'
        )

    if event == 'task_retrying':
        return (
            f'任务需要重试\n'
            f'任务ID：{task_id}\n'
            f'标题：{title}\n'
            f'项目：{repo}\n'
            f'当前阶段：{status}\n'
            f'说明：{note or "等待下一次处理"}'
        )

    if event == 'task_blocked':
        return (
            f'当前无法自动处理\n'
            f'任务ID：{task_id}\n'
            f'标题：{title}\n'
            f'项目：{repo}\n'
            f'当前阶段：{status}\n'
            f'原因：{note or "待补充"}'
        )

    if event == 'blocked_backend':
        return (
            f'需要后端联调\n'
            f'任务ID：{task_id}\n'
            f'标题：{title}\n'
            f'项目：{repo}\n'
            f'原因：{note or "待补充"}'
        )

    if event == 'task_completed':
        return (
            f'任务处理完成\n'
            f'任务ID：{task_id}\n'
            f'标题：{title}\n'
            f'项目：{repo}\n'
            f'结果：{note or "无补充说明"}'
        )

    raise ValueError(f'Unsupported commander event: {event}')


def reply_matches_task(reply: dict, task_id: str, session_id: Optional[str]) -> bool:
    return reply.get('taskId') == task_id and reply.get('sessionId') == session_id
