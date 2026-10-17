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

from common import detect_default_branch, experimental_enabled, matches, read_list
from reviewers import parse, render_codeowners

KIT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "kit/manifest.json"
BRANCH_RULES = "kit/templates/branch-rules.txt"
SCANNER_EXCLUDES = "kit/templates/scanner-excludes.txt"
PLUGIN_SETTINGS = "kit/templates/plugin-settings.txt"
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


def stamped(target: Path, today: str) -> tuple[str, str]:
    """(installed date, default branch): reused from an install, else today and detected."""
    date, branch = None, None
    for rel, getter in (
        ("agk.toml", lambda d: d),
        ("pyproject.toml", lambda d: d.get("tool", {}).get("agk", {})),
    ):
        path = target / rel
        if not path.is_file():
            continue
        try:
            section = getter(tomllib.loads(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            continue
        value = section.get("installed")
        if date is None and isinstance(value, str) and DATE_RE.match(value):
            date = value
        value = section.get("default_branch")
        if branch is None and isinstance(value, str) and value:
            branch = value
    return date or today, branch or detect_default_branch(target) or "main"


def install_mode(target: Path) -> str | None:
    """ "init" or "adopt" when TARGET already carries an agk install, else None.

    Reads the stamp as text (agk.toml `mode`, or a `[tool.agk]` table of an earlier install).
    """
    path = target / "agk.toml"
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        match = re.search(r'(?m)^mode\s*=\s*"(\w+)"', text)
        if match:
            return match.group(1)
    pyproject = target / "pyproject.toml"
    if pyproject.is_file():
        try:
            if re.search(r"(?m)^\[tool\.agk\]", pyproject.read_text(encoding="utf-8")):
                return "init"
        except (OSError, UnicodeDecodeError):
            return None
    return None


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


def build_items(target: Path, today: str) -> tuple[list[tuple[str, bytes]], list[str], str]:
    """Every file init manages as (relative path, content), protected entries, default branch."""
    manifest = json.loads((KIT_ROOT / MANIFEST).read_text(encoding="utf-8"))
    date, branch = stamped(target, today)
    variables = {
        "project": slug(target.name),
        "date": date,
        "kit_version": manifest["kit_version"],
        "default_branch": branch,
    }
    items: dict[str, bytes] = {}
    extra = manifest.get("experimental", []) if experimental_enabled(target) else []
    for rel in [*manifest["verbatim"], *extra]:
        items[rel] = (KIT_ROOT / rel).read_bytes()
    for dest, src in manifest["templates"].items():
        text = (KIT_ROOT / src).read_text(encoding="utf-8")
        items[dest] = render(text, variables, src).encode("utf-8")
    codeowners = render_codeowners(parse(items["config/reviewers.yaml"].decode("utf-8")))
    items[".github/CODEOWNERS"] = codeowners.encode("utf-8")
    entries = read_list(items["config/protected-paths.txt"].decode("utf-8"))
    return sorted(items.items()), entries, branch


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


ISSUES_NOTICE = (
    "notice: the workflows drift-audit.yml, metrics.yml and product-report.yml write GitHub "
    "issues with the workflow token (`issues: write`); delete a workflow file if the repository "
    "must not allow that."
)


def plugin_settings() -> str:
    """The print-only settings entries for the plugin, at this kit's version."""
    manifest = json.loads((KIT_ROOT / MANIFEST).read_text(encoding="utf-8"))
    text = (KIT_ROOT / PLUGIN_SETTINGS).read_text(encoding="utf-8").rstrip()
    return text.replace("{{kit_version}}", manifest["kit_version"])


def print_branch_rules(branch: str, tool: str = "init") -> None:
    print(f"Apply by hand on GitHub to the default branch `{branch}` ({tool} configures nothing):")
    print((KIT_ROOT / BRANCH_RULES).read_text(encoding="utf-8").rstrip())
    print()
    print((KIT_ROOT / SCANNER_EXCLUDES).read_text(encoding="utf-8").rstrip())
    print()
    print(plugin_settings())
    print()
    print(ISSUES_NOTICE)


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
        if install_mode(target) == "adopt":
            raise Refusal("TARGET was installed by adopt (path class agk.toml); init refuses")
        items, entries, branch = build_items(target, datetime.now(UTC).date().isoformat())
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
        print_branch_rules(branch)
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
    print_branch_rules(branch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
