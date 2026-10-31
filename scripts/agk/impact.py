"""The regression selection of a change: which tests guard the changed code (brief #373, ADR-0220).

Standard library only. Read-only: it reads git and files, runs nothing and calls no network. The
optional `[testing]` table of `agk.toml` says, by rule, which tests guard which code:

- `profile`: `fast`, `balanced` (the default) or `thorough`;
- `always_full`: path globs; a changed file that matches one makes the selection full;
- `map`: a list of `{ code = "<glob>", tests = ["<glob>", ...] }`;
- `budget_seconds`: the target time of the full project suite (300 by default), read later by the
  metrics;
- `excluded`: a list of `"<tag>: <reason>"` texts, the tests that the project's own command leaves
  out (brief #425, ADR-0230). Nothing here interprets them; proof lists them in its manifest.

For the change base..head `impact` gives the existing test files of the head (`test_dirs`,
`test_patterns`) that a `tests` glob matches, in an entry whose `code` glob matches a changed file,
each with that file and the entry; `full`, with its reason, when a changed file matches
`always_full` or the profile is `thorough`; and `unmapped`, the changed files outside the test
folders that no entry covers. Under `balanced` an unmapped file makes the selection full (when
unsure, run more); under `fast` it is only listed. A change of only `*.md` files and files under
`docs/` selects nothing under every profile, and such a file is never unmapped. Without the table
the selection is full ("no [testing] table"), which is what governance runs today. Nothing runs the
selection yet: `test_plan.py` shows it.

A glob is a path glob: `*` and `?` stay in one folder, `**` crosses folders, and `dir/` is
`dir/**`. A bad setting is refused (CheckError), naming the setting.
"""

from __future__ import annotations

import fnmatch
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, config_source, git, load_config

PROFILES = ("fast", "balanced", "thorough")
KEYS = {"profile", "always_full", "map", "budget_seconds", "excluded"}
EXCLUDED = re.compile(r"[^\s:]+: \S[^\n]*")
ENTRY_KEYS = {"code", "tests"}
DEFAULT_BUDGET = 300
NO_TABLE = "no [testing] table"


@dataclass
class Selected:
    test: str  # the selected test file
    changed: str  # the changed file whose entry selected it (the first, in path order)
    code: str  # the entry's code glob
    tests: list[str]  # the entry's tests globs


@dataclass
class Impact:
    table: bool  # a [testing] table is set
    profile: str | None  # None without the table
    full: bool
    reason: str | None  # why the selection is full; None when it is not
    selected: list[Selected] = field(default_factory=list)  # in test-file order
    unmapped: list[str] = field(default_factory=list)
    docs_only: bool = False  # the change is only documentation, so nothing is selected

    def data(self) -> dict:
        return {
            "table": self.table,
            "profile": self.profile,
            "full": self.full,
            "reason": self.reason,
            "selected": [
                {"file": s.test, "changed": s.changed, "code": s.code, "tests": list(s.tests)}
                for s in self.selected
            ],
            "unmapped": list(self.unmapped),
        }


def glob_regex(glob: str) -> re.Pattern:
    """A path glob: `*` and `?` stay in one folder, `**` crosses folders, `dir/` is `dir/**`."""
    glob = glob + "**" if glob.endswith("/") else glob
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif glob.startswith("**", i):
            out, i = out + ".*", i + 2
        else:
            out += {"*": "[^/]*", "?": "[^/]"}.get(glob[i]) or re.escape(glob[i])
            i += 1
    return re.compile(out)


def matches(path: str, glob: str) -> bool:
    return glob_regex(glob).fullmatch(path) is not None


def _glob_ok(value: object) -> bool:
    """A non-empty path glob inside the repository: `/` as the separator (no `\\`, which git's
    paths never hold), not absolute, no drive, no `..` part."""
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        return False
    return not value.startswith("/") and ":" not in value and ".." not in value.split("/")


def _globs(value: object, empty_ok: bool) -> bool:
    return isinstance(value, list) and (empty_ok or bool(value)) and all(_glob_ok(v) for v in value)


def testing_table(root: Path) -> dict | None:
    """The `[testing]` settings with their defaults, or None without the table; a bad one is
    refused (CheckError) naming the setting."""
    try:
        table = config_source(root).get("testing")
    except (OSError, UnicodeDecodeError, ValueError):
        raise CheckError("agk.toml cannot be read (setting: testing)") from None
    if table is None:
        return None
    if not isinstance(table, dict) or set(table) - KEYS:
        raise CheckError(
            "[testing] is a table of profile, always_full, map, budget_seconds and excluded "
            "(setting: testing)"
        )
    profile = table.get("profile", "balanced")
    if profile not in PROFILES:
        raise CheckError("the profile is fast, balanced or thorough (setting: testing.profile)")
    always_full = table.get("always_full", [])
    if not _globs(always_full, empty_ok=True):
        raise CheckError(
            "always_full must be a list of path globs inside the repository "
            "(setting: testing.always_full)"
        )
    entries = table.get("map", [])
    if not isinstance(entries, list):
        raise CheckError(
            "map must be a list of { code = <glob>, tests = [<glob>, ...] } (setting: testing.map)"
        )
    mapped = []
    for n, entry in enumerate(entries, 1):
        setting = f"testing.map[{n}]"
        if not isinstance(entry, dict) or set(entry) - ENTRY_KEYS:
            raise CheckError(f"a map entry is a table of code and tests (setting: {setting})")
        if not _glob_ok(entry.get("code")):
            raise CheckError(
                f"the code of a map entry must be a path glob inside the repository "
                f"(setting: {setting}.code)"
            )
        if not _globs(entry.get("tests"), empty_ok=False):
            raise CheckError(
                f"the tests of a map entry must be a list of path globs inside the repository "
                f"(setting: {setting}.tests)"
            )
        mapped.append({"code": entry["code"], "tests": list(entry["tests"])})
    budget = table.get("budget_seconds", DEFAULT_BUDGET)
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise CheckError(
            "budget_seconds must be a whole number of seconds above 0 "
            "(setting: testing.budget_seconds)"
        )
    check_excluded(table.get("excluded", []))
    return {
        "profile": profile,
        "always_full": list(always_full),
        "map": mapped,
        "budget_seconds": budget,
    }


def check_excluded(value: object) -> list[str]:
    """The `excluded` entries, each `"<tag>: <reason>"` (a tag with no space or colon, then one
    line of reason); a malformed one is refused naming the setting, never its value."""
    if not isinstance(value, list):
        raise CheckError(
            'excluded must be a list of "<tag>: <reason>" texts (setting: testing.excluded)'
        )
    for n, entry in enumerate(value, 1):
        if not isinstance(entry, str) or EXCLUDED.fullmatch(entry.strip()) is None:
            raise CheckError(
                'an excluded entry is one "<tag>: <reason>" text '
                f"(setting: testing.excluded[{n}])"
            )
    return [entry.strip() for entry in value]


def excluded_entries(root: Path) -> list[str]:
    """The `[testing] excluded` entries in their order, [] without the table or the key. The whole
    table is checked first, so a bad setting is refused (CheckError) as everywhere else."""
    if testing_table(root) is None:
        return []
    return check_excluded(config_source(root)["testing"].get("excluded", []))


def is_doc(path: str) -> bool:
    return path.endswith(".md") or path.startswith("docs/")


def in_test_dirs(path: str, dirs: list[str]) -> bool:
    return any(d.strip("/") in ("", ".") or path.startswith(d.strip("/") + "/") for d in dirs)


def changed_files(root: Path, base: str, head: str) -> list[str]:
    """The paths changed between base and head, deletions included; a rename is both paths."""
    out = git(root, "diff", "-z", "--name-only", "--no-renames", base, head)
    return sorted(p for p in out.split("\0") if p)


def head_files(root: Path, head: str) -> list[str]:
    out = git(root, "ls-tree", "-r", "-z", "--name-only", head)
    return sorted(p for p in out.split("\0") if p)


def is_test_file(path: str, dirs: list[str], patterns: list[str]) -> bool:
    name = path.rsplit("/", 1)[-1]
    return in_test_dirs(path, dirs) and any(fnmatch.fnmatchcase(name, p) for p in patterns)


def impact(root: Path, base: str, head: str) -> Impact:
    """The regression selection of base..head (git and files only, nothing run)."""
    table = testing_table(root)
    if table is None:
        return Impact(False, None, True, NO_TABLE)
    profile = table["profile"]
    changed = changed_files(root, base, head)
    hit = next(((g, p) for p in changed for g in table["always_full"] if matches(p, g)), None)
    if changed and not hit and all(is_doc(p) for p in changed):
        return Impact(True, profile, False, None, docs_only=True)
    cfg = load_config(root)
    dirs, patterns = list(cfg["test_dirs"]), list(cfg["test_patterns"])
    tests = [p for p in head_files(root, head) if is_test_file(p, dirs, patterns)]
    chosen: dict[str, Selected] = {}
    unmapped: list[str] = []
    for path in changed:
        guarded = False
        for entry in (e for e in table["map"] if matches(path, e["code"])):
            for test in tests:
                if any(matches(test, g) for g in entry["tests"]):
                    guarded = True
                    if test not in chosen:
                        chosen[test] = Selected(test, path, entry["code"], list(entry["tests"]))
        # A file that no entry covers, or whose entries select no existing test file, is
        # unmapped; only a real test file (the change's own test) and documentation are not.
        if not guarded and not is_doc(path) and not is_test_file(path, dirs, patterns):
            unmapped.append(path)
    selected = [chosen[t] for t in sorted(chosen)]
    reason = None
    if hit:
        reason = f"always_full {hit[0]} matches {hit[1]}"
    elif profile == "thorough":
        reason = "profile thorough"
    elif profile == "balanced" and unmapped:
        noun = "file" if len(unmapped) == 1 else "files"
        reason = f"profile balanced: {len(unmapped)} unmapped {noun}"
    return Impact(True, profile, reason is not None, reason, selected, unmapped)


def text(found: Impact) -> list[str]:
    """The `regression` section of the test plan."""
    if found.full:
        lines = [f"regression: full ({found.reason})"]
    elif found.docs_only:
        lines = ["regression: nothing selected (only documentation changed)"]
    elif not found.selected:
        lines = ["regression: nothing selected"]
    else:
        count = len(found.selected)
        noun = "test file" if count == 1 else "test files"
        lines = [f"regression: {count} {noun} selected"]
        lines.extend(
            f"  file: {s.test} ({s.changed} matches code {s.code}, tests {', '.join(s.tests)})"
            for s in found.selected
        )
    lines.extend(f"unmapped (no [testing] map entry covers it): {p}" for p in found.unmapped)
    return lines
