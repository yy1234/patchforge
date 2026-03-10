---
name: zentao-trigger
description: Detect ZenTao links in Feishu DM and trigger the local task loop runner.
---

# Zentao Trigger (Feishu DM)

Use this when a Feishu DM message contains a ZenTao link or starts with `禅道:`.

## Trigger Rule

If the incoming message includes:
- `禅道:` or
- a URL that looks like a ZenTao bug/task link

then run the local trigger script and reply with its response.

## Command

Use the sender id as `session-id` when available; if not, use any stable per-user id.

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop && \
python3 -m scripts.feishu_trigger --text "<original message>" --session-id "<sender_id>"
```

The script prints JSON with `responseMessage`. Reply with that text verbatim.

## Output Example

```
{
  "runDir": "...",
  "taskId": "zentao-task-abcdef123456",
  "responseMessage": "需要你补充信息..."
}
```
