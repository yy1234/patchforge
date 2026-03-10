# OpenClaw Feishu Skill Bridge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reuse the already-working OpenClaw Feishu websocket integration by installing a `zentao-trigger` workspace skill that calls this repo's local trigger script when a Feishu DM contains a ZenTao link.

**Architecture:** Do not add a new Feishu webhook server in this repo. Keep the repo responsible only for task-loop logic (`scripts/feishu_trigger.py`). Bridge the existing OpenClaw main workspace to this repo by installing a workspace skill under `~/.openclaw/workspace/skills/zentao-trigger` whose command changes into the repo root and invokes the existing trigger script. Verify discovery with `openclaw skills list` and keep replies in-band through the existing Feishu session.

**Tech Stack:** OpenClaw workspace skills, Python 3 CLI scripts, existing Feishu websocket channel, `openclaw skills` CLI.

### Task 1: Verify the repo trigger command from the repo root

**Files:**
- Reference: `scripts/feishu_trigger.py`
- Reference: `skills/zentao-trigger/SKILL.md`

**Step 1: Run the trigger command manually**

Run:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m scripts.feishu_trigger \
  --text "禅道: https://zentao.example.com/bug-view-321.html" \
  --session-id "feishu-openclaw-test"
```

Expected: JSON output with `responseMessage`.

### Task 2: Install the OpenClaw workspace skill

**Files:**
- Create: `~/.openclaw/workspace/skills/zentao-trigger/SKILL.md`

**Step 1: Create the skill directory**

Create:

```bash
mkdir -p /Users/yangyang/.openclaw/workspace/skills/zentao-trigger
```

**Step 2: Write the workspace skill**

Write a `SKILL.md` that:
- describes the Feishu DM ZenTao trigger behavior
- runs:

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop && \
python3 -m scripts.feishu_trigger --text "<original message>" --session-id "<sender_id>"
```

- instructs OpenClaw to reply with `responseMessage` verbatim

**Step 3: Verify skill discovery**

Run:

```bash
openclaw skills list | rg zentao-trigger
```

Expected: `zentao-trigger` appears as an `openclaw-workspace` skill.

### Task 3: Smoke-verify the existing Feishu channel still looks healthy

**Files:**
- Reference: `~/.openclaw/openclaw.json`

**Step 1: Probe the channel**

Run:

```bash
openclaw channels status --probe
```

Expected: `Feishu main: enabled, configured, running, works`

### Task 4: Document the bridge in this repo

**Files:**
- Modify: `docs/plans/2026-03-10-email-feishu-codex-task-loop-design.md`

**Step 1: Add a short note**

Document that the first real Feishu integration path is:
- OpenClaw websocket Feishu channel
- workspace `zentao-trigger` skill
- local repo `scripts/feishu_trigger.py`

### Task 5: Final verification

**Files:**
- Reference: `~/.openclaw/workspace/skills/zentao-trigger/SKILL.md`

**Step 1: Verify local bridge shape**

Run:

```bash
openclaw skills list | rg zentao-trigger
openclaw channels status --probe
```

Expected: skill discovered and Feishu channel healthy.
