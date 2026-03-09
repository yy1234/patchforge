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


if __name__ == '__main__':
    unittest.main()
