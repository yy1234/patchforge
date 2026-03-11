# Dispatcher Feishu Notification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Send a Feishu DM update back to the originating session when the dispatcher finishes a task cycle with a meaningful outcome.

**Architecture:** Add a small notifier wrapper around `openclaw message send --channel feishu`. The dispatcher will not notify on transient internal states like `running_coder`; it will notify only on cycle results such as `done`, `coder_retrying`, `review_retry`, and `needs_human`. Messages will be rendered via the existing `feishu_task_bridge.py` so the user-facing copy stays consistent.

**Tech Stack:** Python 3, `unittest`, `subprocess`, OpenClaw CLI, existing Feishu bridge.

### Task 1: Add failing tests for notifier command building

**Files:**
- Create: `tests/test_feishu_notifier.py`
- Create: `scripts/feishu_notifier.py`

**Step 1: Write the failing tests**

Add tests that verify:
- a Feishu message send command is built with `openclaw message send --channel feishu`
- the target is the stored `sessionId`
- `--dry-run` is supported for smoke tests

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_feishu_notifier.py -v`
Expected: FAIL because the notifier module does not exist yet.

**Step 3: Write minimal implementation**

Create `scripts/feishu_notifier.py` with:
- `build_feishu_send_command(...)`
- `send_feishu_message(...)`

**Step 4: Run test to verify it passes**

Run the same test file and expect PASS.

### Task 2: Add failing tests for dispatcher notifications

**Files:**
- Modify: `tests/test_task_dispatcher.py`
- Modify: `tests/test_feishu_task_bridge.py`

**Step 1: Write the failing tests**

Add tests that verify:
- `dispatch_once()` calls notifier on `done`
- `dispatch_once()` calls notifier on `review_retry`
- `dispatch_once()` does not notify when there is nothing to dispatch
- bridge renders a retry/failure-oriented message for dispatcher outcomes

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest \
  tests/test_task_dispatcher.py \
  tests/test_feishu_task_bridge.py -v
```

Expected: FAIL until the dispatcher can notify.

**Step 3: Write minimal implementation**

Update:
- `scripts/feishu_task_bridge.py`
- `scripts/task_dispatcher.py`

Add:
- dispatcher result message rendering
- notifier callback wiring in `dispatch_once()` and `main()`

**Step 4: Run test to verify it passes**

Run the same focused tests and expect PASS.

### Task 3: Add CLI dry-run smoke path

**Files:**
- Modify: `scripts/task_dispatcher.py`
- Modify: `scripts/feishu_notifier.py`

**Step 1: Write the failing test**

Add a test that verifies:
- `python3 -m scripts.task_dispatcher --simulate-success --notify-dry-run`
  triggers the notifier in dry-run mode

**Step 2: Run test to verify it fails**

Run the dispatcher tests and expect FAIL.

**Step 3: Write minimal implementation**

Add:
- `--notify`
- `--notify-dry-run`

**Step 4: Run test to verify it passes**

Run the dispatcher tests and expect PASS.

### Task 4: Regression verification

**Files:**
- Test: `tests/test_feishu_notifier.py`
- Test: `tests/test_task_dispatcher.py`
- Test: `tests/test_feishu_task_bridge.py`

**Step 1: Run focused regression suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_feishu_notifier.py \
  tests/test_task_dispatcher.py \
  tests/test_feishu_task_bridge.py -v
```

Expected: PASS

**Step 2: Run full suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: PASS
