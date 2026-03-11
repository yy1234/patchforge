import json
import tempfile
import unittest
from pathlib import Path


class LocalRuntimeRulesTests(unittest.TestCase):
    def test_enriches_task_with_runtime_rules_and_detects_active_environment(self):
        from scripts.local_runtime_rules import enrich_task_with_runtime_rules

        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / 'repo'
            app_dir = repo_dir / 'lib' / 'app'
            app_dir.mkdir(parents=True)
            (app_dir / 'app.dart').write_text(
                """
// static String baseUrl = 'http://10.1.120.241:9180/serverUia/';
static String baseUrl = 'http://192.168.100.72:10062/uia/';
"""
            )

            task = {
                'id': 'bugfix-001',
                'sourceTaskId': 'source-001',
                'repoCandidate': 'snmis_bjsg',
                'repoPath': str(repo_dir),
                'testCommand': 'flutter test',
                'bugDescription': 'Sample',
                'doneDefinition': ['tests pass'],
            }
            rules = {
                'projects': {
                    'snmis_bjsg': {
                        'entryFile': 'lib/app/app.dart',
                        'environment': {
                            'preferredForAutomation': 'test',
                            'activeProfileMarkers': {
                                'test': ['http://192.168.100.72:10062/uia/'],
                                'prod': ['http://10.1.120.241:9180/serverUia/'],
                            },
                            'autoSwitchRule': {
                                'ifCurrentProfile': 'prod',
                                'switchTo': 'test',
                            },
                        },
                        'credentials': {
                            'sourcePriority': ['remarks', 'local_default'],
                            'localDefault': {'username': 'root', 'password': '123456'},
                        },
                        'backendCollaboration': {
                            'requiredWhenBlocked': ['后端接口地址', '鉴权方式'],
                        },
                    }
                }
            }

            enriched = enrich_task_with_runtime_rules(task, rules)

            self.assertIn('runtimeRules', enriched)
            self.assertEqual(enriched['runtimeRules']['entryFile'], 'lib/app/app.dart')
            self.assertEqual(enriched['runtimeRules']['currentEnvironment'], 'test')
            self.assertFalse(enriched['runtimeRules']['switchRequired'])
            self.assertEqual(enriched['runtimeRules']['defaultUsername'], 'root')
            self.assertTrue(enriched['runtimeRules']['hasDefaultPassword'])
            self.assertIn('后端接口地址', enriched['runtimeRules']['backendRequiredWhenBlocked'])

    def test_loads_local_runtime_rules_from_file(self):
        from scripts.local_runtime_rules import load_local_runtime_rules

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'local_runtime_rules.json'
            path.write_text(json.dumps({'version': 1, 'projects': {'snmis_bjsg': {}}}))

            rules = load_local_runtime_rules(path)
            self.assertIn('snmis_bjsg', rules['projects'])


if __name__ == '__main__':
    unittest.main()
