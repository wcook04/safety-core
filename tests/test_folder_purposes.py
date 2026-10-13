"""Custom folders: policy metadata, routed skills, delivery and live refresh."""
import json
import tomllib
from types import SimpleNamespace

from doctrine_testkit import MINI, RepoTestCase, doctrine
import hooks

SKILL = 'skills/local-notes/SKILL.md'
ROUTE = '''
[[route]]
id = "notes"
paths = ["field-notes/**"]
principles = []
reminder = "Keep observations with their context."
skills = [{ path = "skills/local-notes/SKILL.md", when = "Recording a visit" }]
'''


class FolderPurposes(RepoTestCase):
    def fixture(self):
        policy = {'schema': 'repository_layout@2', 'directories': {
            'field-notes': {'purpose': 'Instrument observations'},
            'field-notes/visits/deep': {'purpose': 'Detailed visits', 'guide': 'field-notes/README.md'},
            'future': {'purpose': 'Planned samples'}}}
        return self.make_repo({'docs/repository_layout.json': json.dumps(policy),
                              'field-notes/README.md': '# Notes',
                              'field-notes/visits/deep/a.md': 'visit',
                              'custom/data.csv': '1,2', SKILL: '# Record a visit\nKeep the date.'},
                             doctrine_text=MINI + ROUTE, git=True)

    def graph(self, root):
        repo = doctrine.open_repo(self.doctrine_path(root))
        graph, _ = doctrine.build_graph(repo)
        return repo, graph, {n['id']: n for n in graph['nodes']}

    def test_declared_observed_nested_and_undeclared_places(self):
        _, graph, nodes = self.graph(self.fixture())
        deep = nodes['place:field-notes/visits/deep']
        self.assertEqual(deep['purpose'], 'Detailed visits')
        self.assertEqual(deep['guide'], 'field-notes/README.md')
        self.assertEqual(nodes['place:field-notes/visits']['purpose'], 'Instrument observations')
        self.assertIsNone(nodes['place:custom']['purpose'])
        self.assertEqual(nodes['place:future']['observation'], 'declared_only')
        self.assertEqual(nodes['place:future']['files'], 0)
        self.assertFalse(any(e['kind'] == 'governs' and e['to'] == 'place:future' for e in graph['edges']))
        ref = nodes['route:notes']['skills'][0]
        self.assertEqual(ref['status'], 'present')
        self.assertIn('Keep the date.', ref['text'])

    def test_skill_only_route_does_not_increase_enforcement(self):
        root = self.fixture()
        _, before, _ = self.graph(root)
        source = self.doctrine_path(root)
        source.write_text(source.read_text().replace(ROUTE, ''))
        _, after, _ = self.graph(root)
        self.assertEqual(before['coverage']['enforced_beyond_words'], after['coverage']['enforced_beyond_words'])
        self.assertEqual(before['coverage']['by_level'], after['coverage']['by_level'])

    def test_explain_projection_and_hook_deliver_the_same_reference(self):
        root = self.fixture()
        repo, _, _ = self.graph(root)
        code, text, err = self.run_cli(root, 'explain', 'field-notes/visits/deep/a.md')
        self.assertEqual(code, 0, err)
        self.assertIn('Detailed visits', text)
        self.assertIn(SKILL, text)
        generated = doctrine.outputs(repo)['.claude/rules/doctrine-notes.md'][1]
        self.assertIn(SKILL, generated)
        self.assertIn('Recording a visit', generated)
        ctx = SimpleNamespace(doctrine=repo.doctrine, path=self.doctrine_path(root), rel=lambda p: str(p))
        delivered = hooks._route_text(ctx, repo.doctrine.routes['notes'], 'field-notes/visit.md')
        self.assertIn(SKILL, delivered)
        self.assertIn('guidance, not execution', delivered)

    def test_missing_skill_is_an_error_and_external_symlink_is_not_read(self):
        root = self.fixture()
        target = root / SKILL
        target.unlink()
        outside = root.parent / (root.name + '-external.md')
        outside.write_text('outside sentinel')
        self.addCleanup(outside.unlink)
        target.symlink_to(outside)
        _, graph, nodes = self.graph(root)
        self.assertTrue(any(g['kind'] == 'missing_skill' for g in graph['gaps']))
        self.assertIsNone(nodes['route:notes']['skills'][0]['text'])
        self.assertNotIn('outside sentinel', json.dumps(graph))
        self.assertEqual(self.run_cli(root, 'check')[0], 1)

    def test_live_signature_tracks_policy_and_skill_edits(self):
        root = self.fixture()
        live = doctrine.Live(self.doctrine_path(root))
        before = live.signature()
        policy = root / 'docs/repository_layout.json'
        policy.write_text(policy.read_text().replace('Instrument observations', 'Instrument measurements'))
        self.assertNotEqual(before, live.signature())
        live.rebuild()
        self.assertIn('Instrument measurements', live.body.decode())
        before = live.signature()
        (root / SKILL).write_text('# A revised workflow with context')
        self.assertNotEqual(before, live.signature())
        live.rebuild()
        self.assertIn('A revised workflow', live.body.decode())

    def test_optional_policy_and_explicit_policy_path(self):
        root = self.make_repo({'custom/a.md': ''})
        repo, _, _ = self.graph(root)
        self.assertEqual(doctrine.layout_roles(repo), ('', {}))
        source = self.doctrine_path(root)
        source.write_text(source.read_text().replace('[doctrine]', '[doctrine]\nlayout_policy = "docs/custom.json"'))
        self.assertEqual(self.run_cli(root, 'check')[0], 2)
        (root / 'docs').mkdir()
        (root / 'docs/custom.json').write_text(json.dumps({'schema': 'repository_layout@2', 'directories': {}}))
        self.assertEqual(doctrine.layout_roles(doctrine.open_repo(source)), ('docs/custom.json', {}))

    def test_bad_skill_references_and_policy_paths_are_rejected(self):
        for path in ('../escape/SKILL.md', 'https://example.org/SKILL.md', '/tmp/SKILL.md'):
            with self.subTest(path=path), self.assertRaises(doctrine.DoctrineError):
                doctrine.from_dict(tomllib.loads(MINI + ROUTE.replace(SKILL, path)))
        root = self.fixture()
        policy = root / 'docs/repository_layout.json'
        policy.write_text('{"schema":"repository_layout@2","directories":{"../escape":{"purpose":"No"}}}')
        self.assertEqual(self.run_cli(root, 'check')[0], 2)

    def test_init_trims_unavailable_skills_but_preserves_existing_ones(self):
        text, _, _ = doctrine.trim_routes(MINI + ROUTE, ['field-notes/a.md'])
        self.assertEqual(doctrine.from_dict(tomllib.loads(text)).routes['notes'].skills, ())
        multiline = (MINI + ROUTE).replace('skills = [{', 'skills = [\n{').replace('visit" }]', 'visit" }\n]')
        text, _, _ = doctrine.trim_routes(multiline, ['field-notes/a.md', SKILL])
        self.assertEqual(doctrine.from_dict(tomllib.loads(text)).routes['notes'].skills[0].path, SKILL)
