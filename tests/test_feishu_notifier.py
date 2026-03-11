import unittest


class FeishuNotifierTests(unittest.TestCase):
    def test_builds_feishu_send_command(self):
        from scripts.feishu_notifier import build_feishu_send_command

        command = build_feishu_send_command(
            session_id='ou_123',
            message='任务处理完成',
        )

        self.assertEqual(
            command,
            [
                'openclaw',
                'message',
                'send',
                '--channel',
                'feishu',
                '--target',
                'ou_123',
                '--message',
                '任务处理完成',
            ],
        )

    def test_builds_feishu_send_command_with_dry_run(self):
        from scripts.feishu_notifier import build_feishu_send_command

        command = build_feishu_send_command(
            session_id='ou_123',
            message='任务处理完成',
            dry_run=True,
        )

        self.assertEqual(command[-1], '--dry-run')


if __name__ == '__main__':
    unittest.main()
