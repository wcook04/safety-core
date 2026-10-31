#!/usr/bin/env python3
"""Keep source roles explicit without traversing ignored runtime state."""
from pathlib import Path, PurePosixPath
import json
import posixpath
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    'Makefile','.gitignore', 'AGENTS.md', 'CLAUDE.md', 'CONTRIBUTING.md', 'LICENSE',
              'README.md', 'SECURITY.md', 'doctrine.py', 'doctrine.toml', 'hooks.py', 'safety.py'}
REQUIRED = {'doctrine.py', 'safety.py', 'hooks.py', 'doctrine.toml', 'viewer/map.html',
            'docs/guides/agent-setup.md', 'docs/README.md'}
DOC_ROLES = {'guides', 'reference', 'maintainers', 'img'}


def candidates(root: Path) -> set[str]:
    raw = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=root)
    return set(raw.decode().split('\0')) - {''}


def check(paths: set[str]) -> list[str]:
    errors = [f'{p}: required source is missing' for p in sorted(REQUIRED - paths)]
    for name in sorted(paths):
        if name == 'skills/repository-organization/scripts/test_check_layout.py':
            continue  # Self-contained portable skill fixture runner, invoked by CI.

        p = PurePosixPath(name)
        if len(p.parts) == 1 and name not in ROOT_FILES:
            errors.append(f'{name}: root is for entry files, the rulebook and the small runtime core')
        if p.parts[0] == 'docs' and name != 'docs/README.md':
            if len(p.parts) < 3 or p.parts[1] not in DOC_ROLES:
                errors.append(f'{name}: documentation needs a guides, reference, maintainers or img owner')
            if p.suffix in {'.py', '.js', '.sh', '.html'}:
                errors.append(f'{name}: executable sources belong in scripts/ or viewer/')
        if p.name.startswith('test_') and p.suffix == '.py' and p.parts[0] not in {'tests', 'examples'}:
            errors.append(f'{name}: regression suites belong in tests/')
        if p.parts[0] == '.doctrine' and p.name != '.gitignore':
            errors.append(f'{name}: local runtime state must not be tracked')
    return errors


def check_doc_images(root: Path, paths: set[str]) -> list[str]:
    """Keep illustrative captures attached to current docs and capture records."""
    images = {p for p in paths if p.startswith('docs/img/')}
    referenced = set()
    for name in sorted(paths):
        if not name.endswith('.md') or (name != 'README.md' and not name.startswith('docs/')):
            continue
        text = (root / name).read_text()
        for match in re.finditer(r'(?:src|srcset|href)="([^"]+)"|\]\(([^)]+)\)', text):
            target = next(part for part in match.groups() if part)
            if target.startswith(('/', '#')) or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            path = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(target.split('#')[0])))
            if path.startswith('docs/img/'):
                referenced.add(path)
    manifest = 'docs/maintainers/map-captures.json'
    if manifest in paths:
        def capture_paths(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key.startswith('docs/img/'):
                        referenced.add(key)
                    capture_paths(child)
            elif isinstance(value, list):
                for child in value:
                    capture_paths(child)
        capture_paths(json.loads((root / manifest).read_text()))
    return ([p + ': documentation or capture record references a missing image' for p in sorted(referenced - images)]
            + [p + ': image has no documentation consumer or capture record' for p in sorted(images - referenced)])


if __name__ == '__main__':
    paths = candidates(ROOT)
    errors = check(paths) + check_doc_images(ROOT, paths)
    print('\n'.join(errors) if errors else 'Repository structure: OK')
    raise SystemExit(bool(errors))
