# Feishu Inbound Trigger Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a real Feishu inbound parsing layer that can accept a DM text event, reuse `scripts/feishu_trigger.py`, and emit a structured reply payload for the caller to send back to Feishu.

**Architecture:** Keep `scripts/feishu_trigger.py` as the task-creation core. Add a new `scripts/feishu_inbound.py` adapter that parses Feishu webhook payloads, extracts the sender id and message text, handles URL verification challenges, ignores unsupported events, and calls `handle_feishu_trigger()` for qualifying DM text messages.

**Tech Stack:** Python 3, `unittest`, JSON CLI scripts, existing task orchestration modules in `scripts/`.

### Task 1: Add inbound trigger routing test

**Files:**
- Create: `tests/test_feishu_inbound.py`
- Reference: `scripts/feishu_trigger.py`
- Reference: `skills/zentao-trigger/SKILL.md`

**Step 1: Write the failing test**

```python
def test_routes_p2p_text_message_into_feishu_trigger():
    payload = {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_123"}},
            "message": {
                "chat_type": "p2p",
                "message_type": "text",
                "message_id": "om_123",
                "content": "{\"text\": \"禅道: https://zentao.example.com/bug-view-321.html\"}",
            },
        },
    }
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_feishu_inbound.py -v`
Expected: FAIL because `scripts.feishu_inbound` does not exist yet.

**Step 3: Write minimal implementation**

Create `scripts/feishu_inbound.py` with:
- `extract_text_message(payload)` to parse event payload safely
- `handle_feishu_inbound(payload, base_dir, registry=None)` to:
  - return URL verification challenge unchanged
  - ignore non-`im.message.receive_v1`, non-`p2p`, or non-text events
  - call `handle_feishu_trigger(text=..., session_id=sender_open_id, ...)`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_feishu_inbound.py -v`
Expected: PASS

### Task 2: Add edge-case inbound coverage

**Files:**
- Modify: `tests/test_feishu_inbound.py`
- Modify: `scripts/feishu_inbound.py`

**Step 1: Write the failing tests**

Add tests for:
- URL verification payload returns `{"challenge": "..."}`
- group or non-text messages are ignored with a structured reason
- text messages without a ZenTao link are ignored cleanly

**Step 2: Run test to verify they fail**

Run: `python3 -m unittest tests/test_feishu_inbound.py -v`
Expected: FAIL until ignore and verification paths are implemented.

**Step 3: Write minimal implementation**

Implement only the missing branches needed by the tests.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_feishu_inbound.py -v`
Expected: PASS

### Task 3: Add CLI entrypoint verification

**Files:**
- Modify: `scripts/feishu_inbound.py`
- Modify: `tests/test_feishu_inbound.py`

**Step 1: Write the failing test**

Add a test for `main()` that passes a payload file path and verifies JSON output includes:
- `eventType`
- `sessionId`
- `responseMessage` when triggered

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_feishu_inbound.py -v`
Expected: FAIL because CLI parsing/output is not complete yet.

**Step 3: Write minimal implementation**

Add CLI options:
- `--payload-file`
- `--runs-dir`

Print a compact JSON result for the outer Feishu webhook layer.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_feishu_inbound.py -v`
Expected: PASS

### Task 4: Regression verification

**Files:**
- Test: `tests/test_feishu_inbound.py`
- Test: `tests/test_feishu_manual_trigger.py`
- Test: `tests/test_bugfix_orchestrator.py`

**Step 1: Run focused regression suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_feishu_inbound.py \
  tests/test_feishu_manual_trigger.py \
  tests/test_bugfix_orchestrator.py -v
```

Expected: PASS
