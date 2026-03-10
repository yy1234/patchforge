import unittest


class ZentaoIntakeTests(unittest.TestCase):
    def test_extracts_first_url(self):
        from scripts.zentao_intake import extract_zentao_link

        text = "帮我看下这个缺陷 https://zentao.example.com/bug-view-123.html 谢谢"
        self.assertEqual(extract_zentao_link(text), "https://zentao.example.com/bug-view-123.html")

    def test_normalizes_task_from_message(self):
        from scripts.zentao_intake import normalize_zentao_task

        task = normalize_zentao_task(
            "禅道: https://zentao.example.com/bug-view-321.html"
        )

        self.assertTrue(task["id"].startswith("zentao-task-"))
        self.assertEqual(task["zentaoUrl"], "https://zentao.example.com/bug-view-321.html")
        self.assertEqual(task["source"], "feishu")
        self.assertTrue(task["needsUserInput"])


if __name__ == "__main__":
    unittest.main()
