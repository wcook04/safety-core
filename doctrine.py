#!/usr/bin/env python3
"""doctrine.py: one doctrine for the AI agents in a repository, compiled, checked and mapped.

Write the doctrine once in doctrine.toml: up to seven axioms, principles paired with
anti-principles, routes that attach principles to paths, and the published sources each
claim rests on. This file turns it into what agents read (a managed region in AGENTS.md,
which CLAUDE.md imports, and path-scoped rules in .claude/rules/), checks that every rule
is linked and enforced or honestly marked as words, and draws the result as a map.

    python3 doctrine.py init [--target DIR]           adopt the reference doctrine
    python3 doctrine.py build [--export rulesync]     write the projections and the graph
    python3 doctrine.py check [--json]                links, drift and coverage; exit 1 on errors
    python3 doctrine.py explain PATH                  what an agent receives at PATH
    python3 doctrine.py map [--out FILE]              one self-contained HTML file
    python3 doctrine.py map --serve [--port N] [--open]   a live map that redraws as you edit
    python3 doctrine.py log-error "WHAT" --principle P9 --lesson "RULE"

Standard library only, Python 3.11 or later. The hooks live in hooks.py and the viewer in
viewer/map.html in the source checkout (map.html beside this file after adoption).
"""

from __future__ import annotations

import argparse, ast, datetime, functools, hashlib, http.server, json, os, re
import shlex, shutil, subprocess, sys, textwrap, threading, time, tomllib, webbrowser
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable

HERE = Path(__file__).resolve().parent


# =========================================================================== 1. the doctrine model

LEVELS = ("block", "ask", "check", "remind", "advise", "prose")
"""Enforcement levels, strongest first."""

LEVEL_RANK = {level: rank for rank, level in enumerate(LEVELS)}
TRIGGERS = ("read", "edit", "shell")
QUOTE_POLICIES = ("quote", "cite")
TIERS = {"block": "enforced", "ask": "enforced", "check": "enforced",
         "remind": "reminded", "advise": "reminded", "prose": "words"}
"""How a level holds at a place: something stops or fails it, text reaches the agent, or words only."""

class DoctrineError(ValueError):
    """The doctrine file is malformed. `problems` lists every issue found."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems

class UsageError(Exception):
    """A command cannot run as asked; the message says why and what to do."""

@dataclass(frozen=True)
class SourceRef:
    ref: str
    at: str = ""
    quote: str = ""

@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    publisher: str = ""
    date: str = ""
    licence: str = ""
    quote_policy: str = "cite"

@dataclass(frozen=True)
class Axiom:
    id: str
    name: str
    clause: str
    plain: str
    anti: str
    sources: tuple[SourceRef, ...] = ()

@dataclass(frozen=True)
class Principle:
    id: str
    name: str
    one: str
    three: str
    anti: str
    axioms: tuple[str, ...]
    enforcement: str
    enforced_by: tuple[str, ...] = ()
    sources: tuple[SourceRef, ...] = ()

@dataclass(frozen=True)
class SkillRef:
    path: str
    when: str


def local_path(value: object) -> bool:
    """A literal repository-relative path, never a URL or traversal."""
    return (isinstance(value, str) and bool(value) and ':' not in value and '\\' not in value
            and not any(ord(c) < 32 for c in value)
            and all(p not in ('', '.', '..') for p in value.split('/')))


@dataclass(frozen=True)
class Route:
    id: str
    paths: tuple[str, ...]
    principles: tuple[str, ...]
    reminder: str
    on: tuple[str, ...] = ("edit",)
    skills: tuple[SkillRef, ...] = ()

    def matches(self, rel_path: str) -> bool:
        return any(glob_match(pattern, rel_path) for pattern in self.paths)

@dataclass
class Doctrine:
    name: str
    version: str
    summary: str
    entry_budget_lines: int
    sources: dict[str, Source] = field(default_factory=dict)
    axioms: dict[str, Axiom] = field(default_factory=dict)
    principles: dict[str, Principle] = field(default_factory=dict)
    routes: dict[str, Route] = field(default_factory=dict)
    path: Path | None = None
    layout_policy: str = ""

    def routes_for(self, rel_path: str, trigger: str | None = None) -> list[Route]:
        """Routes whose paths match `rel_path` (and whose triggers include `trigger`)."""
        rel_path = normalise(rel_path)
        return [route for route in self.routes.values()
                if route.matches(rel_path) and (trigger is None or trigger in route.on)]

    def principles_for(self, rel_path: str, trigger: str | None = None) -> list[Principle]:
        """Principles routed to `rel_path`, in doctrine order, without duplicates."""
        wanted = {pid for route in self.routes_for(rel_path, trigger) for pid in route.principles}
        return [p for pid, p in self.principles.items() if pid in wanted]

    def global_principles(self) -> list[Principle]:
        """Principles no route attaches to a place: they travel in the entry card."""
        routed = {pid for route in self.routes.values() for pid in route.principles}
        return [p for pid, p in self.principles.items() if pid not in routed]

    def entry_lines(self) -> list[str]:
        """The compressed doctrine every agent reads on arrival (one line per item)."""
        script = ".doctrine/doctrine.py" if self.path and self.path.parent.name == ".doctrine" else "doctrine.py"
        lines = [f"Doctrine: {self.name} {self.version}. {self.summary}", "", "Axioms:"]
        lines += [f"- {a.id} {a.name}: {a.plain}" for a in self.axioms.values()]
        lines += ["", "Principles (enforcement in brackets):"]
        lines += [f"- {p.id} [{p.enforcement}] {p.one}" for p in self.principles.values()]
        return lines + ["", "Place-specific reminders arrive when you work in the places they govern.",
                        f"Run `python3 {script} explain <path>` to see what applies to a path."]

def normalise(rel_path: str) -> str:
    text = str(rel_path).replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/")

@functools.lru_cache(maxsize=4096)
def _compile(pattern: str) -> re.Pattern[str]:
    pat = pattern.strip().replace("\\", "/")
    anchored = "/" in pat.rstrip("/")
    pat = pat.strip("/")
    pat = pat[:-3] if pat.endswith("/**") else pat  # what lies beneath is matched below anyway
    parts = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}
    body = "".join(parts.get(t) or re.escape(t) for t in re.findall(r"\*\*/|\*\*|\*|\?|[^*?]+", pat))
    return re.compile(rf"^{body if anchored else '(?:.*/)?' + body}(?:/.*)?$")

def glob_match(pattern: str, rel_path: str) -> bool:
    """Match a repository-relative path against a route glob.

    `**` spans directories, `*` and `?` stay within one path segment. A pattern with no
    slash matches the name at any depth, as in .gitignore. A pattern that names a
    directory also matches everything beneath it.
    """
    return bool(_compile(pattern).match(normalise(rel_path)))

def _strs(value: object) -> tuple[str, ...]:
    return () if value is None else (value,) if isinstance(value, str) else tuple(str(v) for v in value)  # type: ignore[union-attr]

def _refs(items: Iterable[dict] | None) -> tuple[SourceRef, ...]:
    return tuple(SourceRef(ref=str(item.get("ref", "")), at=str(item.get("at", "")),
                           quote=str(item.get("quote", ""))) for item in items or ())

def load(path: str | Path) -> Doctrine:
    """Read and validate a doctrine file. Raises DoctrineError listing every problem."""
    path = Path(path)
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    return from_dict(raw, path)

def from_dict(raw: dict, path: Path | None = None) -> Doctrine:
    """Build a Doctrine from parsed TOML. Raises DoctrineError listing every problem."""
    problems: list[str] = []
    meta = raw.get("doctrine", {})
    d = Doctrine(name=str(meta.get("name", "doctrine")), version=str(meta.get("version", "0")),
                 summary=str(meta.get("summary", "")),
                 entry_budget_lines=int(meta.get("entry_budget_lines", 40)), path=path,
                 layout_policy=meta.get("layout_policy", ""))
    if d.layout_policy and not local_path(d.layout_policy):
        problems.append("layout_policy must be a repository-relative path")

    def items(kind: str, seen: dict) -> Iterable[tuple[str, dict]]:
        for item in raw.get(kind, []):
            ident = str(item.get("id", ""))
            if not ident or ident in seen:
                problems.append(f"duplicate {kind} id {ident}" if ident else f"{kind} without an id")
            else:
                yield ident, item

    def text(item: dict, key: str, default: str = "") -> str:
        return str(item.get(key, default))

    for sid, item in items("source", d.sources):
        d.sources[sid] = Source(id=sid, title=text(item, "title", sid), url=text(item, "url"),
                                publisher=text(item, "publisher"), date=text(item, "date"),
                                licence=text(item, "licence"), quote_policy=text(item, "quote_policy", "cite"))
    for aid, item in items("axiom", d.axioms):
        d.axioms[aid] = Axiom(id=aid, name=text(item, "name"), clause=text(item, "clause"),
                              plain=text(item, "plain"), anti=text(item, "anti"), sources=_refs(item.get("sources")))
    for pid, item in items("principle", d.principles):
        d.principles[pid] = Principle(
            id=pid, name=text(item, "name"), one=text(item, "one"), three=text(item, "three"),
            anti=text(item, "anti"), axioms=_strs(item.get("axioms")), enforcement=text(item, "enforcement", "prose"),
            enforced_by=_strs(item.get("enforced_by")), sources=_refs(item.get("sources")))
    for rid, item in items("route", d.routes):
        skills = []
        raw_skills = item.get("skills", [])
        if not isinstance(raw_skills, list):
            problems.append(f"route {rid}: skills must be a list of path/when tables")
            raw_skills = []
        for skill in raw_skills:
            if (not isinstance(skill, dict) or not local_path(skill.get("path"))
                    or not skill['path'].endswith('/SKILL.md')
                    or not isinstance(skill.get('when'), str) or not skill['when'].strip()):
                problems.append(f"route {rid}: each skill needs a local SKILL.md path and when to use it")
            elif skill['path'] in {ref.path for ref in skills}:
                problems.append(f"route {rid}: duplicate skill {skill['path']}")
            else:
                skills.append(SkillRef(skill['path'], skill['when']))
        d.routes[rid] = Route(id=rid, paths=_strs(item.get("paths")), principles=_strs(item.get("principles")),
                              reminder=text(item, "reminder"), on=_strs(item.get("on")) or ("edit",), skills=tuple(skills))

    for s in d.sources.values():
        if s.quote_policy not in QUOTE_POLICIES:
            problems.append(f"source {s.id}: quote_policy must be one of {QUOTE_POLICIES}")
        if not s.url:
            problems.append(f"source {s.id} has no url")
    if len(d.axioms) > 7:
        problems.append(f"{len(d.axioms)} axioms; a doctrine keeps at most seven")
    for a in d.axioms.values():
        if not a.anti:
            problems.append(f"axiom {a.id} has no anti-axiom")
        problems += [f"axiom {a.id} cites unknown source {r.ref}" for r in a.sources if r.ref not in d.sources]
    for p in d.principles.values():
        if p.enforcement not in LEVELS:
            problems.append(f"principle {p.id}: enforcement must be one of {LEVELS}")
        if not p.anti:
            problems.append(f"principle {p.id} has no anti-principle")
        if not p.axioms:
            problems.append(f"principle {p.id} serves no axiom")
        problems += [f"principle {p.id} serves unknown axiom {a}" for a in p.axioms if a not in d.axioms]
        problems += [f"principle {p.id} cites unknown source {r.ref}" for r in p.sources if r.ref not in d.sources]
    for r in d.routes.values():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", r.id):
            problems.append(f"route {r.id}: id may hold only letters, digits, '.', '_' and '-'")
        if not r.paths:
            problems.append(f"route {r.id} has no paths")
        problems += [f"route {r.id}: trigger {t!r} must be one of {TRIGGERS}" for t in r.on if t not in TRIGGERS]
        problems += [f"route {r.id} names unknown principle {pid}" for pid in r.principles if pid not in d.principles]
    if problems:
        raise DoctrineError(problems)
    return d

def find_doctrine(start: str | Path) -> Path | None:
    """Walk up from `start` to the nearest doctrine.toml (or .doctrine/doctrine.toml)."""
    here = Path(start).resolve()
    for folder in (here, *here.parents):
        for target in (folder / "doctrine.toml", folder / ".doctrine" / "doctrine.toml"):
            if target.is_file():
                return target
    return None

def repo_root(doctrine_path: str | Path) -> Path:
    """The repository a doctrine governs: its folder, or the parent of a .doctrine folder."""
    folder = Path(doctrine_path).resolve().parent
    return folder.parent if folder.name == ".doctrine" else folder

def relative_to_root(path: str | Path, root: str | Path) -> str | None:
    """Repository-relative POSIX path, or None when `path` lies outside `root`."""
    try:
        rel = Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return None
    return PurePosixPath(rel).as_posix()


# =========================================================================== 2. the repository

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
LOCAL_STATE = (".doctrine/sessions/", ".doctrine/graph.json", ".doctrine/mistakes.jsonl")

@dataclass
class Repo:
    root: Path
    doctrine: Doctrine
    files: list[str]
    settings: dict

    @property
    def source(self) -> str:
        return relative_to_root(self.doctrine.path, self.root) or "doctrine.toml"

def git(root: Path, *args: str) -> str | None:
    """Output of a git command run in `root`, or None when git or a repository is missing."""
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None

def repo_files(root: Path) -> list[str]:
    """Repository-relative paths of the files a doctrine governs, sorted.

    In a git work tree: tracked files plus untracked files git does not ignore. Elsewhere:
    a walk that skips version control, dependency and build folders. Local state that the
    hooks and the map write under .doctrine/ is never counted.
    """
    if (git(root, "rev-parse", "--is-inside-work-tree") or "").strip() == "true":
        listed = (git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard") or "").split("\0")
        gone = set((git(root, "ls-files", "-z", "--deleted") or "").split("\0"))
        files = [f for f in listed if f and not f.endswith("/") and f not in gone]
    else:
        files = []
        for here, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            rel = Path(here).relative_to(root).as_posix()
            files += [name if rel == "." else f"{rel}/{name}" for name in names]
    return sorted({f for f in files if not f.startswith(LOCAL_STATE) and not SKIP_DIRS & set(f.split("/")[:-1])})

def read_text(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None

def read_json(path: Path) -> dict:
    try:
        value = json.loads(read_text(path) or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}

def read_literal(path: Path, name: str) -> object:
    """A top-level literal assignment in a Python file, read with ast. The file never runs."""
    try:
        tree = ast.parse(read_text(path) or "")
    except (SyntaxError, ValueError):
        return None
    value = None
    for node in tree.body:
        target = node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else \
            node.target if isinstance(node, ast.AnnAssign) and node.value is not None else None
        if isinstance(target, ast.Name) and target.id == name:
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError, RecursionError):
                value = None
    return value

def open_repo(doctrine_path: str | Path | None = None) -> Repo:
    path = Path(doctrine_path) if doctrine_path else find_doctrine(Path.cwd())
    if path is None or not path.is_file():
        raise UsageError("no doctrine found here or above (doctrine.toml or .doctrine/doctrine.toml); "
                         "run: python3 doctrine.py init")
    root = repo_root(path)
    return Repo(root, load(path.resolve()), repo_files(root), read_json(root / ".claude" / "settings.json"))

def hook_commands(settings: dict) -> list[str]:
    """Every hook command line in a Claude Code settings object."""
    found = []
    events = settings.get("hooks")
    for groups in events.values() if isinstance(events, dict) else ():
        for group in groups if isinstance(groups, list) else ():
            for hook in (group.get("hooks") if isinstance(group, dict) else None) or ():
                if isinstance(hook, dict):
                    found.append(" ".join(str(x) for x in [hook.get("command", ""), *(hook.get("args") or [])]))
    return found

def hooks_wired(settings: dict, event: str | None = None, tools: Iterable[str] = ()) -> bool:
    """Recognised event wiring, with every required tool covered by its matchers."""
    if settings.get("disableAllHooks") is True:
        return False
    plugins = settings.get("enabledPlugins")
    if isinstance(plugins, dict) and any(str(k).startswith(("safety-core@", "doctrine-map@")) and v for k, v in plugins.items()):
        return True
    events = settings.get("hooks")
    events = events if isinstance(events, dict) else {}
    selected = events.values() if event is None else [events.get(event, [])]
    patterns = []
    for groups in selected:
        for group in groups if isinstance(groups, list) else ():
            if not isinstance(group, dict):
                continue
            commands = hook_commands({"hooks": {"selected": [group]}})
            if any("hooks.py" in command and "doctrine" in command for command in commands):
                patterns.append(group.get("matcher", ""))

    def matches(pattern, tool):
        if pattern in ("", "*"):
            return True
        if not isinstance(pattern, str):
            return False
        try:
            return re.search(pattern, tool) is not None
        except re.error:
            return False

    return bool(patterns) and all(any(matches(pattern, tool) for pattern in patterns) for tool in tools)


# =========================================================================== 3. enforcers

BUILT_IN = {"check:links": "check", "check:drift": "check", "cli:log-error": "prose"}
"""Enforcers this file provides. log-error records a lesson; on its own it stops nothing."""

GUARDS = {
    # Other projects' hooks, credited when the repository's .claude/settings.json runs them:
    # the command names that identify each, and the hooks.py checks whose job it does out of
    # the box (each project's README, October 2026). Cupcake enforces only the policies you
    # write, so it counts only where a principle names it: enforced_by = ["guard:cupcake"].
    "nah": (("nah",), {"irreversible": "ask", "secrets": "block"}),
    "cc-safety-net": (("cc-safety-net",), {"irreversible": "ask", "secrets": "block"}),
    "dcg": (("dcg", "destructive_command_guard", "destructive-command-guard"), {"irreversible": "ask"}),
    "cupcake": (("cupcake",), {}),
}

@dataclass
class Enforcer:
    ref: str
    type: str
    level: str | None
    status: str
    file: str
    detail: str = ""

def strongest(levels: Iterable[str | None]) -> str:
    return min((lv for lv in levels if lv in LEVEL_RANK), key=LEVEL_RANK.__getitem__, default="prose")

def find_hooks(root: Path, settings: dict) -> Path:
    """The hooks.py whose CHECKS count: the repository's own copy, else the one beside this file."""
    own = root / ".doctrine" / "hooks.py"
    wired_here = any(".doctrine/hooks.py" in command for command in hook_commands(settings))
    return own if own.exists() or wired_here else HERE / "hooks.py"

def wired_guards(settings: dict) -> set[str]:
    """External guards that .claude/settings.json runs as hooks, found by command name."""
    names = set()
    for command in hook_commands(settings):
        try:
            words = shlex.split(command)
        except ValueError:
            words = command.split()
        for word in [w for w in words if not w.startswith("-")][:3]:
            names.add(re.sub(r"\.(exe|js|py)$", "", word.replace("\\", "/").rsplit("/", 1)[-1].split("@")[0]))
    return {tool for tool, (aliases, _) in GUARDS.items() if names & set(aliases)}

def resolve_enforcers(repo: Repo, matched: dict[str, list[str]]):
    """Resolve each enforcer the doctrine names, and credit wired external guards.

    Returns (enforcers by ref, each principle's list of {ref, status, level[, by]}, notes).
    """
    hooks_file = find_hooks(repo.root, repo.settings)
    hooks_name = relative_to_root(hooks_file, repo.root) or "hooks.py"
    checks = read_literal(hooks_file, "CHECKS")
    checks = {str(k): v for k, v in checks.items() if isinstance(v, dict)} if isinstance(checks, dict) else {}
    guards = set() if repo.settings.get("disableAllHooks") is True else wired_guards(repo.settings)
    raw = tomllib.loads(Path(repo.doctrine.path).read_text(encoding="utf-8"))
    modes = raw.get("hooks", {})
    modes = modes if isinstance(modes, dict) else {}
    nodes: dict[str, Enforcer] = {}
    notes: list[str] = []

    def make(ref: str) -> Enforcer:
        kind, _, rest = ref.partition(":")
        if kind in ("hook", "stop"):  # every hook check lives in hooks.py's CHECKS, keyed after '#'
            check = checks.get(rest.partition("#")[2])
            if check is None:
                why = f"{hooks_name} has no check {rest.partition('#')[2]!r}" if hooks_file.exists() else f"{hooks_name} not found"
                return Enforcer(ref, kind, None, "missing", hooks_name, why)
            if check.get("level") not in (*LEVELS, "off", "record"):
                notes.append(f"{ref} has level {check.get('level')!r}, not one of {', '.join((*LEVELS, 'off', 'record'))}")
            key = rest.partition("#")[2]
            event = check.get("event") or {"pre_tool": "PreToolUse", "post_tool": "PostToolUse"}.get(
                rest.partition("#")[0], "Stop" if kind == "stop" else "")
            mode = modes.get(key)
            mode = mode if mode in ("block", "ask", "remind", "advise", "record", "off") else check.get("level")
            level = mode if mode in LEVELS else None
            required_tools = check.get("tools", ())
            if not event or not hooks_wired(repo.settings, event, required_tools):
                level = None
                scope = f" covering {', '.join(required_tools)}" if required_tools else ""
                notes.append(f"{ref} is not wired for {event or 'a known event'}{scope} in repository settings; no hook credit.")
            elif mode in ("off", "record"):
                notes.append(f"{ref} is {mode}; it does not enforce or deliver this rule.")
            elif event == "Stop" and mode != "block":
                level = "advise"
            elif event in ("PostToolUse", "PostToolUseFailure", "SessionStart") and mode in ("block", "ask"):
                level = "remind"
            receipt_events = check.get("receipt_events", ())
            if level and receipt_events:
                if modes.get("receipts") == "off":
                    notes.append(f"{ref} has receipts off; command-result contradictions are not checked. "
                                 "Git-state contradictions can still be checked.")
                else:
                    for receipt_event in receipt_events:
                        if not hooks_wired(repo.settings, receipt_event, ("Bash",)):
                            notes.append(f"{ref} lacks Bash receipts from {receipt_event}; command results from that "
                                         "event cannot contradict final claims. Git-state contradictions can still be checked.")
            return Enforcer(ref, kind, level, "present", hooks_name)
        if ref in BUILT_IN:
            return Enforcer(ref, kind, BUILT_IN[ref], "present", "doctrine.py")
        if kind == "route":
            live = bool(matched.get(rest))
            why = "" if live else "the route matches no file" if rest in repo.doctrine.routes else "no such route"
            return Enforcer(ref, "route", "remind", "present" if live else "missing", repo.source, why)
        if kind == "guard":
            on = rest in guards
            why = "" if on else f"{rest} is not run by any hook in .claude/settings.json"
            return Enforcer(ref, "guard", None, "present" if on else "missing", ".claude/settings.json", why)
        return Enforcer(ref, kind or "unknown", None, "missing", "", f"{kind or ref!r} is not a kind of enforcer")

    per: dict[str, list[dict]] = {}
    for p in repo.doctrine.principles.values():
        entries = per.setdefault(p.id, [])
        for ref in p.enforced_by:
            e = nodes[ref] if ref in nodes else nodes.setdefault(ref, make(ref))
            entry = {"ref": ref, "status": e.status, "level": e.level if e.status == "present" else None}
            if e.type == "guard":  # a principle that names a guard asserts its own level for it
                entry.update(level=p.enforcement if e.status == "present" else None, by=ref.partition(":")[2])
                e.level = strongest([e.level, entry["level"]]) if e.status == "present" else None
            entries.append(entry)
            check = checks.get(ref.partition("#")[2]) if e.type in ("hook", "stop") else None
            if check is not None and p.id not in check.get("principles", ()):
                notes.append(f"{ref} does not list {p.id} among the principles it serves")
        keys = {ref.partition("#")[2] for ref in p.enforced_by if "#" in ref}
        for tool in sorted(guards):
            credit = [level for key, level in GUARDS[tool][1].items() if key in keys]
            if credit and f"guard:{tool}" not in p.enforced_by:
                node = nodes.setdefault(f"guard:{tool}", Enforcer(f"guard:{tool}", "guard", None, "present",
                                                                  ".claude/settings.json"))
                node.level = strongest([node.level, *credit])
                entries.append({"ref": f"guard:{tool}", "status": "present", "level": strongest(credit), "by": tool})
    return nodes, per, notes

def tier(principle: dict, types: dict[str, str], local: bool) -> str:
    """How a principle holds at a place: hooks and checks hold it everywhere, and a route
    makes it at least reminded where the route reaches."""
    held = TIERS[strongest(e["level"] for e in principle["enforcers"]
                           if e["status"] == "present" and types.get(e["ref"]) != "route")]
    return "reminded" if local and held == "words" else held


# =========================================================================== 4. the graph

SENSITIVE = {
    "CI": (".github/workflows/**", ".gitlab-ci.yml", ".circleci/**", "Jenkinsfile", "azure-pipelines.yml",
           ".buildkite/**"),
    "infrastructure": ("**/*.tf", "**/*.tfvars", "infra/**", "terraform/**", "deploy/**", "k8s/**",
                       "kubernetes/**", "helm/**"),
    "migration": ("**/migrations/**", "db/migrate/**", "alembic/versions/**"),
    "secret": (".env", ".env.*", "**/*.pem", "**/*.key", "**/*.p12", "**/*.pfx", "id_rsa*", "secrets/**",
               "**/credentials*"),
    "release": ("scripts/release*", "release/**", ".goreleaser.y*ml", ".releaserc*"),
}
"""Places that deserve a route in any repository; a sensitive file no route reaches is reported."""

def sensitive_kind(rel_path: str) -> str | None:
    return next((kind for kind, patterns in SENSITIVE.items() if any(glob_match(p, rel_path) for p in patterns)), None)

def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

DEFAULT_LAYOUT_POLICIES = ('docs/repository_layout.json', 'docs/maintainers/repository-layout.json')


def layout_roles(repo: Repo) -> tuple[str, dict]:
    """Read display metadata from the existing project policy; never execute a skill helper."""
    source = repo.doctrine.layout_policy or next(
        (path for path in DEFAULT_LAYOUT_POLICIES if (repo.root / path).exists()), '')
    if not source:
        return '', {}
    target = repo.root / source
    if relative_to_root(target, repo.root) is None:
        raise DoctrineError(['layout policy must stay inside the repository'])
    try:
        policy = json.loads(target.read_text(encoding='utf-8'))
        if not isinstance(policy, dict) or policy.get('schema') not in ('repository_layout@1', 'repository_layout@2'):
            raise ValueError('unsupported repository layout schema')
        roles = policy.get('directories')
        if not isinstance(roles, dict):
            raise ValueError('directories must be an object')
        for name, role in roles.items():
            if (not local_path(name) or not isinstance(role, dict)
                    or not isinstance(role.get('purpose'), str) or not role['purpose'].strip()
                    or ('/' in name and policy['schema'] == 'repository_layout@1')
                    or ('guide' in role and not local_path(role['guide']))):
                raise ValueError('invalid directory purpose or guide: ' + str(name))
        return source, roles
    except (OSError, ValueError) as exc:
        raise DoctrineError([f'{source}: {exc}']) from exc


def purpose_for(path: str, roles: dict) -> tuple[str, dict]:
    ancestors = [p for p in roles if path == p or path.startswith(p + '/')]
    name = max(ancestors, key=lambda p: len(p.split('/')), default='')
    return name, roles.get(name, {})


def skill_details(repo: Repo, route: Route) -> list[dict]:
    result = []
    for ref in route.skills:
        present = ref.path in repo.files and relative_to_root(repo.root / ref.path, repo.root) is not None
        text = read_text(repo.root / ref.path) if present else None
        result.append({'path': ref.path, 'when': ref.when,
                       'status': 'present' if text is not None else 'missing', 'text': text})
    return result


def build_graph(repo: Repo, stale: Iterable[tuple[str, str]] = ()) -> tuple[dict, list[str]]:
    """The doctrine and the repository as one graph (doctrine-map/graph@1), plus link notes."""
    d, files = repo.doctrine, repo.files
    policy_source, roles = layout_roles(repo)
    matched = {rid: [f for f in files if route.matches(f)] for rid, route in d.routes.items()}
    live = {rid for rid, hits in matched.items() if hits}
    enforcers, entries, notes = resolve_enforcers(repo, matched)
    carried = {pid for rid in live for pid in d.routes[rid].principles}
    effective = {pid: strongest([e["level"] for e in entries[pid] if e["status"] == "present"]
                                + (["remind"] if pid in carried else [])) for pid in d.principles}
    nodes: list[dict] = []
    edges: list[dict] = []
    gaps: list[dict] = []

    def cite(owner: str, refs: tuple[SourceRef, ...]) -> list[dict]:
        for target in dict.fromkeys("src:" + r.ref for r in refs):
            edges.append({"kind": "cites", "from": owner, "to": target})
        return [{"ref": r.ref, "at": r.at, "quote": r.quote} for r in refs]

    for a in d.axioms.values():
        nodes.append({"id": a.id, "kind": "axiom", "name": a.name, "clause": a.clause, "plain": a.plain,
                      "anti": a.anti, "sources": cite(a.id, a.sources)})
    for p in d.principles.values():
        nodes.append({"id": p.id, "kind": "principle", "name": p.name, "one": p.one, "three": p.three,
                      "anti": p.anti, "axioms": list(p.axioms), "declared": p.enforcement,
                      "effective": effective[p.id], "enforcers": entries[p.id], "global": p.id not in carried,
                      "sources": cite(p.id, p.sources)})
        edges += [{"kind": "serves", "from": p.id, "to": aid} for aid in p.axioms]
        edges += [{"kind": "enforced_by", "from": p.id, "to": "enf:" + e["ref"]} for e in entries[p.id]]
        if effective[p.id] == "prose":
            gaps.append({"kind": "prose_only", "id": p.id,
                         "detail": f"{p.name}: nothing delivers or enforces it beyond the entry card."})
        gaps += [{"kind": "missing_enforcer", "id": p.id,
                  "detail": f"{p.id} names {e['ref']}, which is missing: {enforcers[e['ref']].detail}."}
                 for e in entries[p.id] if e["status"] == "missing"]
        if not p.enforced_by and p.enforcement != "prose" and effective[p.id] == "prose":
            gaps.append({"kind": "missing_enforcer", "id": p.id,
                         "detail": f"{p.id} declares {p.enforcement} but names no enforcer."})

    for r in d.routes.values():
        nodes.append({"id": "route:" + r.id, "kind": "route", "name": r.id, "paths": list(r.paths),
                      "reminder": r.reminder, "on": list(r.on), "principles": list(r.principles),
                      "matches": len(matched[r.id]), "skills": skill_details(repo, r)})
        gaps += [{"kind": "missing_skill", "id": "route:" + r.id, "path": ref["path"],
                  "detail": "Route skill is missing or outside the repository: " + ref["path"]}
                 for ref in skill_details(repo, r) if ref["status"] == "missing"]
        edges += [{"kind": "applies", "from": "route:" + r.id, "to": pid} for pid in r.principles]
        if not matched[r.id]:
            gaps.append({"kind": "dead_route", "id": "route:" + r.id,
                         "detail": f"Route {r.id} matches no file ({', '.join(r.paths)})."})

    # Places: folders at depth one and two, and root files that a route or a sensitive pattern names.
    reach: dict[str, set[str]] = {}
    for rid, hits in matched.items():
        for f in hits:
            reach.setdefault(f, set()).add(rid)
    kinds = {f: sensitive_kind(f) for f in files}
    groups: dict[str, list[str]] = {}
    for f in files:
        parts = f.split("/")
        for depth in (1, 2):
            if len(parts) > depth:
                groups.setdefault("/".join(parts[:depth]), []).append(f)
        if len(parts) == 1 and (f in reach or kinds[f]):
            groups[f] = [f]
    for declared in roles:
        groups.setdefault(declared, [f for f in files if f.startswith(declared + '/')])
    for path in sorted(groups):
        members, is_dir = groups[path], path not in kinds
        declared, role = purpose_for(path, roles)
        routed = set().union(*(reach.get(f, set()) for f in members))
        rids = [rid for rid in d.routes if rid in routed]
        nodes.append({"id": "place:" + path, "kind": "place", "name": path + ("/" if is_dir else ""), "path": path,
                      "is_dir": is_dir, "files": len(members), "sensitive": any(kinds[f] for f in members),
                      "purpose": role.get('purpose'), "purpose_path": declared or None,
                      "policy_source": policy_source or None, "guide": role.get('guide'),
                      "observation": 'observed' if members else 'declared_only',
                      "routes": ["route:" + rid for rid in rids],
                      "principles": [pid for pid in d.principles if any(pid in d.routes[r].principles for r in rids)]})
        for rid in rids:
            hits = [f for f in members if rid in reach.get(f, set())]
            edges.append({"kind": "governs", "from": "route:" + rid, "to": "place:" + path,
                          "matches": len(hits), "matched_files": hits})
    unrouted: dict[str, list[str]] = {}
    for f in files:
        if kinds[f] and f not in reach:
            parts = f.split("/")
            unrouted.setdefault("/".join(parts[:min(len(parts) - 1, 2)]) or f, []).append(f)
    for path, members in sorted(unrouted.items()):
        what = " and ".join(sorted({kinds[f] for f in members}))
        shown = ", ".join(members[:3]) + (", ..." if len(members) > 3 else "")
        gaps.append({"kind": "unrouted_sensitive", "id": "place:" + path, "path": path,
                     "detail": f"{path} holds {what} files ({shown}) but no route governs them."})

    for name, role in roles.items():
        if role.get('guide') and (role['guide'] not in files or relative_to_root(repo.root / role['guide'], repo.root) is None):
            gaps.append({'kind': 'missing_guide', 'id': 'place:' + name, 'path': role['guide'],
                         'detail': 'Declared owner guide is missing or outside the repository.'})
    for ref, e in enforcers.items():
        nodes.append({"id": "enf:" + ref, "kind": "enforcer", "name": ref, "ref": ref, "type": e.type,
                      "level": e.level, "status": e.status, "file": e.file})
    for s in d.sources.values():
        nodes.append({"id": "src:" + s.id, "kind": "source", "name": s.title, "title": s.title,
                      "publisher": s.publisher, "date": s.date, "url": s.url, "licence": s.licence,
                      "quote_policy": s.quote_policy})
    gaps += [{"kind": "stale_projection", "path": path, "detail": why} for path, why in stale]
    entry = d.entry_lines()
    if len(entry) > d.entry_budget_lines:
        gaps.append({"kind": "over_budget", "id": "entry",
                     "detail": f"The entry card is {len(entry)} lines; its budget is {d.entry_budget_lines}."})
    by_level = {level: sum(1 for e in effective.values() if e == level) for level in LEVELS}
    return {
        "schema": "doctrine-map/graph@1",
        "generated_at": now(),
        "repository": {"name": repo.root.name, "files_total": len(files),
                       "commit": (git(repo.root, "rev-parse", "--short", "HEAD") or "").strip() or None},
        "doctrine": {"name": d.name, "version": d.version, "summary": d.summary, "source": repo.source,
                     "sha256": hashlib.sha256(Path(d.path).read_bytes()).hexdigest() if d.path else ""},
        "entry": {"lines": entry, "budget": d.entry_budget_lines, "used": len(entry)},
        "nodes": nodes, "edges": edges, "gaps": gaps,
        "coverage": {"basis": "declared_repository_configuration",
                     "not_evaluated": ["task_completeness", "undeclared_requirements", "live_hook_execution"],
                     "axioms": len(d.axioms), "principles": len(d.principles), "by_level": by_level,
                     "enforced_beyond_words": sum(by_level[level] for level in ("block", "ask", "check")), "files_total": len(files),
                     "files_governed": len(reach), "routes_live": len(live), "routes_dead": len(d.routes) - len(live)},
    }, notes


# =========================================================================== 5. projections

BEGIN, END = "<!-- doctrine-map:begin -->", "<!-- doctrine-map:end -->"
GENERATED = "doctrine-map:generated"

def header(source: str) -> str:
    return f"<!-- {GENERATED} from {source} by doctrine.py build. Do not edit; change {source} and rebuild. -->"

def export_globs(patterns: Iterable[str]) -> list[str]:
    """Route patterns as plain globs for other tools, with the same meaning: a pattern
    without a slash matches at any depth, and a match also covers everything beneath it."""
    globs = []
    for pattern in patterns:
        text = pattern.strip().replace("\\", "/")
        anchored = "/" in text.rstrip("/")
        text = text.strip("/")
        base = text if anchored or text.startswith("**") else f"**/{text}"
        if base.endswith("/**"):  # "docs/**" also matches a file named docs
            globs += [base, base[:-3]]
        else:
            globs += [base] if base.endswith("**") else [base, f"{base}/**"]
    return list(dict.fromkeys(globs))

def outputs(repo: Repo, rulesync: bool = False) -> dict[str, tuple[str, str]]:
    """Everything the build writes, as {path: ("region" or "file", content)}."""
    d, src = repo.doctrine, repo.source
    table = ["| Route | Paths | Principles |", "|---|---|---|"]
    for r in d.routes.values():
        paths = ", ".join("`" + p.replace("|", "\\|") + "`" for p in r.paths)
        table.append(f"| {r.id} | {paths} | {', '.join(r.principles)} |")
    agents = [header(src), *d.entry_lines(), "", "Where rules live:", "", *table, "",
              "Each route's reminder and principles are in `.claude/rules/doctrine-<route>.md`. "
              "Read that file before you work in its paths."]
    claude = [header(src), "@AGENTS.md", "Path rules for this repository load from "
              "`.claude/rules/doctrine-*.md` when you work on matching files."]
    out = {"AGENTS.md": ("region", "\n".join(agents) + "\n"), "CLAUDE.md": ("region", "\n".join(claude) + "\n")}
    for r in d.routes.values():
        body = [header(src), f"# Doctrine route: {r.id}", "", r.reminder]
        for ref in r.skills:
            body += ["", f"Workflow: `{ref.path}` — {ref.when}. Read the skill when relevant; a link does not run it."]
        for p in (d.principles[pid] for pid in r.principles):
            body += ["", f"## {p.id} {p.name} [{p.enforcement}]", "", p.one, "", p.three]
        globs = export_globs(r.paths)
        front = ["---", "paths:", *[f"  - {json.dumps(g)}" for g in globs], "---"]
        out[f".claude/rules/doctrine-{r.id}.md"] = ("file", "\n".join(front + body) + "\n")
        if rulesync:
            front = ["---", "root: false", 'targets: ["*"]', f"description: {json.dumps(r.reminder, ensure_ascii=False)}",
                     f"globs: {json.dumps(globs)}", "---"]
            out[f".rulesync/rules/doctrine-{r.id}.md"] = ("file", "\n".join(front + body) + "\n")
    return out

def region_of(text: str | None) -> str | None:
    """The managed region's content, or None when there is none. Raises on broken markers."""
    if text is None:
        return None
    text = text.replace("\r\n", "\n")
    begin, end = text.find(BEGIN), text.find(END)
    if begin < 0 and end < 0:
        return None
    if begin < 0 or end < begin or text.count(BEGIN) > 1 or text.count(END) > 1:
        raise ValueError("its doctrine-map markers are unbalanced; fix them by hand")
    return text[begin + len(BEGIN):end].removeprefix("\n")

def splice(text: str | None, region: str) -> str:
    """`text` with its managed region replaced by `region`; everything outside stays as it was."""
    block = f"{BEGIN}\n{region}{END}"
    if not text or not text.strip():
        return block + "\n"
    newline = "\r\n" if "\r\n" in text else "\n"
    block = block.replace("\n", newline)
    if region_of(text) is None:
        return text + ("" if text.endswith("\n") else newline) + newline + block + newline
    return text[:text.find(BEGIN)] + block + text[text.find(END) + len(END):]

def generated_files(root: Path) -> list[str]:
    """Route rule files a build wrote earlier, recognised by their header."""
    return [f"{folder}/{path.name}" for folder in (".claude/rules", ".rulesync/rules")
            for path in sorted((root / folder).glob("doctrine-*.md")) if GENERATED in (read_text(path) or "")]

def exported(root: Path) -> bool:
    """True once `build --export rulesync` has run here: the export then stays in step."""
    return any(p.startswith(".rulesync/") for p in generated_files(root))

def drift(repo: Repo, outs: dict[str, tuple[str, str]]) -> list[tuple[str, str]]:
    """Generated files that differ from a fresh build, as (path, why)."""
    stale = []
    for path, (kind, content) in outs.items():
        text = read_text(repo.root / path)
        try:
            current = text.replace("\r\n", "\n") if kind == "file" and text is not None else region_of(text)
        except ValueError as exc:
            stale.append((path, str(exc)))
            continue
        if current is None:
            stale.append((path, "has no doctrine-map region; run doctrine.py build" if text is not None
                          else "missing; run doctrine.py build"))
        elif current != content:
            stale.append((path, "differs from a fresh build; change doctrine.toml and run doctrine.py build"))
    return stale + [(path, "was generated for a route that no longer exists; run doctrine.py build")
                    for path in generated_files(repo.root) if path not in outs]

def write_outputs(repo: Repo, outs: dict[str, tuple[str, str]]) -> list[str]:
    """Write each projection that changed and remove orphaned rule files. Text outside a
    managed region is never touched. Returns what changed."""
    changed = []
    for path, (kind, content) in outs.items():
        target = repo.root / path
        old = read_text(target)
        try:
            new = content if kind == "file" else splice(old, content)
        except ValueError as exc:
            raise UsageError(f"{path}: {exc}") from None
        if new != old:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8", newline="") as fh:
                fh.write(new)
            changed.append(path)
    for path in generated_files(repo.root):
        if path not in outs:
            (repo.root / path).unlink()
            changed.append(f"{path} (removed)")
    return changed

def write_graph(repo: Repo, graph: dict) -> None:
    ensure_gitignore(repo.root)
    text = json.dumps(graph, indent=2, ensure_ascii=False) + "\n"
    (repo.root / ".doctrine" / "graph.json").write_text(text, encoding="utf-8")

GITIGNORE = ("# Local state written by doctrine-map: session records, the built graph and the mistakes log.\n"
             "sessions/\ngraph.json\nmistakes.jsonl\n__pycache__/\n")

def ensure_gitignore(root: Path) -> None:
    path = root / ".doctrine" / ".gitignore"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(GITIGNORE, encoding="utf-8")

WIRING = {"SessionStart": ("startup|clear|compact", 10), "PreToolUse": ("Bash|Edit|Write|MultiEdit|NotebookEdit|Read", 15),
          "PostToolUse": ("*", 10), "PostToolUseFailure": ("Bash", 10), "Stop": ("", 30)}
"""Event: (matcher, timeout). hooks.py's own literal WIRING wins when it has one."""

HOOK_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR"/.doctrine/hooks.py'

def wire_hooks(root: Path, write: bool = True) -> bool:
    """Merge hooks.py into .claude/settings.json, one entry per event. Other keys and hooks
    stay; an earlier doctrine-map entry is replaced. Returns True when the file changed (or,
    with write=False, would change). Raises UsageError on a settings file it cannot read."""
    path = root / ".claude" / "settings.json"
    old = read_text(path) or ""
    wiring = read_literal(root / ".doctrine" / "hooks.py", "WIRING") or read_literal(HERE / "hooks.py", "WIRING")
    try:
        settings = json.loads(old) if old.strip() else {}
        hooks = settings.setdefault("hooks", {})
        for event, (matcher, timeout) in (wiring if isinstance(wiring, dict) else WIRING).items():
            groups = []
            for group in hooks.get(event, []):
                kept = [h for h in group.get("hooks", []) if ".doctrine/hooks.py" not in str(h.get("command", ""))]
                if kept:
                    groups.append({**group, "hooks": kept})
            ours = {"hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": timeout}]}
            hooks[event] = groups + [{"matcher": matcher, **ours} if matcher else ours]
    except (ValueError, AttributeError, TypeError) as exc:
        raise UsageError(f".claude/settings.json is not a settings object ({exc}); fix it and run again") from None
    new = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    if new != old and write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
    return new != old


# =========================================================================== 6. commands

def cmd_build(args: argparse.Namespace) -> int:
    repo = open_repo(args.doctrine)
    outs = outputs(repo, rulesync=args.export == "rulesync" or exported(repo.root))
    changed = write_outputs(repo, outs)
    repo.files = repo_files(repo.root)
    graph, _ = build_graph(repo)
    write_graph(repo, graph)
    unchanged = len(outs) - len([c for c in changed if not c.endswith("(removed)")])
    print(f"Built {repo.doctrine.name} {repo.doctrine.version} from {repo.source}: {len(changed)} written, "
          f"{unchanged} unchanged.")
    for path in changed:
        print(f"  {path}")
    print(f"Graph: .doctrine/graph.json ({len(graph['gaps'])} gaps). Next: python3 doctrine.py check")
    return 0

def principle_line(p: dict, routes: list[str]) -> str:
    """What makes a principle hold: its enforcers, and the live routes that carry it."""
    held = [e["ref"] + (" (missing)" if e["status"] == "missing" else "") for e in p["enforcers"]]
    return ", ".join(held + (["routes " + ", ".join(routes)] if routes else [])) or "words only"

def cmd_check(args: argparse.Namespace) -> int:
    repo = open_repo(args.doctrine)
    graph, notes = build_graph(repo, drift(repo, outputs(repo, rulesync=exported(repo.root))))
    d, cov = repo.doctrine, graph["coverage"]
    principles = [n for n in graph["nodes"] if n["kind"] == "principle"]
    places = [n for n in graph["nodes"] if n["kind"] == "place" and "/" not in n["path"]]
    types = {n["ref"]: n["type"] for n in graph["nodes"] if n["kind"] == "enforcer"}
    live = {n["name"] for n in graph["nodes"] if n["kind"] == "route" and n["matches"]}
    errors = [g for g in graph["gaps"] if g["kind"] in ("missing_enforcer", "stale_projection", "over_budget", "missing_skill", "missing_guide")]
    warnings = [g for g in graph["gaps"] if g["kind"] in ("dead_route", "unrouted_sensitive")]
    warnings += [{"kind": "link", "detail": note} for note in notes]
    warnings += [{"kind": "level", "id": p["id"], "detail": f"{p['id']} declares {p['declared']} but holds at {p['effective']}."}
                 for p in principles if LEVEL_RANK[p["declared"]] < LEVEL_RANK[p["effective"]]
                 and all(e["status"] == "present" for e in p["enforcers"])]
    if not hooks_wired(repo.settings) and any(types.get(e["ref"]) in ("hook", "stop") and e["status"] == "present"
                                              for p in principles for e in p["enforcers"]):
        warnings.append({"kind": "hooks_unwired", "detail": "hooks.py is not run by .claude/settings.json, so its "
                         "checks receive no enforcement credit; init wires it. Global plugin settings are not inspected."})
    table = {pl["path"]: {p["id"]: tier(p, types, p["id"] in pl["principles"] or any(
        e["ref"] in pl["routes"] and e["status"] == "present" for e in p["enforcers"])) for p in principles}
        for pl in places}
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings, "coverage": cov,
                          "entry": {k: graph["entry"][k] for k in ("budget", "used")},
                          "principles": {p["id"]: {k: p[k] for k in ("declared", "effective", "enforcers")}
                                         for p in principles}, "places": table}, indent=2, ensure_ascii=False))
        return 1 if errors else 0
    width = max([len(p["id"]) for p in principles] + [3])
    print(f"doctrine.py check: {d.name} {d.version} ({repo.source}), {cov['files_total']} files\n")
    print("Principles: effective level, declared level, and what makes each hold")
    for p in principles:
        routes = [rid for rid in d.routes if rid in live and p["id"] in d.routes[rid].principles]
        print(f"  {p['id']:<{width}}  {p['effective']:<6}  declared {p['declared']:<6}  {principle_line(p, routes)}")
    if places:
        label, mark = min(max(len(pl["name"]) for pl in places), 28), {"enforced": "E", "reminded": "R", "words": "."}
        print("\nCoverage by place: E enforced (a hook or check stops or fails it), R reminded (text reaches the "
              "agent), . words only")
        print("  " + " " * label + "".join(f" {p['id']:>{width}}" for p in principles))
        for pl in places:
            print(f"  {pl['name'][:label]:<{label}}" + "".join(f" {mark[table[pl['path']][p['id']]]:>{width}}"
                                                              for p in principles))
    levels = ", ".join(f"{level} {count}" for level, count in cov["by_level"].items())
    print(f"\n{cov['enforced_beyond_words']} of {cov['principles']} principles enforced beyond words ({levels}).")
    print(f"Files governed by a route: {cov['files_governed']} of {cov['files_total']}. Routes: {cov['routes_live']} "
          f"live, {cov['routes_dead']} dead. Entry card: {graph['entry']['used']} of {graph['entry']['budget']} lines.")
    for title, items in (("Warnings", warnings), ("Errors", errors)):
        if items:
            print(f"\n{title}")
            for g in items:
                print(f"  {g['kind']:<18} {g.get('path') or g.get('id') or '':<24} {g['detail']}")
    plural = lambda n, word: f"{n} {word}" + ("s" if n != 1 else "")  # noqa: E731
    verdict = f"check failed: {plural(len(errors), 'error')}" if errors else "check passed"
    print("\nScope: declared repository configuration. Task completeness, undeclared requirements "
          "and live hook execution are not evaluated.")
    print(f"\n{verdict}, {plural(len(warnings), 'warning')}.")
    return 1 if errors else 0

def cmd_explain(args: argparse.Namespace) -> int:
    repo = open_repo(args.doctrine)
    given = Path(args.path)
    if given.is_absolute():
        rel = relative_to_root(given, repo.root)
    else:  # relative to here when it exists here (or nowhere), else to the repository root
        here = relative_to_root(Path.cwd() / given, repo.root)
        exists_here = (Path.cwd() / given).exists() or not (repo.root / given).exists()
        rel = here if here is not None and exists_here else normalise(args.path)
    if rel is None:
        raise UsageError(f"{args.path} lies outside the repository this doctrine governs")
    graph, _ = build_graph(repo)
    d, entry = repo.doctrine, graph["entry"]
    principles = {n["id"]: n for n in graph["nodes"] if n["kind"] == "principle"}
    types = {n["ref"]: n["type"] for n in graph["nodes"] if n["kind"] == "enforcer"}
    routes = d.routes_for(rel)
    reach = {"route:" + r.id for r in routes}
    local = [pid for pid, p in principles.items() if any(pid in r.principles for r in routes)
             or any(e["ref"] in reach and e["status"] == "present" for e in p["enforcers"])]
    wrap = lambda text: textwrap.fill(text, 100, initial_indent="     ", subsequent_indent="     ")  # noqa: E731
    print(f"{rel}\n")
    policy_source, roles = layout_roles(repo)
    declared, role = purpose_for(rel, roles)
    if role:
        print(f"Purpose: {role['purpose']} (declared at {policy_source}: {declared})")
        if role.get('guide'):
            print(f"Owner guide: {role['guide']}")
    elif policy_source:
        print(f"Purpose not declared; extend {policy_source} for an ordinary custom folder.")
    print(f"1. On arrival, every agent reads the entry card in AGENTS.md (CLAUDE.md imports it), "
          f"{entry['used']} of {entry['budget']} lines:")
    for line in entry["lines"]:
        print(f"   {line}" if line else "")
    print("\n2. Routes that match this path:" if routes else
          "\n2. No route matches this path, so nothing beyond the entry card is delivered here.")
    for r in routes:
        print(f"   {r.id}: rule file .claude/rules/doctrine-{r.id}.md; hook reminder on {', '.join(r.on)}")
        print(wrap(r.reminder))
        for ref in skill_details(repo, r):
            print(wrap(f"Workflow [{ref['status']}]: {ref['path']} — {ref['when']} (guidance, not execution)"))
    if local:
        print("\n3. Principles delivered here, and how each holds:")
    for pid in local:
        p = principles[pid]
        declared = "" if p["declared"] == p["effective"] else f", declared {p['declared']}"
        how = principle_line(p, [r.id for r in routes if pid in r.principles])
        print(f"   {pid} {p['name']}: {tier(p, types, True)} ({p['effective']}{declared}; {how})")
        print(wrap(p["one"]))
        print(wrap(p["three"]))
    rest = {pid: tier(p, types, False) for pid, p in principles.items() if pid not in local}
    print("\n4. Everywhere else in the doctrine:")
    for name, label in (("enforced", "Enforced by hooks and checks"), ("reminded", "Reminded or advised by hooks"),
                        ("words", "Words only (the entry card)")):
        held = [pid if name == "words" else f"{pid} {principles[pid]['effective']}" for pid, t in rest.items() if t == name]
        if held:
            print(f"   {label}: {', '.join(held)}.")
    return 0

def trim_routes(text: str, files: list[str]) -> tuple[str, list[str], list[str]]:
    """Drop the [[route]] blocks that match none of `files`, keeping comments and layout. A
    principle that named a dropped route as its enforcer loses that ref, and falls back to
    prose when no live route still carries it. Returns (text, kept, dropped)."""
    doctrine = from_dict(tomllib.loads(text))
    dead = [rid for rid, r in doctrine.routes.items() if not any(r.matches(f) for f in files)]
    carried = {pid for rid, r in doctrine.routes.items() if rid not in dead for pid in r.principles}
    chunks: list[list[str]] = [[]]
    for line in text.splitlines(keepends=True):
        if re.match(r"\s*\[\[?[\w.-]+\]\]?\s*(#.*)?$", line) and chunks[-1]:
            chunks.append([])
        chunks[-1].append(line)
    out = []
    for chunk in chunks:
        table = chunk[0].strip()
        ident = next((m.group(1) for line in chunk if (m := re.match(r'\s*id\s*=\s*"([^"]*)"', line))), "")
        if table == "[[route]]" and ident in dead:
            continue
        if table == "[[route]]":
            start = next((i for i, line in enumerate(chunk) if re.match(r'\s*skills\s*=', line)), None)
            if start is not None:
                for end in range(start + 1, len(chunk) + 1):
                    try:
                        refs = tomllib.loads(''.join(chunk[start:end]))['skills']
                    except tomllib.TOMLDecodeError:
                        continue
                    kept_refs = [r for r in refs if r['path'] in files]
                    encoded = ', '.join('{ path = ' + json.dumps(r['path']) + ', when = ' + json.dumps(r['when']) + ' }' for r in kept_refs)
                    chunk[start:end] = ['skills = [' + encoded + ']\n']
                    break
        for i, line in enumerate(chunk if table == "[[principle]]" else []):
            m = re.match(r"(\s*enforced_by\s*=\s*)\[(.*)\]\s*$", line)
            refs = re.findall(r'"([^"]*)"', m.group(2)) if m else []
            keep = [r for r in refs if not (r.startswith("route:") and r[6:] in dead)]
            if keep != refs:
                chunk[i] = m.group(1) + "[" + ", ".join(json.dumps(r) for r in keep) + "]\n"
                if not keep and ident not in carried:
                    gone = ", ".join(r[6:] for r in refs)
                    chunk[:] = [re.sub(r'^(\s*enforcement\s*=\s*)"(\w+)".*$',
                                       rf'\1"prose"  # was "\2"; route {gone} matches no file here', x) for x in chunk]
        out.extend(chunk)
    new = "".join(out)
    from_dict(tomllib.loads(new))
    return new, [rid for rid in doctrine.routes if rid not in dead], dead

def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    if not target.is_dir():
        raise UsageError(f"{args.target} is not a directory")
    dest = target / ".doctrine"
    if ((target / "doctrine.toml").exists() or (dest / "doctrine.toml").exists()) and not args.force:
        raise UsageError("this repository already has a doctrine; edit it, or pass --force to replace it")
    wire_hooks(target, write=False)  # refuse a broken settings file before writing anything
    reference = Path(args.reference) if args.reference else HERE / "doctrine.toml"
    planned = [".doctrine/doctrine.toml", ".doctrine/doctrine.py", ".doctrine/hooks.py", "AGENTS.md", "CLAUDE.md",
               ".claude/settings.json"]
    text, kept, dropped = trim_routes(reference.read_text(encoding="utf-8"), repo_files(target) + planned)
    dest.mkdir(exist_ok=True)
    (dest / "doctrine.toml").write_text(text, encoding="utf-8")
    copied = []
    for name in ("safety.py", "doctrine.py", "hooks.py"):
        if (HERE / name).exists() and (HERE / name).resolve() != (dest / name).resolve():
            shutil.copyfile(HERE / name, dest / name)
            copied.append(f".doctrine/{name}")
    viewer = next((p for p in (HERE / "viewer" / "map.html", HERE / "map.html") if p.is_file()), None)
    if viewer is not None and viewer.resolve() != (dest / "map.html").resolve():
        shutil.copyfile(viewer, dest / "map.html")
        copied.append(".doctrine/map.html")
    wired = (dest / "hooks.py").exists() and wire_hooks(target)
    repo = open_repo(dest / "doctrine.toml")
    changed = write_outputs(repo, outputs(repo))
    repo.files = repo_files(repo.root)
    write_graph(repo, build_graph(repo)[0])
    print(f"Adopted {repo.doctrine.name} {repo.doctrine.version} in {target.name}/.")
    print(f"  routes kept: {', '.join(kept) or 'none'}")
    print(f"  routes dropped (no matching files): {', '.join(dropped) or 'none'}")
    print(f"  copied: {', '.join(copied) or 'nothing'}; wrote: {', '.join(changed) or 'nothing'}")
    print("  hooks: " + ("wired in .claude/settings.json" if wired else "already wired" if hooks_wired(repo.settings)
                         else "not wired (hooks.py not found)"))
    command = "safety.py" if (dest / "safety.py").exists() else "doctrine.py"
    print(f"Next: python3 .doctrine/{command} check, then explain <path> and map --serve")
    return 0

def find_viewer(root: Path) -> Path | None:
    return next((p for p in (root / ".doctrine" / "map.html", HERE / "viewer" / "map.html", HERE / "map.html") if p.is_file()), None)

GRAPH_TAG = re.compile(r'(<script\b[^>]*\bid="doctrine-graph"[^>]*>)(.*?)(</script>)', re.S | re.I)

def inject(html: str, graph: dict) -> str:
    """The viewer with the graph inside its doctrine-graph script tag: one file, no server."""
    data = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c")
    if GRAPH_TAG.search(html):
        return GRAPH_TAG.sub(lambda m: m.group(1) + data + m.group(3), html, count=1)
    at = html.lower().find("</head>")
    tag = f'<script id="doctrine-graph" type="application/json">{data}</script>\n'
    return html[:at] + tag + html[at:] if at >= 0 else tag + html

class Live:
    """The map server's state: the latest graph, and a condition that wakes /events streams."""

    def __init__(self, doctrine_path: Path, interval: float = 1.0):
        self.path, self.interval, self.cond = doctrine_path, interval, threading.Condition()
        self.version, self.stamp, self.body, self.sig, self.error, self.closed = 0, "", b"{}", None, "", False

    def signature(self) -> tuple:
        """What the graph depends on: the doctrine, the file list, hooks, settings and projections."""
        root = repo_root(self.path)
        files = repo_files(root)
        watched = [root / ".claude/settings.json", root / ".doctrine/hooks.py", HERE / "hooks.py",
                   root / "AGENTS.md", root / "CLAUDE.md"]
        watched += [root / f for f in files if f.startswith((".claude/rules/", ".rulesync/rules/"))]
        d = load(self.path)
        watched += [root / path for path in ((d.layout_policy,) if d.layout_policy else DEFAULT_LAYOUT_POLICIES)]
        watched += [root / ref.path for route in d.routes.values() for ref in route.skills]
        stats = [(str(p), p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else (str(p),) for p in watched]
        return hashlib.sha256(self.path.read_bytes()).hexdigest(), "\0".join(files), tuple(stats)

    def rebuild(self) -> None:
        sig, repo = self.signature(), open_repo(self.path)
        graph, _ = build_graph(repo, drift(repo, outputs(repo, rulesync=exported(repo.root))))
        with self.cond:
            self.sig, self.stamp, self.body = sig, graph["generated_at"], json.dumps(graph, ensure_ascii=False).encode()
            self.version += 1
            self.cond.notify_all()

    def watch(self) -> None:
        """Poll about once a second; rebuild and wake the streams when anything changed."""
        while not self.closed:
            time.sleep(self.interval)
            if self.closed:
                return
            try:
                if self.signature() != self.sig:
                    self.rebuild()
                    self.error = ""
            except (OSError, ValueError) as exc:
                if str(exc) != self.error:
                    self.error = str(exc)
                    print(f"doctrine.py map: keeping the last good graph: {exc}", file=sys.stderr)

    def close(self) -> None:
        with self.cond:
            self.closed = True
            self.cond.notify_all()

def make_server(doctrine_path: Path, port: int = 7878, interval: float = 1.0) -> http.server.ThreadingHTTPServer:
    """A local map server on 127.0.0.1: the viewer at /, /graph.json, and /events (server-sent events)."""
    live = Live(Path(doctrine_path).resolve(), interval)
    live.rebuild()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def send(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            route = self.path.split("?", 1)[0]
            viewer = find_viewer(repo_root(live.path))
            if route in ("/", "/index.html", "/map.html") and viewer:
                self.send(200, viewer.read_bytes(), "text/html; charset=utf-8")
            elif route == "/graph.json":
                with live.cond:
                    body = live.body
                self.send(200, body, "application/json")
            elif route == "/events":
                self.stream()
            else:
                self.send(404, b"not found", "text/plain; charset=utf-8")

        def stream(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            seen = live.version
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while not live.closed:
                    with live.cond:
                        live.cond.wait_for(lambda: live.version != seen or live.closed, timeout=15)
                        version, stamp = live.version, live.stamp
                    message = f"data: {json.dumps({'rebuilt': stamp})}\n\n" if version != seen else ": still here\n\n"
                    seen = version
                    self.wfile.write(message.encode())
                    self.wfile.flush()
            except OSError:
                pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.live = live  # type: ignore[attr-defined]
    threading.Thread(target=live.watch, daemon=True).start()
    return server

def cmd_map(args: argparse.Namespace) -> int:
    repo = open_repo(args.doctrine)
    viewer = find_viewer(repo.root)
    if viewer is None:
        raise UsageError("map.html was not found in viewer/, beside doctrine.py or in .doctrine/")
    if args.serve:
        server = make_server(repo.doctrine.path, args.port)
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        print(f"Serving the map at {url}; it redraws when doctrine.toml or the repository changes. Ctrl+C stops "
              "it.", flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.live.close()  # type: ignore[attr-defined]
            server.server_close()
        return 0
    graph, _ = build_graph(repo, drift(repo, outputs(repo, rulesync=exported(repo.root))))
    out = Path(args.out or "doctrine-map.html")
    out.write_text(inject(viewer.read_text(encoding="utf-8"), graph), encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size:,} bytes). Open it in a browser; it needs no server.")
    return 0

def cmd_log_error(args: argparse.Namespace) -> int:
    repo = open_repo(args.doctrine)
    unknown = [pid for pid in args.principle if pid not in repo.doctrine.principles]
    if unknown:
        raise UsageError(f"unknown principle {', '.join(unknown)}; this doctrine has {', '.join(repo.doctrine.principles)}")
    record = {"time": now(), "what": args.what, "principles": args.principle, "lesson": args.lesson}
    if os.environ.get("CLAUDE_SESSION_ID"):
        record["session"] = os.environ["CLAUDE_SESSION_ID"]
    ensure_gitignore(repo.root)
    with (repo.root / ".doctrine" / "mistakes.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Logged in .doctrine/mistakes.jsonl. Lesson: {args.lesson}")
    return 0


# =========================================================================== 7. command line

def main(argv: list[str] | None = None, *, prog: str = "doctrine.py") -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--doctrine", help="doctrine file (default: the nearest doctrine.toml or .doctrine/doctrine.toml)")
    parser = argparse.ArgumentParser(prog=prog, description="Safety Core: set up, tailor and inspect the rules for your project.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", parents=[common], help="set up the starting rules in your project")
    p.add_argument("--target", default=".", help="repository to set up (default: here)")
    p.add_argument("--from", dest="reference", help="doctrine to adopt (default: doctrine.toml beside this file)")
    p.add_argument("--force", action="store_true", help="replace an existing doctrine")
    p = sub.add_parser("build", parents=[common], help="write AGENTS.md, CLAUDE.md, .claude/rules and the graph")
    p.add_argument("--export", choices=["rulesync"], help="also write .rulesync/rules/ for rulesync's agents")
    p = sub.add_parser("check", parents=[common], help="links, drift and coverage; exit 1 on errors")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p = sub.add_parser("explain", parents=[common], help="what an agent receives at a path")
    p.add_argument("path")
    p = sub.add_parser("map", parents=[common], help="write the map as one HTML file, or serve it live")
    p.add_argument("--out", help="output file (default: doctrine-map.html)")
    p.add_argument("--serve", action="store_true", help="serve a live map that redraws as you edit")
    p.add_argument("--port", type=int, default=7878)
    p.add_argument("--open", action="store_true", help="open the map in a browser")
    p = sub.add_parser("log-error", parents=[common], help="record a mistake and the lesson it teaches")
    p.add_argument("what", help="what happened")
    p.add_argument("--principle", action="append", default=[], help="principle it broke (repeatable)")
    p.add_argument("--lesson", required=True, help="the rule learned")
    args = parser.parse_args(argv)
    commands = {"init": cmd_init, "build": cmd_build, "check": cmd_check, "explain": cmd_explain,
                "map": cmd_map, "log-error": cmd_log_error}
    try:
        return commands[args.command](args)
    except DoctrineError as exc:
        print("The doctrine has problems:\n  " + "\n  ".join(exc.problems), file=sys.stderr)
    except (UsageError, tomllib.TOMLDecodeError, OSError) as exc:
        print(f"doctrine.py {args.command}: {exc}", file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main())
