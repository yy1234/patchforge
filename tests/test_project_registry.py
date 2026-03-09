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


if __name__ == '__main__':
    unittest.main()
