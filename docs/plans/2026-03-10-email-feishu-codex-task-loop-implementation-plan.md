# Email Feishu Codex Task Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## 已完成范围

- Task 1: project registry loader and matcher
- Task 2: mail intake normalization
- Task 3: run directory state tracking
- Task 4: Feishu DM bridge formatter
- Task 5: Codex watchdog classification and retry policy
- Task 6: deterministic checker preflight
- Task 7: resume task after matching Feishu reply
- Task 8: IMAP loop runner with dry-run entry
- Task 10: manual Feishu trigger (ZenTao link intake)

## 验证命令

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 -m unittest \
  tests/test_bugfix_orchestrator.py \
  tests/test_codex_worker.py \
  tests/test_project_registry.py \
  tests/test_mail_intake.py \
  tests/test_feishu_task_bridge.py \
  tests/test_run_mail_task_loop.py -v
```

## 仍需接入的真实外部依赖

- 真实 IMAP client
- 真实 Feishu 发送与回复接收
- 真实 Commander 调度入口
- 真实 Codex CLI 执行包装

## 首次接线前检查项

- 企业邮箱 IMAP 已开通
- 账号密码或客户端专用密码可用
- 飞书私聊机器人已完成连通验证
- `project_registry` 已填入真实项目
- 本地仓库路径和测试命令已验证

## rollout 建议

1. 先只启用飞书私聊手动贴链接触发
2. 再接真实 Codex 和飞书回复恢复流
3. 邮箱接入放到后续阶段
