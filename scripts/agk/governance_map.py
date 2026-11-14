"""The governance checks a set of changed paths needs (brief #1254, ADR-0531).

Read by `.claude/hooks/stop_check.py`. Installed: a verbatim entry of `kit/manifest.json`.

`CHECKS` holds the commands of the `agk-governance` recipe of `agk.mk`, in its order (a kit test
compares them). `ALWAYS` names the checks that read the whole diff or every tracked file, so they
run for any change. `INPUTS` maps a path (an exact file) or a folder (ending in `/`) to the further
checks that read it. `select(paths)` returns the commands to run, in the recipe's order: none for
no path, and None, meaning the full `make -f agk.mk agk-governance`, when a path matches no entry.
Only documentation and configuration paths are mapped; code and tests run the full set.

`changed_paths(root, default_branch)` lists what a checkout changed, with local git only: the
working tree (`git status --porcelain -z --untracked-files=all`, both sides of a rename) and the
commits of HEAD not on `origin/<default branch>` (else `<default branch>`). None when git cannot
tell (no repository, no default branch), which also means the full set. No network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
from pathlib import Path

GIT_TIMEOUT_SECONDS = 20

CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("protected-changes", ("scripts/agk/check_protected_changes.py",)),
    ("requirements", ("scripts/agk/check_requirements.py",)),
    ("adrs", ("scripts/agk/check_adrs.py",)),
    ("numbers", ("scripts/agk/check_numbers.py",)),
    ("specs", ("scripts/agk/check_specs.py",)),
    ("neutrality", ("scripts/agk/check_neutrality.py",)),
    ("build-state", ("scripts/agk/check_build_state.py",)),
    ("kit-tests", ("scripts/agk/check_kit_tests.py",)),
    ("design", ("scripts/agk/check_design.py",)),
    ("playbooks", ("scripts/agk/check_playbooks.py",)),
    ("runbooks", ("scripts/agk/check_runbooks.py",)),
    ("acceptance", ("scripts/agk/check_acceptance.py",)),
    ("plan", ("scripts/agk/check_plan.py",)),
    ("reviewers", ("scripts/agk/reviewers.py", "--check")),
    ("codeowners", ("scripts/agk/reviewers.py", "--check-codeowners")),
    ("pr-mode", ("scripts/agk/check_pr_mode.py",)),
    ("final-clearance", ("scripts/agk/check_final_clearance.py",)),
)

ALWAYS: frozenset[str] = frozenset(
    {"protected-changes", "neutrality", "build-state", "pr-mode", "final-clearance"}
)

# A path or folder, and the checks besides ALWAYS that read it (from the paths each check and the
# modules it imports name).
INPUTS: tuple[tuple[str, frozenset[str]], ...] = (
    ("docs/requirements.md", frozenset({"requirements", "numbers", "specs", "plan", "design"})),
    ("docs/adr/", frozenset({"adrs", "numbers", "specs", "kit-tests", "acceptance"})),
    ("docs/specs/", frozenset({"specs", "numbers", "acceptance"})),
    ("docs/runs/", frozenset({"numbers", "specs", "acceptance", "playbooks"})),
    ("docs/research/", frozenset({"acceptance", "playbooks"})),
    ("docs/discovery/", frozenset({"acceptance"})),
    ("docs/design/", frozenset({"design", "acceptance"})),
    ("docs/plan/", frozenset({"plan"})),
    ("docs/sources/", frozenset({"plan", "design"})),
    ("docs/runbooks/", frozenset({"runbooks"})),
    ("docs/acceptance/", frozenset({"acceptance"})),
    ("docs/guides/", frozenset()),
    ("docs/build-state.md", frozenset()),
    ("changelog.d/", frozenset()),
    ("README.md", frozenset({"design"})),
    ("config/playbooks/", frozenset({"playbooks", "acceptance"})),
    ("config/stack-signals.toml", frozenset({"acceptance"})),
    ("config/neutrality.txt", frozenset({"playbooks"})),
    ("config/reviewers.yaml", frozenset({"reviewers", "codeowners"})),
    ("config/protected-paths.txt", frozenset({"reviewers", "codeowners"})),
    (".github/CODEOWNERS", frozenset({"reviewers", "codeowners"})),
)


def _entries(path: str) -> list[frozenset[str]]:
    return [
        checks
        for entry, checks in INPUTS
        if (path.startswith(entry) if entry.endswith("/") else path == entry)
    ]


def select(paths: list[str]) -> list[tuple[str, ...]] | None:
    """The commands to run for these paths in the recipe's order; None means the full set."""
    if not paths:
        return []
    wanted = set(ALWAYS)
    for path in paths:
        found = _entries(path)
        if not found:
            return None
        for checks in found:
            wanted |= checks
    return [argv for name, argv in CHECKS if name in wanted]


def _git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _status_paths(out: str) -> list[str]:
    """Paths of `git status --porcelain -z`; a rename or copy gives both sides."""
    parts = out.split("\0")
    paths: list[str] = []
    i = 0
    while i < len(parts):
        item = parts[i]
        i += 1
        if len(item) < 4:
            continue
        paths.append(item[3:])
        if item[0] in "RC" or item[1] in "RC":
            if i < len(parts) and parts[i]:
                paths.append(parts[i])
            i += 1
    return paths


def changed_paths(root: Path, default_branch: str) -> list[str] | None:
    """The sorted paths the checkout changed, or None when git cannot tell."""
    status = _git(root, "status", "--porcelain", "-z", "--untracked-files=all")
    if status is None:
        return None
    base = None
    for ref in (f"origin/{default_branch}", default_branch):
        if _git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}") is not None:
            base = ref
            break
    if base is None:
        return None
    diff = _git(root, "diff", "--name-only", "--no-renames", "-z", f"{base}...HEAD")
    if diff is None:
        return None
    found = set(_status_paths(status)) | {p for p in diff.split("\0") if p}
    return sorted(found)
