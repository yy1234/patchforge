import unittest


class FakeImapClient:
    def __init__(self, messages):
        self._messages = messages

    def fetch_unseen_messages(self):
        return list(self._messages)


class MailTaskLoopTests(unittest.TestCase):
    def test_loads_mailbox_config_from_env(self):
        from scripts.run_mail_task_loop import load_mailbox_config

        config = load_mailbox_config(
            {
                'MAIL_HOST': 'imap.qiye.aliyun.com',
                'MAIL_PORT': '993',
                'MAIL_USERNAME': 'user@example.com',
                'MAIL_PASSWORD': 'secret',
                'MAIL_FOLDER': 'INBOX',
            }
        )

        self.assertEqual(config['host'], 'imap.qiye.aliyun.com')
        self.assertEqual(config['port'], 993)
        self.assertEqual(config['username'], 'user@example.com')
        self.assertEqual(config['folder'], 'INBOX')

    def test_fetches_unseen_messages_and_emits_tasks(self):
        from scripts.run_mail_task_loop import poll_mailbox_once

        emitted = []
        registry = [
            {
                'id': 'sample-app',
                'repoPath': '/repos/sample-app',
                'testCommand': 'pytest -q',
                'keywords': ['sample app', 'white screen'],
            }
        ]
        client = FakeImapClient(
            [
                {
                    'messageId': '<abc123@example.com>',
                    'subject': 'Fix white screen in sample app',
                    'from': 'pm@example.com',
                    'bodyText': 'The login page shows a white screen after release.',
                }
            ]
        )

        processed = poll_mailbox_once(client, registry, emitted.append)

        self.assertEqual(processed, 1)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]['mailMessageId'], '<abc123@example.com>')
        self.assertEqual(emitted[0]['repoCandidate'], 'sample-app')


if __name__ == '__main__':
    unittest.main()
