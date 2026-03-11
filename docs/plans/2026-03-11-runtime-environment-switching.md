# Runtime Environment Switching Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically switch matched projects from production to test environment inside the isolated workspace before the worker runs, when local runtime rules require it.

**Architecture:** Keep source repositories untouched. After the dispatcher prepares the isolated workspace, apply local runtime-rule-based replacements only inside the workspace copy/worktree. The switcher should update task runtime metadata so the worker prompt and downstream notifications reflect the final environment used.

**Tech Stack:** Python 3, `unittest`, filesystem text replacement, existing `local_runtime_rules.py` and `task_dispatcher.py`.

### Task 1: Add failing tests for workspace environment switching

**Files:**
- Modify: `tests/test_local_runtime_rules.py`
- Modify: `scripts/local_runtime_rules.py`

**Step 1: Write the failing tests**

Add tests that verify:
- a workspace file on `prod` is rewritten to `test`
- commented lines remain commented
- the returned runtime metadata says `switchPerformed=true` and `currentEnvironment=test`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_local_runtime_rules.py -v`
Expected: FAIL because no switcher helper exists yet.

**Step 3: Write minimal implementation**

Add a helper like:
- `apply_runtime_rules_to_workspace(task, workspace_path)`

It should:
- inspect the workspace entry file
- replace active prod markers with matching test markers
- return updated runtime metadata

**Step 4: Run test to verify it passes**

Run the same test file and expect PASS.

### Task 2: Add failing tests for dispatcher integration

**Files:**
- Modify: `tests/test_task_dispatcher.py`
- Modify: `scripts/task_dispatcher.py`

**Step 1: Write the failing tests**

Add tests that verify:
- dispatcher applies the switch before worker execution
- updated runtime metadata is written back to `task.json`
- state metadata includes environment switching info

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_task_dispatcher.py -v`
Expected: FAIL because dispatcher does not call the switcher yet.

**Step 3: Write minimal implementation**

Update dispatcher to:
- call the switcher after workspace preparation
- persist updated task runtime metadata
- include switch info in state metadata

**Step 4: Run test to verify it passes**

Run the same test file and expect PASS.

### Task 3: Add fallback behavior when automatic switching is not configured

**Files:**
- Modify: `tests/test_task_dispatcher.py`
- Modify: `scripts/task_dispatcher.py`

**Step 1: Write the failing test**

Add a test that verifies:
- if `switchRequired=true` but replacement mapping is not usable
- dispatcher marks the run `needs_human`
- the reason explains that automatic environment switching is not configured

**Step 2: Run test to verify it fails**

Run the dispatcher tests and expect FAIL.

**Step 3: Write minimal implementation**

Catch switcher errors and convert them into a blocked/needs-human state before worker execution.

**Step 4: Run test to verify it passes**

Run the dispatcher tests and expect PASS.

### Task 4: Regression verification

**Files:**
- Test: `tests/test_local_runtime_rules.py`
- Test: `tests/test_task_dispatcher.py`
- Test: `tests/test_feishu_manual_trigger.py`

**Step 1: Run focused regression suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_local_runtime_rules.py \
  tests/test_task_dispatcher.py \
  tests/test_feishu_manual_trigger.py -v
```

Expected: PASS

**Step 2: Run full suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: PASS
