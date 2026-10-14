"""agk init: install the kit into an empty repository (SPEC-0001).

Usage: python3 scripts/agk/init.py TARGET [--dry-run]

Standard library only. No network, no git or gh calls, no writes outside TARGET. Reads only
kit/manifest.json (and what it lists) from the kit checkout this script lives in. Refuses
(exit 1) rather than overwrite; nothing is written when any file conflicts.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from common import matches, read_list
from reviewers import parse, render_codeowners

KIT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "kit/manifest.json"
BRANCH_RULES = "kit/templates/branch-rules.txt"
PLACEHOLDER = "@REPLACE-ME"
MIN_PYTHON = (3, 11)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VAR_RE = re.compile(r"\{\{(\w+)\}\}")


class Refusal(Exception):
    """Exit 1: nothing is written."""


def check_interpreter(version: tuple[int, ...]) -> str | None:
    if tuple(version[:2]) < MIN_PYTHON:
        return "Python 3.11 or newer is required (path class scripts/agk/: the checks use tomllib)"
    return None


def slug(name: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return out or "project"


def stamped_date(target: Path, today: str) -> str:
    """The `installed` date of an existing pyproject.toml, else today (UTC)."""
    path = target / "pyproject.toml"
    if path.is_file():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            return today
        value = data.get("tool", {}).get("agk", {}).get("installed")
        if isinstance(value, str) and DATE_RE.match(value):
            return value
    return today


def render(text: str, variables: dict[str, str], source: str) -> str:
    def sub(match: re.Match) -> str:
        name = match.group(1)
        if name not in variables:
            raise Refusal(f"template {source} uses an unknown variable")
        return variables[name]

    return VAR_RE.sub(sub, text)


def path_class(rel: str, entries: list[str]) -> str:
    for entry in entries:
        if matches(rel, entry):
            return entry
    return rel.split("/", 1)[0] + "/" if "/" in rel else "(repository root)"


def build_items(target: Path, today: str) -> tuple[list[tuple[str, bytes]], list[str]]:
    """Every file init manages as (relative path, content), and the installed protected entries."""
    manifest = json.loads((KIT_ROOT / MANIFEST).read_text(encoding="utf-8"))
    variables = {
        "project": slug(target.name),
        "date": stamped_date(target, today),
        "kit_version": manifest["kit_version"],
    }
    items: dict[str, bytes] = {}
    for rel in manifest["verbatim"]:
        items[rel] = (KIT_ROOT / rel).read_bytes()
    for dest, src in manifest["templates"].items():
        text = (KIT_ROOT / src).read_text(encoding="utf-8")
        items[dest] = render(text, variables, src).encode("utf-8")
    codeowners = render_codeowners(parse(items["config/reviewers.yaml"].decode("utf-8")))
    items[".github/CODEOWNERS"] = codeowners.encode("utf-8")
    entries = read_list(items["config/protected-paths.txt"].decode("utf-8"))
    return sorted(items.items()), entries


def passes_symlink(target: Path, rel: str) -> bool:
    current = target
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def classify(target: Path, items: list[tuple[str, bytes]], entries: list[str]):
    """Plan entries: (relative path, action, content, detail)."""
    plan: list[tuple[str, str, bytes, str]] = []
    for rel, content in items:
        path = target / rel
        cls = path_class(rel, entries)
        if passes_symlink(target, rel):
            plan.append((rel, "conflict", content, f" (path class {cls}: symlink)"))
        elif not path.exists():
            plan.append((rel, "create", content, ""))
        elif path.is_file() and path.read_bytes() == content:
            plan.append((rel, "unchanged", content, ""))
        else:
            plan.append((rel, "conflict", content, f" (path class {cls}: differs)"))
    return plan


def print_branch_rules() -> None:
    print("Apply by hand on GitHub (init configures nothing):")
    print((KIT_ROOT / BRANCH_RULES).read_text(encoding="utf-8").rstrip())


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    dry_run = "--dry-run" in args
    rest = [a for a in args if a != "--dry-run"]
    if len(rest) != 1 or rest[0].startswith("-"):
        print("usage: init.py TARGET [--dry-run]", file=sys.stderr)
        return 2
    try:
        problem = check_interpreter(tuple(sys.version_info[:3]))
        if problem:
            raise Refusal(problem)
        target = Path(rest[0])
        if not target.is_dir():
            raise Refusal("TARGET is not an existing directory (path class: the target root)")
        target = target.resolve()
        if target == KIT_ROOT or KIT_ROOT in target.parents:
            raise Refusal("TARGET is the kit checkout or inside it (path class kit/)")
        items, entries = build_items(target, datetime.now(UTC).date().isoformat())
        plan = classify(target, items, entries)
    except Refusal as exc:
        print(f"refused: {exc}")
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: cannot read the kit sources ({type(exc).__name__})")
        return 3

    for rel, action, _, detail in plan:
        print(f"{action} {rel}{detail}")
    if any(action == "conflict" for _, action, _, _ in plan):
        print("refused: existing files differ; nothing was written (merging is `agk adopt`)")
        print_branch_rules()
        return 1

    created = [(rel, content) for rel, action, content, _ in plan if action == "create"]
    if dry_run:
        print(f"dry run: {len(created)} files would be created; nothing was written")
    else:
        for rel, content in created:
            path = target / rel
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            except OSError:
                print(f"error: cannot write {rel} (path class {path_class(rel, entries)})")
                return 3
        print(f"installed {len(created)} files" if created else "nothing to do")
    if not (target / ".git").exists():
        print("notice: TARGET is not a git work tree; the checks need git")
    if PLACEHOLDER in dict(items)["config/reviewers.yaml"].decode("utf-8"):
        print(f"notice: config/reviewers.yaml maps `maintainers` to the placeholder {PLACEHOLDER}")
    print_branch_rules()
    return 0


if __name__ == "__main__":
    sys.exit(main())
