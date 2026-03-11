import unittest


class FeishuTaskBridgeTests(unittest.TestCase):
    def test_renders_task_started_message(self):
        from scripts.feishu_task_bridge import render_commander_message

        message = render_commander_message(
            event='task_started',
            task={
                'id': 'mail-task-001',
                'title': 'Fix white screen',
                'repoCandidate': 'sample-app',
            },
            state={'status': 'running_coder'},
        )

        self.assertIn('开始处理任务', message)
        self.assertIn('mail-task-001', message)
        self.assertIn('sample-app', message)

    def test_renders_task_started_message_with_note(self):
        from scripts.feishu_task_bridge import render_commander_message

        message = render_commander_message(
            event='task_started',
            task={
                'id': 'mail-task-001',
                'title': 'Fix white screen',
                'repoCandidate': 'sample-app',
            },
            state={'status': 'created'},
            note='检测到当前为生产环境，执行前将切到 test',
        )

        self.assertIn('开始处理任务', message)
        self.assertIn('检测到当前为生产环境，执行前将切到 test', message)

    def test_renders_missing_info_message(self):
        from scripts.feishu_task_bridge import render_commander_message

        message = render_commander_message(
            event='awaiting_info',
            task={
                'id': 'mail-task-001',
                'title': 'Fix white screen',
                'repoCandidate': None,
            },
            state={'status': 'awaiting_user'},
            missing_items=['项目名', '测试账号'],
        )

        self.assertIn('需要你补充信息', message)
        self.assertIn('项目名', message)
        self.assertIn('测试账号', message)

    def test_renders_blocked_backend_message(self):
        from scripts.feishu_task_bridge import render_commander_message

        message = render_commander_message(
            event='blocked_backend',
            task={
                'id': 'mail-task-001',
                'title': 'Order save failed',
                'repoCandidate': 'sample-app',
            },
            state={'status': 'blocked_backend'},
            note='接口 /api/order/save 返回 500',
        )

        self.assertIn('需要后端联调', message)
        self.assertIn('/api/order/save', message)

    def test_renders_completion_message(self):
        from scripts.feishu_task_bridge import render_commander_message

        message = render_commander_message(
            event='task_completed',
            task={
                'id': 'mail-task-001',
                'title': 'Fix white screen',
                'repoCandidate': 'sample-app',
            },
            state={'status': 'review_passed'},
            note='局部测试已通过',
        )

        self.assertIn('任务处理完成', message)
        self.assertIn('局部测试已通过', message)

    def test_renders_queue_message(self):
        from scripts.feishu_task_bridge import render_commander_message

        message = render_commander_message(
            event='task_queued',
            task={
                'id': 'mail-task-001',
                'title': 'Fix white screen',
                'repoCandidate': 'sample-app',
            },
            state={'status': 'queued'},
            note='前方还有 1 个任务',
        )

        self.assertIn('已进入队列', message)
        self.assertIn('前方还有 1 个任务', message)

    def test_renders_retry_message(self):
        from scripts.feishu_task_bridge import render_commander_message

        message = render_commander_message(
            event='task_retrying',
            task={
                'id': 'mail-task-001',
                'title': 'Fix white screen',
                'repoCandidate': 'sample-app',
            },
            state={'status': 'review_retry'},
            note='checker 未通过，准备重试',
        )

        self.assertIn('任务需要重试', message)
        self.assertIn('checker 未通过', message)

    def test_renders_blocked_message(self):
        from scripts.feishu_task_bridge import render_commander_message

        message = render_commander_message(
            event='task_blocked',
            task={
                'id': 'mail-task-001',
                'title': 'Fix white screen',
                'repoCandidate': 'sample-app',
            },
            state={'status': 'needs_human'},
            note='项目路径不存在：/missing/repo',
        )

        self.assertIn('当前无法自动处理', message)
        self.assertIn('项目路径不存在', message)


if __name__ == '__main__':
    unittest.main()
