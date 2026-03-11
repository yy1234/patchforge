# Active Run Queue Control Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reuse the same active run for the same ZenTao bug inside one Feishu session, while limiting ready-to-process runs to 3 and queueing overflow runs FIFO.

**Architecture:** Introduce a stable `sourceTaskId` per ZenTao link and a unique run `id` per created run. Add orchestrator helpers to find an active run by `sessionId + sourceTaskId`, count active ready runs, enqueue overflow runs, and promote the next queued run when capacity frees up. Keep tasks that still need user input in `awaiting_user` so they do not consume one of the 3 ready slots.

**Tech Stack:** Python 3, `unittest`, filesystem-backed run state in `runs/tasks`, existing trigger/orchestrator scripts.

### Task 1: Add failing tests for run identity and reuse

**Files:**
- Modify: `tests/test_zentao_intake.py`
- Modify: `tests/test_feishu_manual_trigger.py`

**Step 1: Write the failing tests**

Add tests that verify:
- the same ZenTao URL produces the same `sourceTaskId` but different run `id`s
- a second trigger for the same `sessionId + sourceTaskId` reuses the existing run directory
- follow-up text is appended to the existing `context.md`

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest \
  tests/test_zentao_intake.py \
  tests/test_feishu_manual_trigger.py -v
```

Expected: FAIL because there is no `sourceTaskId` or active-run reuse yet.

**Step 3: Write minimal implementation**

Update:
- `scripts/zentao_intake.py`
- `scripts/feishu_trigger.py`

So repeated messages for the same bug/session reuse the current active run.

**Step 4: Run test to verify it passes**

Run the same focused tests and expect PASS.

### Task 2: Add failing tests for queue capacity

**Files:**
- Modify: `tests/test_bugfix_orchestrator.py`
- Modify: `tests/test_feishu_task_bridge.py`

**Step 1: Write the failing tests**

Add tests that verify:
- the 4th ready run is marked `queued`
- queued state stores enough metadata to know it should resume as `created`
- the next queued run is promoted when capacity becomes available
- queue message rendering is supported

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest \
  tests/test_bugfix_orchestrator.py \
  tests/test_feishu_task_bridge.py -v
```

Expected: FAIL because queue-control helpers and message event do not exist yet.

**Step 3: Write minimal implementation**

Update `scripts/bugfix_orchestrator.py` and `scripts/feishu_task_bridge.py` with:
- active-state constants
- queue helper functions
- FIFO promotion helper
- queue response message

**Step 4: Run test to verify it passes**

Run the same focused tests and expect PASS.

### Task 3: Wire queue decisions into trigger flow

**Files:**
- Modify: `scripts/feishu_trigger.py`
- Modify: `tests/test_feishu_manual_trigger.py`

**Step 1: Write the failing test**

Add a test that creates 3 ready runs, then triggers a 4th distinct matched bug and verifies:
- a new run is created
- state is `queued`
- response message says the task entered the queue

**Step 2: Run test to verify it fails**

Run the trigger test file and expect FAIL.

**Step 3: Write minimal implementation**

Call the new queue-control helpers from `handle_feishu_trigger()`.

**Step 4: Run test to verify it passes**

Run the same trigger tests and expect PASS.

### Task 4: Regression verification

**Files:**
- Test: `tests/test_bugfix_orchestrator.py`
- Test: `tests/test_feishu_task_bridge.py`
- Test: `tests/test_feishu_manual_trigger.py`
- Test: `tests/test_zentao_intake.py`
- Test: `tests/test_feishu_inbound.py`

**Step 1: Run focused regression suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_bugfix_orchestrator.py \
  tests/test_feishu_task_bridge.py \
  tests/test_feishu_manual_trigger.py \
  tests/test_zentao_intake.py \
  tests/test_feishu_inbound.py -v
```

Expected: PASS

**Step 2: Run full suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: PASS
