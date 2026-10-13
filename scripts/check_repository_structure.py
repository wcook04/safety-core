#!/usr/bin/env python3
"""Keep source roles explicit without traversing ignored runtime state."""
from pathlib import Path, PurePosixPath
import subprocess

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


if __name__ == '__main__':
    errors = check(candidates(ROOT))
    print('\n'.join(errors) if errors else 'Repository structure: OK')
    raise SystemExit(bool(errors))
