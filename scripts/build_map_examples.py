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


def build(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='safety-map-example-') as raw:
        root = Path(raw) / 'demo-repo'
        shutil.copytree(ROOT / 'examples/demo-repo', root, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
        source = root / '.doctrine/doctrine.toml'
        for name in ('tests', 'empty'):
            if name == 'empty':
                with source.open('a') as file:
                    file.write('\n# Synthetic review fixture: this path intentionally has no files.\n'
                               '[[route]]\nid = "unused"\npaths = ["unused/**"]\nprinciples = ["P7", "P6"]\n'
                               'reminder = "Check the paths when a route matches no files."\non = ["edit"]\n')
            graph, _ = doctrine.build_graph(doctrine.open_repo(source))
            (out / (name + '.json')).write_text(json.dumps(graph, indent=2) + '\n')
            html = doctrine.inject((ROOT / 'viewer/map.html').read_text(), graph)
            (out / (name + '.html')).write_text(html)
            (out / (name + '-light.html')).write_text(html.replace('<html lang="en">', '<html lang="en" data-theme="light">'))
            (out / (name + '-dark.html')).write_text(html.replace('@media (prefers-color-scheme: dark)', '@media all'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    build(p.parse_args().out.resolve())
