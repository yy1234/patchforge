# Project Registry Schema Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the task-loop scripts consume the new `data/project_registry.json` schema and let Feishu/manual ZenTao triggers auto-match projects when the incoming text contains an app name, alias, or keyword.

**Architecture:** Keep the rest of the task-loop code working against a normalized registry entry shape. Extend `load_project_registry()` so it can read both the old list schema and the new `{version, roots, projects}` schema, filtering to matchable app entries and synthesizing legacy fields like `repoPath` and `testCommand` from the richer schema. Then reuse the normalized registry in `zentao_intake.py` and `feishu_trigger.py`.

**Tech Stack:** Python 3, `unittest`, JSON config files, existing scripts in `scripts/`.

### Task 1: Add failing tests for new registry schema loading

**Files:**
- Modify: `tests/test_project_registry.py`
- Reference: `scripts/bugfix_orchestrator.py`

**Step 1: Write the failing test**

Add a test that writes the new object schema:
- `version`
- `roots`
- `projects`

The test should verify:
- only `role="app"` and `matchEnabled=true` entries are loaded
- `rootPath` is normalized into `repoPath`
- `commands.test` is normalized into `testCommand`
- `keywords` include useful match tokens from `name` / `aliases`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_project_registry.py -v`
Expected: FAIL because `load_project_registry()` currently only accepts a top-level list.

**Step 3: Write minimal implementation**

Update `scripts/bugfix_orchestrator.py` so `load_project_registry()` accepts both schemas and emits the normalized list shape expected by current code.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_project_registry.py -v`
Expected: PASS

### Task 2: Add failing test for Feishu trigger project auto-match

**Files:**
- Modify: `tests/test_feishu_manual_trigger.py`
- Modify: `tests/test_zentao_intake.py`
- Reference: `scripts/feishu_trigger.py`
- Reference: `scripts/zentao_intake.py`

**Step 1: Write the failing tests**

Add tests that verify:
- `normalize_zentao_task(text, registry)` fills `repoCandidate`, `repoPath`, and `testCommand` when the text contains a project alias
- `handle_feishu_trigger()` moves straight to `task_started` instead of `awaiting_user` when the project matches

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m unittest \
  tests/test_zentao_intake.py \
  tests/test_feishu_manual_trigger.py -v
```

Expected: FAIL because `normalize_zentao_task()` currently ignores the registry.

**Step 3: Write minimal implementation**

Update:
- `scripts/zentao_intake.py`
- `scripts/feishu_trigger.py`

So the trigger path uses the normalized registry to match the incoming text.

**Step 4: Run test to verify it passes**

Run the same focused tests and expect PASS.

### Task 3: Add CLI support for real registry file in Feishu trigger

**Files:**
- Modify: `scripts/feishu_trigger.py`

**Step 1: Write the failing behavior test**

Extend an existing trigger CLI test or add a small one-off test to verify:
- `--registry-path` is accepted
- if omitted, the script prefers `data/project_registry.json` when present

**Step 2: Run test to verify it fails**

Run the focused trigger test and expect FAIL.

**Step 3: Write minimal implementation**

Add:
- `DEFAULT_REGISTRY_PATH`
- `--registry-path`
- `load_project_registry()` call in `main()`

**Step 4: Run test to verify it passes**

Run the trigger tests and expect PASS.

### Task 4: Regression verification

**Files:**
- Test: `tests/test_project_registry.py`
- Test: `tests/test_zentao_intake.py`
- Test: `tests/test_feishu_manual_trigger.py`
- Test: `tests/test_run_mail_task_loop.py`
- Test: `tests/test_feishu_inbound.py`

**Step 1: Run focused regression suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_project_registry.py \
  tests/test_zentao_intake.py \
  tests/test_feishu_manual_trigger.py \
  tests/test_run_mail_task_loop.py \
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
