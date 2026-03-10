# Feishu Webhook Reply Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a real local Feishu webhook server that receives DM events, routes qualifying ZenTao messages into the existing trigger flow, and replies back to the originating Feishu message.

**Architecture:** Keep `scripts/feishu_trigger.py` and `scripts/feishu_inbound.py` as pure task-routing layers. Add `scripts/feishu_api.py` for token + reply HTTP calls and `scripts/feishu_webhook_server.py` for the HTTP endpoint and orchestration. Use Python stdlib only so the repo stays dependency-light and easy to run locally.

**Tech Stack:** Python 3 stdlib, `unittest`, `urllib.request`, `http.server`, existing scripts in `scripts/`.

### Task 1: Add webhook orchestration tests

**Files:**
- Create: `tests/test_feishu_webhook_server.py`
- Reference: `scripts/feishu_inbound.py`
- Reference: `scripts/feishu_trigger.py`

**Step 1: Write the failing tests**

Add tests for:
- URL verification payload returns `{"challenge": ...}` and does not call the reply client
- A qualifying DM text event replies to the original `message_id` with `responseMessage`
- A non-trigger DM event is ignored and does not send a reply

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_feishu_webhook_server.py -v`
Expected: FAIL because `scripts.feishu_webhook_server` does not exist yet.

**Step 3: Write minimal implementation**

Create `scripts/feishu_webhook_server.py` with:
- `process_feishu_webhook(payload, base_dir, reply_client, verification_token=None)`
- structured result for `challenge`, `ignored`, and `triggered`
- reply side effect only for `triggered`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_feishu_webhook_server.py -v`
Expected: PASS

### Task 2: Add Feishu API request-building tests

**Files:**
- Create: `tests/test_feishu_api.py`
- Create: `scripts/feishu_api.py`

**Step 1: Write the failing tests**

Add tests for:
- `load_feishu_config_from_env()` reads `FEISHU_APP_ID` and `FEISHU_APP_SECRET`
- `build_reply_message_request()` builds the expected URL, method, headers, and JSON body
- `build_tenant_access_token_request()` builds the auth request payload

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_feishu_api.py -v`
Expected: FAIL because the module/functions do not exist yet.

**Step 3: Write minimal implementation**

Create a small client that:
- loads config from env
- requests tenant access token
- sends a text reply to a Feishu message

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_feishu_api.py -v`
Expected: PASS

### Task 3: Add HTTP handler/CLI tests

**Files:**
- Modify: `tests/test_feishu_webhook_server.py`
- Modify: `scripts/feishu_webhook_server.py`

**Step 1: Write the failing tests**

Add tests for:
- invalid verification token returns HTTP 403 style result
- `main()` can start from CLI args/config without executing the server loop during unit test

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_feishu_webhook_server.py -v`
Expected: FAIL until CLI/server helpers exist.

**Step 3: Write minimal implementation**

Add:
- `--host`
- `--port`
- `--runs-dir`
- `--verify-token`

Wrap `HTTPServer` around a thin request handler that delegates to `process_feishu_webhook()`.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_feishu_webhook_server.py -v`
Expected: PASS

### Task 4: Regression verification

**Files:**
- Test: `tests/test_feishu_api.py`
- Test: `tests/test_feishu_webhook_server.py`
- Test: `tests/test_feishu_inbound.py`
- Test: `tests/test_feishu_manual_trigger.py`
- Test: `tests/test_bugfix_orchestrator.py`

**Step 1: Run focused regression suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_feishu_api.py \
  tests/test_feishu_webhook_server.py \
  tests/test_feishu_inbound.py \
  tests/test_feishu_manual_trigger.py \
  tests/test_bugfix_orchestrator.py -v
```

Expected: PASS

**Step 2: Run full suite**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: PASS
