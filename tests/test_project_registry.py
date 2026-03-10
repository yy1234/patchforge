import json
import tempfile
import unittest
from pathlib import Path


class ProjectRegistryLoaderTests(unittest.TestCase):
    def test_loads_registry_and_matches_keywords(self):
        from scripts.bugfix_orchestrator import load_project_registry, match_project

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / 'project_registry.json'
            registry_path.write_text(json.dumps([
                {
                    'id': 'sample-app',
                    'repoPath': '/repos/sample-app',
                    'testCommand': 'pytest -q',
                    'keywords': ['sample app', 'sample-app', 'white screen'],
                }
            ]))

            registry = load_project_registry(registry_path)
            match = match_project('Fix white screen in sample app', 'The sample-app login page is blank.', registry)

            self.assertEqual(registry[0]['id'], 'sample-app')
            self.assertEqual(match['id'], 'sample-app')

    def test_loads_new_registry_schema_and_filters_matchable_apps(self):
        from scripts.bugfix_orchestrator import load_project_registry, match_project

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / 'project_registry.json'
            registry_path.write_text(json.dumps({
                'version': 1,
                'roots': [
                    {'id': 'apps', 'path': '/repos'}
                ],
                'projects': [
                    {
                        'id': 'sx-app',
                        'name': '绍兴环卫监管',
                        'aliases': ['igmis_sx', 'sx'],
                        'role': 'app',
                        'projectType': 'hybrid',
                        'matchEnabled': True,
                        'rootPath': '/repos/igmis_sx',
                        'keywords': ['绍兴', '监管'],
                        'commands': {'test': 'xcodebuild test'},
                    },
                    {
                        'id': 'common-lib',
                        'name': 'common',
                        'aliases': ['common'],
                        'role': 'package',
                        'projectType': 'flutter_package',
                        'matchEnabled': False,
                        'rootPath': '/repos/common',
                        'keywords': ['基础组件'],
                        'commands': {'test': 'flutter test'},
                    },
                ],
            }, ensure_ascii=False))

            registry = load_project_registry(registry_path)
            match = match_project(
                '修复 绍兴环卫监管 登录白屏',
                '用户反馈 igmis_sx 登录页白屏',
                registry,
            )

            self.assertEqual(len(registry), 1)
            self.assertEqual(registry[0]['id'], 'sx-app')
            self.assertEqual(registry[0]['repoPath'], '/repos/igmis_sx')
            self.assertEqual(registry[0]['testCommand'], 'xcodebuild test')
            self.assertIn('绍兴环卫监管', registry[0]['keywords'])
            self.assertIn('igmis_sx', registry[0]['keywords'])
            self.assertEqual(match['id'], 'sx-app')

    def test_rejects_entries_missing_required_fields(self):
        from scripts.bugfix_orchestrator import load_project_registry

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / 'project_registry.json'
            registry_path.write_text(json.dumps([
                {
                    'id': 'broken-app',
                    'keywords': ['broken'],
                }
            ]))

            with self.assertRaises(ValueError):
                load_project_registry(registry_path)

    def test_does_not_false_positive_on_short_ascii_alias_inside_url(self):
        from scripts.bugfix_orchestrator import match_project

        registry = [
            {
                'id': 'igmis-xa',
                'repoPath': '/repos/igmis_xa',
                'testCommand': 'xcodebuild test',
                'keywords': ['igmis_xa', 'xa'],
            },
            {
                'id': 'snmis-bjsg',
                'repoPath': '/repos/snmis_bjsg',
                'testCommand': 'flutter test',
                'keywords': ['snmis_bjsg', '北京首钢'],
            },
        ]

        match = match_project(
            '禅道: https://zentao.example.com/bug-view-321.html 北京首钢登录白屏',
            '禅道: https://zentao.example.com/bug-view-321.html 北京首钢登录白屏',
            registry,
        )

        self.assertEqual(match['id'], 'snmis-bjsg')


if __name__ == '__main__':
    unittest.main()
