#!/usr/bin/env python3
"""Build map review fixtures from demo-repo, including a synthetic empty route.

No packages or browser are needed. Output stays in an explicitly selected folder.
The real demo remains unchanged. Open tests.html#route=tests or empty.html#route=unused.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import doctrine


def build(out: Path, refresh_sample: bool = False):
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='safety-map-example-') as raw:
        root = Path(raw) / 'demo-repo'
        shutil.copytree(ROOT / 'examples/demo-repo', root, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
        source = root / '.doctrine/doctrine.toml'
        original = source.read_text()
        for name in ('tests', 'empty', 'purposes'):
            source.write_text(original)
            if name == 'empty':
                with source.open('a') as file:
                    file.write('\n# Synthetic review fixture: this path intentionally has no files.\n'
                               '[[route]]\nid = "unused"\npaths = ["unused/**"]\nprinciples = ["P7", "P6"]\n'
                               'reminder = "Check the paths when a route matches no files."\non = ["edit"]\n')
            if name == 'purposes':
                skill = 'skills/repository-organization/SKILL.md'
                (root / skill).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / skill, root / skill)
                (root / 'field-notes/visits').mkdir(parents=True)
                (root / 'field-notes/visits/visit-01.md').write_text('# Instrument trial\nA dated observation with its context.\n')
                policy = {'schema': 'repository_layout@2', 'undeclared_directories': 'warn',
                          'root_files': [], 'required_files': [], 'content_routes': {},
                          'directories': {
                              'src': {'purpose': 'Application source'},
                              'tests': {'purpose': 'Behaviour checks'},
                              'field-notes': {'purpose': 'Instrument observations and supporting material'},
                              'field-notes/visits': {'purpose': 'Dated observations from individual visits'},
                              'future-samples': {'purpose': 'Planned samples; no visible files yet'}}}
                (root / 'docs').mkdir(exist_ok=True)
                (root / 'docs/repository_layout.json').write_text(json.dumps(policy, indent=2) + '\n')
                with source.open('a') as file:
                    file.write('\n[[route]]\nid = "field-notes"\npaths = ["field-notes/**"]\n'
                               'principles = ["P8"]\nreminder = "Keep observations with their evidence."\n'
                               'skills = [{ path = "' + skill + '", when = "Adding folders or generalising a local organisation lesson" }]\n')
            graph, _ = doctrine.build_graph(doctrine.open_repo(source))
            if name == 'purposes' and refresh_sample:
                (ROOT / 'examples/graph.sample.json').write_text(json.dumps(graph, indent=2) + '\n')
            (out / (name + '.json')).write_text(json.dumps(graph, indent=2) + '\n')
            html = doctrine.inject((ROOT / 'viewer/map.html').read_text(), graph)
            (out / (name + '.html')).write_text(html)
            (out / (name + '-light.html')).write_text(html.replace('<html lang="en">', '<html lang="en" data-theme="light">'))
            (out / (name + '-dark.html')).write_text(html.replace('@media (prefers-color-scheme: dark)', '@media all'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--refresh-sample', action='store_true', help='Regenerate the viewer fallback from the purpose fixture.')
    args = p.parse_args()
    build(args.out.resolve(), args.refresh_sample)
