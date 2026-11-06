"""Parity: every discipline of the kit reaches a project (brief 680, ADR-0326).

    python3 parity.py report [--root DIR]
    python3 parity.py check [--root DIR]

A kit discipline is each `scripts/agk/*.py`, each `.claude/agents/*.md`, each file directly under
`config/` and each `docs/runs/` log that an agent file names (a placeholder `N`, `<n>` or `<...>`
read as `*`). A project gets it `installed` (kit/manifest.json), through the `plugin` (a
`skills/*/SKILL.md` runs it from `${CLAUDE_PLUGIN_ROOT}`, or a script the plugin runs imports it)
or not at all, `kit-only (<reason>)`, as a line `<path> <reason>` of `config/kit-only.txt` says.

`report` prints one line per discipline, sorted. `check` exits 1 naming each discipline in none
of the three and each line of the list that is stale, unreasoned, repeated or names nothing. A
tree without `kit/manifest.json` (an installed project) has nothing to check. No network.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

MANIFEST = "kit/manifest.json"
KIT_ONLY = "config/kit-only.txt"
NO_MANIFEST = "parity: no kit/manifest.json; nothing to check"
USAGE = "usage: parity.py report|check [--root DIR]"
LOG = re.compile(r"docs/runs/[A-Za-z0-9_.<>*-]+\.[a-z]+")
PLACEHOLDER = re.compile(r"<[^<>/]*>|(?<![A-Za-z0-9])N(?![A-Za-z0-9])")
PLUGIN_RUN = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?/(scripts/agk/[A-Za-z0-9_]+\.py)")


def read_kit_only(path: Path) -> list[tuple[str, str]]:
    """The lines `<path> <reason>` of the exception list, in order (comments and blanks skipped)."""
    if not path.is_file():
        return []
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, _, reason = line.partition(" ")
        entries.append((name, reason.strip()))
    return entries


def log_pattern(token: str) -> str:
    return PLACEHOLDER.sub("*", token)


def disciplines(root: Path) -> list[str]:
    found = {p.relative_to(root).as_posix() for p in (root / "scripts" / "agk").glob("*.py")}
    found |= {p.relative_to(root).as_posix() for p in (root / ".claude" / "agents").glob("*.md")}
    config = root / "config"
    if config.is_dir():
        found |= {p.relative_to(root).as_posix() for p in config.iterdir() if p.is_file()}
    for agent in (root / ".claude" / "agents").glob("*.md"):
        for token in LOG.findall(agent.read_text(encoding="utf-8")):
            found.add(log_pattern(token))
    return sorted(found)


def installed_paths(manifest: dict) -> set[str]:
    paths: set[str] = set()
    for key in ("verbatim", "experimental", "rendered"):
        paths |= set(manifest.get(key) or [])
    paths |= set(manifest.get("templates") or {})
    paths |= set((manifest.get("adopt") or {}).get("templates") or {})
    return paths


def imports_of(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def plugin_paths(root: Path) -> set[str]:
    """Scripts a skill runs from the plugin root, and the kit modules they import, transitively."""
    todo = []
    for skill in sorted((root / "skills").glob("*/SKILL.md")):
        todo += PLUGIN_RUN.findall(skill.read_text(encoding="utf-8"))
    seen: set[str] = set()
    while todo:
        rel = todo.pop()
        if rel in seen or not (root / rel).is_file():
            continue
        seen.add(rel)
        for name in imports_of(root / rel):
            module = f"scripts/agk/{name}.py"
            if (root / module).is_file():
                todo.append(module)
    return seen


def is_installed(path: str, installed: set[str], root: Path) -> bool:
    if path in installed:
        return True
    if "*" not in path:
        return False
    stem = path.split("*", 1)[0]
    for rel in sorted(installed):
        if not rel.endswith(".py") or not (root / rel).is_file():
            continue
        if stem in (root / rel).read_text(encoding="utf-8"):
            return True
    return False


def classify(root: Path) -> tuple[dict[str, str], list[str]]:
    """({discipline: how}, problems); `how` is installed, plugin, kit-only (...) or none."""
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    installed = installed_paths(manifest)
    plugin = plugin_paths(root)
    entries = read_kit_only(root / KIT_ONLY)
    reasons: dict[str, str] = {}
    problems: list[str] = []
    for name, reason in entries:
        if name in reasons:
            problems.append(f"{name} is listed twice in {KIT_ONLY}: keep one line")
            continue
        reasons[name] = reason
    found = disciplines(root)
    how: dict[str, str] = {}
    for path in found:
        if is_installed(path, installed, root):
            how[path] = "installed"
        elif path in plugin:
            how[path] = "plugin"
        elif path in reasons and reasons[path]:
            how[path] = f"kit-only ({reasons[path]})"
        else:
            how[path] = "none"
    for name, reason in reasons.items():
        if name not in how:
            problems.append(f"{name} names no kit discipline: remove its line from {KIT_ONLY}")
        elif not reason:
            problems.append(f"{name} has no reason in {KIT_ONLY}: add one after the path")
        elif how[name] == "installed":
            problems.append(f"{name} is installed: remove its line from {KIT_ONLY}")
        elif how[name] == "plugin":
            problems.append(
                f"{name} reaches a project through the plugin: remove its line from {KIT_ONLY}"
            )
    for path in found:
        if how[path] == "none" and not (path in reasons and not reasons[path]):
            problems.append(
                f"{path} reaches no project: install it (kit/manifest.json), run it from a "
                f"skill, or list it with its reason in {KIT_ONLY}"
            )
    return how, problems


def main(argv: list[str]) -> int:
    args = list(argv)
    root = Path.cwd()
    if "--root" in args:
        at = args.index("--root")
        if at + 1 >= len(args):
            print(USAGE, file=sys.stderr)
            return 2
        root = Path(args[at + 1])
        del args[at : at + 2]
    if len(args) != 1 or args[0] not in ("report", "check"):
        print(USAGE, file=sys.stderr)
        return 2
    if not (root / MANIFEST).is_file():
        print(NO_MANIFEST)
        return 0
    how, problems = classify(root)
    if args[0] == "report":
        for path in sorted(how):
            print(f"{path} {how[path]}")
        return 0
    for line in problems:
        print(line)
    if problems:
        return 1
    kit_only = sum(1 for value in how.values() if value.startswith("kit-only"))
    reach = len(how) - kit_only
    print(f"parity: {len(how)} disciplines; {reach} reach a project, {kit_only} kit-only")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
