import unittest


class MailTaskNormalizationTests(unittest.TestCase):
    def test_normalizes_mail_into_task_payload(self):
        from scripts.mail_intake import normalize_mail_task

        registry = [
            {
                'id': 'sample-app',
                'repoPath': '/repos/sample-app',
                'testCommand': 'pytest -q',
                'keywords': ['sample app', 'white screen'],
            }
        ]
        message = {
            'messageId': '<abc123@example.com>',
            'subject': 'Fix white screen in sample app',
            'from': 'pm@example.com',
            'bodyText': 'The login page shows a white screen after release.',
        }

        task = normalize_mail_task(message, registry)

        self.assertTrue(task['id'].startswith('mail-task-'))
        self.assertEqual(task['mailMessageId'], '<abc123@example.com>')
        self.assertEqual(task['title'], 'Fix white screen in sample app')
        self.assertEqual(task['taskType'], 'bugfix')
        self.assertEqual(task['repoCandidate'], 'sample-app')
        self.assertFalse(task['needsUserInput'])

    def test_marks_task_for_user_input_when_project_is_unknown(self):
        from scripts.mail_intake import normalize_mail_task

        task = normalize_mail_task(
            {
                'messageId': '<unknown@example.com>',
                'subject': 'Please investigate',
                'from': 'pm@example.com',
                'bodyText': 'There is a problem but the project is not clear.',
            },
            [],
        )

        self.assertIsNone(task['repoCandidate'])
        self.assertTrue(task['needsUserInput'])


if __name__ == '__main__':
    unittest.main()
