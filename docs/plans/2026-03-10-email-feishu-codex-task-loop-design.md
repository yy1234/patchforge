# 阿里邮箱 + 飞书 + Codex 任务闭环设计

## 目标

V0 目标是跑通一个本地优先的最小任务闭环（当前先跳过邮箱）：

- 从飞书私聊手动贴禅道链接触发
- 映射到本地项目
- 在隔离 worktree 中交给 Codex 执行
- 缺信息时通过飞书私聊追问用户
- 由 Checker 复审并给出最终状态

## 当前 V0 组成

- `scripts/mail_intake.py`
  负责邮件标准化和任务对象生成
- `scripts/bugfix_orchestrator.py`
  负责 run 目录、状态机、恢复流和 checker preflight
- `scripts/codex_worker.py`
  负责 Codex 命令构造、结构化结果读取和 watchdog 分类
- `scripts/feishu_task_bridge.py`
  负责 Commander 发给飞书私聊的消息格式
- `scripts/run_mail_task_loop.py`
  负责 mailbox 配置加载、轮询入口和 dry-run（当前未接入）
- `scripts/zentao_intake.py`
  负责从飞书私聊文本中提取禅道链接并标准化任务
- `scripts/feishu_trigger.py`
  负责手动触发入口的任务创建与状态更新
- `skills/zentao-trigger/SKILL.md`
  飞书私聊触发规则与执行命令说明

## 必需环境变量（邮箱接入时）

真实邮箱接入前至少需要：

- `MAIL_HOST`
- `MAIL_PORT`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_FOLDER`，默认可用 `INBOX`

推荐的阿里企业邮箱配置：

- `MAIL_HOST=imap.qiye.aliyun.com`
- `MAIL_PORT=993`

## 飞书会话假设

V0 假设只有一个主交互通道：飞书私聊机器人。

前提：

- OpenClaw 的 Feishu 通道已经启用
- 机器人能稳定给你发私聊
- 用户回复中会带可关联的任务上下文
- Commander 以 `taskId + sessionId` 关联恢复中的任务

## 当前接线方式

当前真实接线优先复用已存在的 OpenClaw Feishu websocket 通道，不在这个仓库里重复实现 Feishu webhook 服务。

桥接链路是：

- OpenClaw gateway 的 `feishu` channel 接收私聊消息
- OpenClaw workspace skill `zentao-trigger` 识别禅道链接触发条件
- skill 进入本仓库目录后执行 `python3 -m scripts.feishu_trigger`
- 脚本输出 JSON，其中 `responseMessage` 作为会话内回复返回给用户

这样 Feishu 的收发仍然由现有 OpenClaw 集成负责，这个仓库只负责任务标准化、run 目录、状态流转和回复文案。

## 首次生产 rollout 限制

第一版只建议这样用：

- 单邮箱账号
- 单用户飞书私聊
- 单任务串行执行
- 单机本地运行
- 单次轮询，不做常驻 daemon
- 不接真实 Codex 自动提交
- 不自动发 PR / merge

## 风险边界

- 项目匹配仍然依赖本地 `project_registry`
- 邮件正文抽取当前只覆盖文本路径
- 飞书桥接当前只负责文案，不直接发消息
- IMAP runner 当前只提供 dry-run 和依赖注入入口

## 手动触发方式

飞书私聊触发时，用户贴入禅道链接，例如：

`禅道: https://zentao.example.com/bug-view-321.html`

触发后任务状态会进入 `awaiting_user`，待补齐 `项目名` 等必要信息。

## Dry Run 方式（邮箱通道）

```bash
cd /Users/yangyang/Documents/patchforge/email-feishu-codex-task-loop
python3 scripts/run_mail_task_loop.py --dry-run
```

期望结果：

- 不访问真实邮箱
- 生成一个 sample task
- 在 `runs/tasks/` 下写入任务 run 目录
