# Task Dispatcher Execution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local dispatcher that advances ready bug runs from `created/queued` through coder/checker states and writes real execution artifacts into each run directory.

**Architecture:** Keep Feishu trigger handling fast and non-blocking. Introduce a dispatcher module that scans `runs/tasks`, promotes queued runs when capacity is available, and processes ready runs one at a time through a synchronous execution cycle. The execution cycle should render a worker prompt, prepare a worktree path, invoke a worker runner abstraction, classify the outcome, run checker preflight, and update state accordingly.

**Tech Stack:** Python 3, `unittest`, `subprocess`, existing `codex_worker.py` helpers, filesystem-backed run state.

### Task 1: Add failing tests for worker prompt/rendered artifacts

**Files:**
- Modify: `tests/test_codex_worker.py`
- Reference: `scripts/codex_worker.py`

**Step 1: Write the failing tests**

Add tests that verify:
- `render_worker_prompt()` includes the run directory path
- a helper can write `prompt.md` for a run

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_codex_worker.py -v`
Expected: FAIL because the prompt does not include run-directory context and no prompt-writing helper exists.

**Step 3: Write minimal implementation**

Update `scripts/codex_worker.py` to:
- accept `run_dir` in prompt rendering or prompt file creation
- create `prompt.md` in the run directory

**Step 4: Run test to verify it passes**

Run the same test file and expect PASS.

### Task 2: Add failing tests for dispatcher state transitions

**Files:**
- Create: `tests/test_task_dispatcher.py`
- Create: `scripts/task_dispatcher.py`

**Step 1: Write the failing tests**

Add tests that verify:
- a `created` run moves to `running_coder`, then `running_checker`, then `done` when worker + checker succeed
- a retryable worker result leads to `coder_retrying`
- a failed checker preflight leads to `review_retry`
- a queued run is promoted before dispatch if capacity exists

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_task_dispatcher.py -v`
Expected: FAIL because the dispatcher module does not exist yet.

**Step 3: Write minimal implementation**

Create `scripts/task_dispatcher.py` with:
- `dispatch_once(base_dir, worker_runner=..., checker_runner=...)`
- helpers to find the next runnable run
- state updates using existing orchestrator helpers

**Step 4: Run test to verify it passes**

Run the dispatcher test file and expect PASS.

### Task 3: Add a real subprocess-backed worker runner

**Files:**
- Modify: `scripts/codex_worker.py`
- Modify: `scripts/task_dispatcher.py`

**Step 1: Write the failing test**

Add a narrow unit test for a subprocess-backed worker wrapper that:
- builds the codex command
- captures exit code
- inspects produced artifacts

**Step 2: Run test to verify it fails**

Run the relevant worker/dispatcher tests and expect FAIL.

**Step 3: Write minimal implementation**

Add a default worker runner that:
- writes `prompt.md`
- invokes `codex`
- returns a structure consumable by `classify_worker_run()`

**Step 4: Run test to verify it passes**

Run the focused tests and expect PASS.

### Task 4: Regression verification

**Files:**
- Test: `tests/test_task_dispatcher.py`
- Test: `tests/test_codex_worker.py`
- Test: `tests/test_bugfix_orchestrator.py`
- Test: `tests/test_feishu_manual_trigger.py`

**Step 1: Run focused regression suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_task_dispatcher.py \
  tests/test_codex_worker.py \
  tests/test_bugfix_orchestrator.py \
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
