"""Placement rules cover source, staged changes and ignored local state."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_repository_structure as structure


class StructureTests(unittest.TestCase):
    def test_role_boundaries(self):
        accepted = structure.REQUIRED | structure.ROOT_FILES | {
            'docs/guides/adoption.md', 'docs/reference/graph-schema.md',
            'docs/maintainers/hooks.md', 'docs/img/map.png', 'tests/test_init.py',
            'scripts/check_repository_structure.py', '.doctrine/.gitignore',
            'examples/demo-repo/README.md', 'sources/anthropic-constitution/extract_clauses.py'}
        self.assertEqual(structure.check(accepted), [])
        for path in ('program.md', 'map.html', 'docs/ADOPTION.md', 'docs/guides/tool.py',
                     'scripts/test_init.py', '.doctrine/graph.json'):
            with self.subTest(path=path):
                self.assertTrue(any(e.startswith(path + ':') for e in structure.check(accepted | {path})))
        self.assertTrue(structure.check(accepted - {'viewer/map.html'}))

    def test_git_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL)
            git('init', '-q')
            (root / '.gitignore').write_text('.doctrine/graph.json\n')
            (root / 'program.md').write_text('')
            git('add', '.')
            git('-c', 'user.name=Structure Tests', '-c', 'user.email=tests@example.invalid', 'commit', '-qm', 'fixture')
            git('rm', 'program.md')
            (root / 'docs/guides').mkdir(parents=True)
            (root / 'docs/guides/agent-setup.md').write_text('')
            git('add', 'docs/guides/agent-setup.md')
            (root / 'map.html').write_text('')
            (root / '.doctrine').mkdir()
            (root / '.doctrine/graph.json').write_text('{}')
            paths = structure.candidates(root)
            self.assertNotIn('program.md', paths)
            self.assertIn('docs/guides/agent-setup.md', paths)
            self.assertIn('map.html', paths)
            self.assertNotIn('.doctrine/graph.json', paths)
            git('add', '-f', '.doctrine/graph.json')
            self.assertTrue(any(e.startswith('.doctrine/graph.json:')
                                for e in structure.check(structure.candidates(root))))


if __name__ == '__main__':
    unittest.main()
