# Explicit Task Triage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a first-class triage step that evaluates whether an incoming bug task can be executed automatically, needs more information, or should be blocked and reported before entering the dispatcher.

**Architecture:** Introduce a `triage_task()` helper in the orchestrator that returns a structured decision: `run`, `awaiting_info`, or `blocked`. The trigger flow uses this decision before queueing or starting a run. Existing dispatcher notifications remain, but trigger-time blocked/awaiting cases will now be explicit, with reasons stored in state metadata and reflected in Feishu messages.

**Tech Stack:** Python 3, `unittest`, existing filesystem-backed state machine and Feishu bridge.

### Task 1: Add failing tests for triage decisions

**Files:**
- Modify: `tests/test_bugfix_orchestrator.py`
- Modify: `tests/test_feishu_manual_trigger.py`

**Step 1: Write the failing tests**

Add tests that verify:
- a matched task with valid repo path and test command triages to `run`
- a task without project match triages to `awaiting_info`
- a task whose repo path does not exist triages to `blocked`
- trigger flow reports the blocked reason instead of pretending the task started

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest \
  tests/test_bugfix_orchestrator.py \
  tests/test_feishu_manual_trigger.py -v
```

Expected: FAIL because there is no explicit triage helper or blocked reporting path yet.

**Step 3: Write minimal implementation**

Add `triage_task(task)` to `scripts/bugfix_orchestrator.py` and wire it into `scripts/feishu_trigger.py`.

**Step 4: Run test to verify it passes**

Run the same tests and expect PASS.

### Task 2: Add failing tests for triage user messages

**Files:**
- Modify: `tests/test_feishu_task_bridge.py`
- Modify: `scripts/feishu_task_bridge.py`

**Step 1: Write the failing tests**

Add tests that verify:
- blocked triage uses a dedicated message type
- the message includes the reason and does not claim work has started

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest tests/test_feishu_task_bridge.py -v
```

Expected: FAIL until the new bridge event exists.

**Step 3: Write minimal implementation**

Add a `task_blocked` event renderer to `scripts/feishu_task_bridge.py`.

**Step 4: Run test to verify it passes**

Run the same test file and expect PASS.

### Task 3: Add triage metadata persistence

**Files:**
- Modify: `scripts/bugfix_orchestrator.py`
- Modify: `tests/test_bugfix_orchestrator.py`

**Step 1: Write the failing test**

Add a test that verifies triage writes:
- `triageDecision`
- `triageReason` or `missingItems`

into state metadata for blocked/awaiting runs.

**Step 2: Run test to verify it fails**

Run the orchestrator tests and expect FAIL.

**Step 3: Write minimal implementation**

Persist triage metadata when the trigger chooses `awaiting_user` or `needs_human`.

**Step 4: Run test to verify it passes**

Run the orchestrator tests and expect PASS.

### Task 4: Regression verification

**Files:**
- Test: `tests/test_bugfix_orchestrator.py`
- Test: `tests/test_feishu_manual_trigger.py`
- Test: `tests/test_feishu_task_bridge.py`
- Test: `tests/test_task_dispatcher.py`

**Step 1: Run focused regression suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_bugfix_orchestrator.py \
  tests/test_feishu_manual_trigger.py \
  tests/test_feishu_task_bridge.py \
  tests/test_task_dispatcher.py -v
```

Expected: PASS

**Step 2: Run full suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: PASS
