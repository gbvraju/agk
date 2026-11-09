"""The regression selection of a change: which tests guard the changed code (brief #373, ADR-0220).

Standard library only. Read-only: it reads git and files, runs nothing and calls no network. The
optional `[testing]` table of `agk.toml` says, by rule, which tests guard which code:

- `profile`: `fast`, `balanced` (the default) or `thorough`;
- `always_full`: path globs; a changed file that matches one makes the selection full;
- `map`: a list of `{ code = "<glob>", tests = ["<glob>", ...] }`;
- `budget_seconds`: the target time of the full project suite (300 by default), read later by the
  metrics;
- `excluded`: a list of `"<tag>: <reason>"` texts, the tests that the project's own command leaves
  out (brief #425, ADR-0230). Nothing here interprets them; proof lists them in its manifest;
- `proof_regression`: a boolean, false by default; with true and a `[proof]` table, proof also runs
  the selection on the head (brief #442, ADR-0238, off until a person approves the spec change);
- `pr_tests`: `full` (the default) or `selected`; with `selected`, a pull request's CI step
  `Project tests` runs only the selection, while a push and a release run the full suite
  (`project_tests.py`, brief #453, ADR-0242);
- `junit`: the path or glob of the JUnit XML reports that the project's own test command writes,
  relative to the run's folder (SPEC-0044 rule 2, brief #560); a level's own `junit` comes first
  (SPEC-0055 rule 8). `run_timing` reads it, or else the durations
  table that pytest prints when the project's command passes `--durations=0`, for the per-file
  timing of a run; the kit adds no flag to the command, and with neither the timing is `unknown`;
- `workers`: `1` (the default), `"auto"` (the CPU count, at least 1) or a positive whole number,
  the parallel workers of the full run (SPEC-0044 rule 4, brief #583; `prepush.full_command`);
- `parallel_command`: the full command of a non-pytest runner with more than one worker, `{workers}`
  filled with the number (rule 5);
- `slow_suite_seconds`: above it a single-process full run gets doctor's line (rule 7; 600);
- `results_dir`, `keep_passed`, `keep_runs`: the retired run folders of ADR-0299 (SPEC-0046 rule
  11, build (f)): still accepted with their checks, they do nothing, and `run_folder_deprecation`
  gives the one line `prepush.py` and `doctor.py` print when one is set; build (g) removes them;
- `pre_merge_tests`: the test files (paths, no globs) that `merge_cleared.py` runs on the would-be
  merge after governance passes (brief #667, ADR-0320, amendment 132 of SPEC-0039 rule 6), each a
  file; without the key, none;
- `links`: a list of `{ code = ["<glob>", ...], run = ["<area>:<level>", ...] }` (SPEC-0055 rule 7,
  brief #828): a changed file that matches a `code` glob selects each named level on a pull request,
  even one whose `when` has no `pr`. A link only adds tests. The links of a `.agk-test-map.toml`
  built from the head's tree are added to them; one of another tree adds none and says so. A linked
  level whose environment is absent fails the test step in CI (`CI` set, as `common.resolve_base`
  reads it) and is `not run` on a developer's machine.

For the change base..head `impact` gives the existing test files of the head (`test_dirs`,
`test_patterns`) that a `tests` glob matches, in an entry whose `code` glob matches a changed file,
each with that file and the entry; `full`, with its reason, when a changed file matches
`always_full` or the profile is `thorough`; and `unmapped`, the changed files outside the test
folders that no entry covers. Under `balanced` a file that no entry covers selects the test files
of the head that name its path or its folder, and the selection is full only when no test names
it (SPEC-0055 rule 6, brief #773, ADR-0359; `unmapped: <path> -> <k> tests that name it`); a
covered file whose entries select no existing test stays full. Under `fast` an unmapped file is
only listed. A change of only `*.md` files and files under
`docs/` selects nothing under every profile, and such a file is never unmapped. Without the table
the selection is full ("no [testing] table"), which is what governance runs today. `test_plan.py`
shows the selection; `prepush.py` runs the selected regression tests (brief #417), and `proof.py`
runs them on the head only with `proof_regression = true` (brief #442, off by default).

A glob is a path glob: `*` and `?` stay in one folder, `**` crosses folders, and `dir/` is
`dir/**`. A bad setting is refused (CheckError), naming the setting.
"""

from __future__ import annotations

import fnmatch
import math
import os
import re
import subprocess  # nosec B404 - fixed argument list only, no shell
import sys
import tomllib
import xml.parsers.expat
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, area_levels, config_source, git, load_config, proof_areas

PROFILES = ("fast", "balanced", "thorough")
KEYS = {
    "profile",
    "always_full",
    "map",
    "budget_seconds",
    "excluded",
    "proof_regression",
    "pr_tests",
    "junit",
    "workers",
    "parallel_command",
    "slow_suite_seconds",
    "results_dir",
    "keep_passed",
    "keep_runs",
    "pre_merge_tests",
    "rerun_alone",
    "map_source",
    "links",
}
MAP_SOURCES = ("curated", "generated")  # SPEC-0055 rule 1: data, never a code path
TEST_ENV = "AGK_TEST_ENV"  # what a machine has (SPEC-0055 rule 4)
DEFAULT_SLOW = 600
DEFAULT_KEEP_RUNS = 20
RUN_FOLDER_KEYS = ("results_dir", "keep_passed", "keep_runs")  # retired (SPEC-0046 rule 11)
RUN_FOLDER_DEPRECATED = "deprecated: testing.results_dir (ADR-0303)"
PR_TESTS = ("full", "selected")
EXCLUDED = re.compile(r"[^\s:]+: \S[^\n]*")
ENTRY_KEYS = {"code", "tests"}
LINK_KEYS = {"code", "run"}
MAP_FILE = ".agk-test-map.toml"  # written by test_map.py, git-ignored (SPEC-0055 rule 5)
MAP_STALE = (
    "tests: the generated map is of another tree or unreadable, so its links are not read "
    "(setting: testing.links)"
)
MAP_UNREAD = (
    "tests: the generated map cannot be built or read, so it adds no entries "
    "(setting: testing.map_source)"
)
LINK_REASON = "link: "  # how a run that a link added says why it runs
LINK_ABSENT = f"{LINK_REASON}a linked level's environment is absent (setting: testing.links)"
DEFAULT_BUDGET = 300
NO_TABLE = "no [testing] table"
# Per-file timing (SPEC-0044 rules 2 and 3).
DURATIONS_HEAD = re.compile(r"^=+ slowest (?:\d+ )?durations =+$")
DURATION_LINE = re.compile(r"^\s*(\d+(?:\.\d+)?)s\s+(?:call|setup|teardown)\s+(\S+?)::")
MTIME_SLACK = 2  # seconds: a file system that keeps coarse modification times
TIMING_FILES = 50  # the record keeps the slowest 50 files
JUNIT_LIMIT = 32 * 1024 * 1024  # a larger report is not read
JUNIT_UNREADABLE = (
    "tests: the JUnit report cannot be read; per-file timing unknown (setting: testing.junit)"
)
JUNIT_MISSING = (
    "tests: no JUnit report was written by this run; per-file timing unknown "
    "(setting: testing.junit)"
)
PRE_MERGE = "pre_merge_tests"
PRE_MERGE_BAD = (
    "pre_merge_tests must be a non-empty list of test file paths inside the repository "
    "(setting: testing.pre_merge_tests)"
)
PRE_MERGE_MISSING = "a pre-merge test is not a file (setting: testing.pre_merge_tests)"
UNKNOWN_TIMING = {"source": "unknown", "total_seconds": None, "files": []}
NAME_WORD = re.compile(r"[\w./-]+")  # a path-like word of a test file (SPEC-0055 rule 6)
NAMED = "(names it)"  # the `code` of a test selected because it names the changed file


@dataclass
class Selected:
    test: str  # the selected test file
    changed: str  # the changed file whose entry selected it (the first, in path order)
    code: str  # the entry's code glob
    tests: list[str]  # the entry's tests globs


@dataclass
class Linked:
    run: str  # the level, `<area>:<level>`
    changed: str  # the changed file that its link matched (the first, in path order)
    code: str  # the link's code glob


@dataclass
class Impact:
    table: bool  # a [testing] table is set
    profile: str | None  # None without the table
    full: bool
    reason: str | None  # why the selection is full; None when it is not
    selected: list[Selected] = field(default_factory=list)  # in test-file order
    unmapped: list[str] = field(default_factory=list)
    docs_only: bool = False  # the change is only documentation, so nothing is selected
    named: dict[str, int] = field(default_factory=dict)  # uncovered path -> tests that name it
    map_source: str | None = None  # the `[testing] map_source`, None where it is not set
    linked: list[Linked] = field(default_factory=list)  # the levels links select (SPEC-0055 rule 7)
    link_notes: list[str] = field(default_factory=list)
    map_notes: list[str] = field(default_factory=list)  # the generated map could not be used
    tracked: list[str] = field(default_factory=list)  # the head's files, read only for a link

    def data(self) -> dict:
        source = {} if self.map_source is None else {"map_source": self.map_source}
        links = [{"run": k.run, "changed": k.changed, "code": k.code} for k in self.linked]
        return {
            **source,
            **({"links": links} if links else {}),
            **({"map_notes": list(self.map_notes)} if self.map_notes else {}),
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


@cache  # a generated map has an entry per file, each matched per changed file
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


def _folder_ok(value: object) -> bool:
    """A folder inside the repository and below its root: a path as `_glob_ok` takes it, with no
    empty, `.` or wildcard part (`.` would make the repository's root the results root)."""
    if not isinstance(value, str) or not _glob_ok(value) or any(c in value for c in "*?["):
        return False
    return all(part not in ("", ".") for part in value.rstrip("/").split("/"))


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
            "[testing] is a table of profile, always_full, map, budget_seconds, excluded, "
            "proof_regression, pr_tests, junit, workers, parallel_command, "
            "slow_suite_seconds, results_dir, keep_passed, keep_runs, rerun_alone and map_source "
            "(setting: testing)"
        )
    links = check_links(table.get("links", []), root)
    profile = table.get("profile", "balanced")
    if profile not in PROFILES:
        raise CheckError("the profile is fast, balanced or thorough (setting: testing.profile)")
    always_full = table.get("always_full", [])
    if not _globs(always_full, empty_ok=True):
        raise CheckError(
            "always_full must be a list of path globs inside the repository "
            "(setting: testing.always_full)"
        )
    mapped = check_map(table.get("map", []))
    budget = table.get("budget_seconds", DEFAULT_BUDGET)
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise CheckError(
            "budget_seconds must be a whole number of seconds above 0 "
            "(setting: testing.budget_seconds)"
        )
    check_excluded(table.get("excluded", []))
    if not isinstance(table.get("proof_regression", False), bool):
        raise CheckError(
            "proof_regression must be true or false (setting: testing.proof_regression)"
        )
    if table.get("pr_tests", "full") not in PR_TESTS:
        raise CheckError("pr_tests is full or selected (setting: pr_tests)")
    if "junit" in table and not _glob_ok(table["junit"]):
        raise CheckError(
            "junit must be a file path relative to the run's folder (setting: testing.junit)"
        )
    workers = table.get("workers", 1)
    if workers != "auto" and (
        isinstance(workers, bool) or not isinstance(workers, int) or workers < 1
    ):
        raise CheckError('workers is "auto" or a whole number above 0 (setting: testing.workers)')
    command = table.get("parallel_command", "x")
    if not isinstance(command, str) or not command.strip():
        raise CheckError("parallel_command must be a command (setting: testing.parallel_command)")
    slow = table.get("slow_suite_seconds", DEFAULT_SLOW)
    if isinstance(slow, bool) or not isinstance(slow, int) or slow <= 0:
        raise CheckError(
            "slow_suite_seconds must be a whole number of seconds above 0 "
            "(setting: testing.slow_suite_seconds)"
        )
    if "results_dir" in table and not _folder_ok(table["results_dir"]):
        raise CheckError(
            "results_dir must be a folder path inside the repository (setting: testing.results_dir)"
        )
    if not isinstance(table.get("keep_passed", False), bool):
        raise CheckError("keep_passed must be true or false (setting: testing.keep_passed)")
    keep = table.get("keep_runs", DEFAULT_KEEP_RUNS)
    if isinstance(keep, bool) or not isinstance(keep, int) or keep < 1:
        raise CheckError("keep_runs must be a whole number above 0 (setting: testing.keep_runs)")
    if not isinstance(table.get("rerun_alone", False), bool):
        raise CheckError("rerun_alone must be true or false (setting: testing.rerun_alone)")
    if PRE_MERGE in table:
        pre_merge_names(table, root)
    source = table.get("map_source", MAP_SOURCES[0])
    if not isinstance(source, str) or source not in MAP_SOURCES:
        raise CheckError("map_source is curated or generated (setting: testing.map_source)")
    return {
        "profile": profile,
        "always_full": list(always_full),
        "map": mapped,
        "budget_seconds": budget,
        **({"map_source": source} if "map_source" in table else {}),
        **({"links": links} if links else {}),
    }


def check_map(entries: object) -> list[dict]:
    """`[testing] map`, or the same shape in the generated file; a bad one is refused."""
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
    return mapped


def check_links(value: object, root: Path) -> list[dict]:
    """The `links` entries; a malformed one, or one naming a level that does not exist, is refused
    naming the setting, never its value (SPEC-0055 rule 7)."""
    if not isinstance(value, list):
        raise CheckError(
            "links must be a list of { code = [<glob>, ...], run = [<area>:<level>, ...] } "
            "(setting: testing.links)"
        )
    known: set[str] = set()
    if value:
        for area in proof_areas(root) or []:
            known |= {f"{area['name']}:{level['name']}" for level in area_levels(area)}
    checked = []
    for n, entry in enumerate(value, 1):
        setting = f"testing.links[{n}]"
        if not isinstance(entry, dict) or set(entry) - LINK_KEYS:
            raise CheckError(f"a link is a table of code and run (setting: {setting})")
        if not _globs(entry.get("code"), empty_ok=False):
            raise CheckError(
                f"the code of a link must be a list of path globs inside the repository "
                f"(setting: {setting}.code)"
            )
        run = entry.get("run")
        if (
            not isinstance(run, list)
            or not run
            or not all(isinstance(r, str) and r in known for r in run)
        ):
            raise CheckError(
                f"the run of a link must name levels as <area>:<level> (setting: {setting}.run)"
            )
        checked.append({"code": list(entry["code"]), "run": list(run)})
    return checked


def check_pre_merge_tests(value: object) -> list[str]:
    """The `pre_merge_tests` names: a non-empty list of relative file paths inside the repository,
    no globs; a bad one is refused (CheckError) naming the setting, never its value."""
    if not isinstance(value, list) or not value:
        raise CheckError(PRE_MERGE_BAD)
    for name in value:
        if not isinstance(name, str) or not _glob_ok(name) or any(c in name for c in "*?[]"):
            raise CheckError(PRE_MERGE_BAD)
    return list(value)


def pre_merge_names(table: dict | None, tree: Path) -> list[str]:
    """The pre-merge test files of TABLE (a `[testing]` table, None without one) for the tree
    TREE: the key's names, each a file of TREE, else refused naming the setting; without the
    key, none (brief #667)."""
    if table is not None and PRE_MERGE in table:
        names = check_pre_merge_tests(table[PRE_MERGE])
        if not all((tree / name).is_file() for name in names):
            raise CheckError(PRE_MERGE_MISSING)
        return names
    return []


def pre_merge_tests(root: Path) -> list[str]:
    """`[testing] pre_merge_tests` of ROOT (the whole table checked first, a bad setting refused),
    or the default of `pre_merge_names`."""
    found = testing_table(root)
    return pre_merge_names(None if found is None else config_source(root)["testing"], root)


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
                f'an excluded entry is one "<tag>: <reason>" text (setting: testing.excluded[{n}])'
            )
    return [entry.strip() for entry in value]


def excluded_entries(root: Path) -> list[str]:
    """The `[testing] excluded` entries in their order, [] without the table or the key. The whole
    table is checked first, so a bad setting is refused (CheckError) as everywhere else."""
    if testing_table(root) is None:
        return []
    return check_excluded(config_source(root)["testing"].get("excluded", []))


def proof_regression(root: Path) -> bool:
    """`[testing] proof_regression`, false without the table or the key. The whole table is
    checked first, so a bad setting is refused (CheckError) as everywhere else."""
    if testing_table(root) is None:
        return False
    return config_source(root)["testing"].get("proof_regression", False)


def pr_tests(root: Path) -> str:
    """`[testing] pr_tests`, `full` without the table or the key (brief #453, ADR-0242). The whole
    table is checked first, so a bad setting is refused (CheckError) as everywhere else."""
    if testing_table(root) is None:
        return "full"
    return config_source(root)["testing"].get("pr_tests", "full")


def junit_setting(root: Path) -> str | None:
    """`[testing] junit`, None without the table or the key. The whole table is checked first,
    so a bad setting is refused (CheckError) as everywhere else."""
    if testing_table(root) is None:
        return None
    return config_source(root)["testing"].get("junit")


def workers_setting(root: Path) -> int:
    """`[testing] workers` as a number, 1 without the table or the key; `"auto"` is the CPU count,
    at least 1. The whole table is checked first, so a bad setting is refused (CheckError)."""
    if testing_table(root) is None:
        return 1
    workers = config_source(root)["testing"].get("workers", 1)
    return max(1, os.cpu_count() or 1) if workers == "auto" else workers


def parallel_command(root: Path) -> str | None:
    """`[testing] parallel_command`, None without the table or the key (checked first)."""
    if testing_table(root) is None:
        return None
    return config_source(root)["testing"].get("parallel_command")


def slow_suite_seconds(root: Path) -> int:
    """`[testing] slow_suite_seconds`, 600 without the table or the key (checked first)."""
    if testing_table(root) is None:
        return DEFAULT_SLOW
    return config_source(root)["testing"].get("slow_suite_seconds", DEFAULT_SLOW)


def rerun_alone(root: Path) -> bool:
    """`[testing] rerun_alone`, false without the table or the key (brief #670, ADR-0323). The
    whole table is checked first, so a malformed key is refused naming the setting."""
    if testing_table(root) is None:
        return False
    return config_source(root)["testing"].get("rerun_alone", False)


def run_folder_deprecation(root: Path) -> str | None:
    """SPEC-0046 rule 11: the deprecation line when `[testing]` sets one of the retired run-folder
    keys, None otherwise. The whole table is checked first, so a malformed key is still refused
    (CheckError) naming the setting."""
    if testing_table(root) is None:
        return None
    table = config_source(root)["testing"]
    return RUN_FOLDER_DEPRECATED if any(k in table for k in RUN_FOLDER_KEYS) else None


def durations_sums(output: str) -> dict[str, float] | None:
    """The seconds of each test file from pytest's durations table (`call`, `setup` and
    `teardown` lines summed by the file of the test id), or None when the output has no table."""
    sums: dict[str, float] | None = None
    for line in output.splitlines():
        if sums is None:
            if DURATIONS_HEAD.match(line.strip()):
                sums = {}
            continue
        if line.startswith("="):
            break
        found = DURATION_LINE.match(line)
        if found:
            sums[found.group(2)] = sums.get(found.group(2), 0.0) + float(found.group(1))
    return sums


class Unreadable(Exception):
    """A JUnit report that cannot be parsed, or that declares a document type."""


def junit_sums(data: bytes) -> dict[str, float]:
    """The seconds of each `testcase` of a JUnit report, by its `file` attribute or else its
    `classname`. A document type or entity declaration is refused, never expanded."""
    sums: dict[str, float] = {}

    def refuse(*_args) -> None:
        raise Unreadable

    def start(name: str, attrs: dict[str, str]) -> None:
        if name != "testcase":
            return
        try:
            seconds = float(attrs.get("time") or 0)
        except ValueError:
            raise Unreadable from None
        if not math.isfinite(seconds) or seconds < 0:
            raise Unreadable
        key = attrs.get("file") or attrs.get("classname") or "(no file)"
        sums[key] = sums.get(key, 0.0) + seconds

    parser = xml.parsers.expat.ParserCreate()
    parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.StartDoctypeDeclHandler = refuse
    parser.EntityDeclHandler = refuse
    parser.StartElementHandler = start
    try:
        parser.Parse(data, True)
    except xml.parsers.expat.ExpatError:
        raise Unreadable from None
    return sums


def report_files(folder: Path, junit: str, since: float | None = None) -> list[Path]:
    """The reports at `junit` in `folder`, sorted: one path, or every file a glob matches (Gradle
    writes a folder of them, SPEC-0055 rule 8). With `since`, only those written at or after it (a
    file older than the run is not this run's report)."""
    try:
        found = sorted(folder.glob(junit)) if any(c in junit for c in "*?[") else [folder / junit]
    except (OSError, ValueError):
        return []
    kept = []
    for report in found:
        try:
            if report.is_file() and (
                since is None or report.stat().st_mtime >= since - MTIME_SLACK
            ):
                kept.append(report)
        except OSError:
            continue
    return kept


def report_of(areas: list[dict] | None, run: str, default: str | None) -> str | None:
    """The report of the run named `<area>:<level>`: the level's `junit`, else DEFAULT, the
    `[testing] junit` (SPEC-0055 rule 8). A run with any other name has DEFAULT."""
    level = level_of(areas, run)
    return (level or {}).get("junit") or default


def level_of(areas: list[dict] | None, run: str) -> dict | None:
    """The level of the run named `<area>:<level>`, None for a run with any other name."""
    area_name, _, level_name = run.partition(":")
    for area in areas or []:
        if area["name"] == area_name:
            return next((x for x in area.get("levels", []) if x["name"] == level_name), None)
    return None


def measure(
    output: str, folder: Path, junit: str | None, since: float
) -> tuple[str, dict[str, float] | None, str | None]:
    """(source, seconds by file or None, the one line to print or None) of one test run: the
    JUnit reports at `junit` in `folder` written at or after `since`, else the durations table of
    `output`, else `unknown`."""
    if junit is not None:
        reports = report_files(folder, junit, since)
        if reports:
            seconds_of: dict[str, float] = {}
            try:
                if sum(r.stat().st_size for r in reports) > JUNIT_LIMIT:
                    raise Unreadable
                for report in reports:
                    for key, seconds in junit_sums(report.read_bytes()).items():
                        seconds_of[key] = seconds_of.get(key, 0.0) + seconds
            except (OSError, Unreadable):
                return "unknown", None, JUNIT_UNREADABLE
            return "junit", seconds_of, None
    sums = durations_sums(output)
    if sums is not None:
        return "durations", sums, None
    return "unknown", None, JUNIT_MISSING if junit is not None else None


def run_timing(
    output: str, folder: Path, junit: str | None, since: float
) -> tuple[dict, str | None]:
    """The `timing` object of a run in the prepush record (SPEC-0044 rule 3): `files` (path and
    seconds, slowest first, at most 50), `total_seconds` over every file and `source`; and the
    one line to print, or None."""
    source, sums, note = measure(output, folder, junit, since)
    if sums is None:
        return dict(UNKNOWN_TIMING, files=[]), note
    ranked = sorted(sums.items(), key=lambda kv: (-kv[1], kv[0]))[:TIMING_FILES]
    files = [{"path": p, "seconds": round(s, 3)} for p, s in ranked]
    return {"source": source, "total_seconds": round(sum(sums.values()), 3), "files": files}, note


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


def _blobs(root: Path, head: str, paths: list[str]) -> list[tuple[str, str]]:
    """(path, text) of each of PATHS at HEAD, by one `git cat-file --batch`."""
    asked = [p for p in paths if "\n" not in p]
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "cat-file", "--batch"],
        cwd=root,
        input="".join(f"{head}:{p}\n" for p in asked).encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise CheckError("git cat-file failed")
    out, at, found = proc.stdout, 0, []
    for path in asked:
        end = out.index(b"\n", at)
        fields = out[at:end].split(b" ")
        at = end + 1
        if len(fields) == 3 and fields[1] == b"blob":
            size = int(fields[2])
            found.append((path, out[at : at + size].decode("utf-8", "replace")))
            at += size + 1
    return found


def name_index(root: Path, head: str, tests: list[str]) -> dict[str, set[str]]:
    """Each path-like word of the test files at HEAD, and each folder it holds as `<folder>/`,
    with the test files that hold it."""
    index: dict[str, set[str]] = {}
    for test, source in _blobs(root, head, tests):
        for word in set(NAME_WORD.findall(source)):
            word = word.removeprefix("./").rstrip(".")
            index.setdefault(word, set()).add(test)
            parts = word.split("/")
            for n in range(1, len(parts)):
                index.setdefault("/".join(parts[:n]) + "/", set()).add(test)
    return index


def tests_naming(path: str, index: dict[str, set[str]]) -> list[str]:
    """The test files that name PATH or its folder. A folder of one part is named only with its
    slash, because the bare word (`kit`, `config`) is ordinary prose."""
    folder = path.rpartition("/")[0]
    hits = set(index.get(path, ()))
    if folder:
        hits |= index.get(folder + "/", set())
        if "/" in folder:
            hits |= index.get(folder, set())
    return sorted(hits)


def uncovered(root: Path, head: str = "HEAD") -> list[str]:
    """The tracked files that would make a `balanced` selection full: no entry covers them, no
    test names them and they are neither documentation, a test file nor `always_full`."""
    table = testing_table(root)
    if table is None:
        return []
    cfg = load_config(root)
    dirs, patterns = list(cfg["test_dirs"]), list(cfg["test_patterns"])
    files = head_files(root, head)
    index = name_index(root, head, [p for p in files if is_test_file(p, dirs, patterns)])
    globs = [e["code"] for e in map_entries(root, head, table)[0]] + table["always_full"]
    return [
        p
        for p in files
        if not is_doc(p)
        and not is_test_file(p, dirs, patterns)
        and not any(matches(p, g) for g in globs)
        and not tests_naming(p, index)
    ]


def impact(root: Path, base: str, head: str) -> Impact:
    """The regression selection of base..head, with the map's source where it is set."""
    found = select(root, base, head)
    table = testing_table(root) or {}
    found.map_source = table.get("map_source")
    links = list(table.get("links", []))
    derived, found.link_notes = derived_links(root, head)
    links += derived
    if links:
        found.linked = linked_levels(links, changed_files(root, base, head))
        found.tracked = head_files(root, head) if found.linked else []
    return found


def current_map(root: Path, head: str) -> dict | None:
    """`.agk-test-map.toml` as data when its first line names HEAD's tree, else None."""
    try:
        text = (root / MAP_FILE).read_text(encoding="utf-8")
        table = tomllib.loads(text)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    tree = git(root, "rev-parse", head + "^{tree}").strip()
    return table if text.split("\n", 1)[0] == f"# tree {tree}" else None


def generated_entries(root: Path, head: str) -> list[dict] | None:
    """The `[[testing.map]]` entries of HEAD's map file, None when it has no usable file."""
    table = current_map(root, head)
    section = None if table is None else table.get("testing", {})
    try:
        return check_map(section.get("map", []) if isinstance(section, dict) else None)
    except CheckError:
        return None


def map_entries(root: Path, head: str, table: dict) -> tuple[list[dict], list[str]]:
    """The entries a selection reads (SPEC-0055 rule 5, a union), and what it could not use."""
    if table.get("map_source") != "generated":
        return table["map"], []
    generated = generated_entries(root, head)
    if generated is None:
        return table["map"], [MAP_UNREAD]
    return [*table["map"], *generated], []


def derived_links(root: Path, head: str) -> tuple[list[dict], list[str]]:
    """The links of the `.agk-test-map.toml` of HEAD's tree, or the line that says it is not."""
    if not (root / MAP_FILE).is_file():
        return [], []  # nobody built one: nothing to read, whichever the map's source
    table = current_map(root, head)
    if table is None:
        return [], [MAP_STALE]
    return check_links(table.get("testing", {}).get("links", []), root), []


def linked_levels(links: list[dict], changed: list[str]) -> list[Linked]:
    """Each level a changed file's link names, once, in name order."""
    found: dict[str, Linked] = {}
    for link in links:
        for path in changed:
            glob = next((g for g in link["code"] if matches(path, g)), None)
            if glob is not None:
                for name in link["run"]:
                    found.setdefault(name, Linked(name, path, glob))
    return [found[name] for name in sorted(found)]


def select(root: Path, base: str, head: str) -> Impact:
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
    entries, map_notes = map_entries(root, head, table)
    chosen: dict[str, Selected] = {}
    unmapped: list[str] = []
    named: dict[str, int] = {}
    index: dict[str, set[str]] | None = None
    for path in changed:
        guarded = False
        covering = [e for e in entries if matches(path, e["code"])]
        for entry in covering:
            for test in tests:
                if any(matches(test, g) for g in entry["tests"]):
                    guarded = True
                    if test not in chosen:
                        chosen[test] = Selected(test, path, entry["code"], list(entry["tests"]))
        # A file that no entry covers, or whose entries select no existing test file, is
        # unmapped; only a real test file (the change's own test) and documentation are not.
        if not guarded and not is_doc(path) and not is_test_file(path, dirs, patterns):
            unmapped.append(path)
            if profile == "balanced" and not hit and not covering:  # SPEC-0055 rule 6
                index = name_index(root, head, tests) if index is None else index
                naming = tests_naming(path, index)
                named[path] = len(naming)
                for test in naming:
                    chosen.setdefault(test, Selected(test, path, NAMED, []))
    selected = [chosen[t] for t in sorted(chosen)]
    reason = None
    if hit:
        reason = f"always_full {hit[0]} matches {hit[1]}"
    elif profile == "thorough":
        reason = "profile thorough"
    elif profile == "balanced" and any(not named.get(p) for p in unmapped):
        count = sum(1 for p in unmapped if not named.get(p))
        reason = f"profile balanced: {count} unmapped {'file' if count == 1 else 'files'}"
    found = Impact(True, profile, reason is not None, reason, selected, unmapped, named=named)
    found.map_notes = map_notes
    return found


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
            f"  file: {s.test} (names {s.changed})"
            if s.code == NAMED
            else f"  file: {s.test} ({s.changed} matches code {s.code}, tests {', '.join(s.tests)})"
            for s in found.selected
        )
    links = [f"link: {k.run} ({k.changed} matches code {k.code})" for k in found.linked]
    return map_lines(found) + lines + links + unmapped_lines(found)


def map_lines(found: Impact) -> list[str]:
    """The line that leads a selection in a repository that sets `map_source` (SPEC-0055 rule 1)."""
    source = [] if found.map_source is None else [f"tests: map {found.map_source}"]
    return source + found.map_notes


def machine_env() -> str:
    """The environments this machine has: the text of `AGK_TEST_ENV` (SPEC-0055 rule 4)."""
    return os.environ.get(TEST_ENV, "")


def level_groups(
    area: dict, paths: list[str], event: str, env: str
) -> tuple[list[dict], list[str]]:
    """PATHS of AREA by level for EVENT: the groups to run (`label`, `level`, `files`) and the lines
    of what does not run. A file belongs to the first level that matches it (SPEC-0055 rule 3); one
    in no level is refused naming the setting; ENV is the comma-separated `AGK_TEST_ENV`."""
    have = {name.strip() for name in env.split(",") if name.strip()}
    levels = area_levels(area)
    placed: dict[str, list[str]] = {}
    for path in paths:
        level = next((x for x in levels if is_test_file(path, x["dirs"], x["patterns"])), None)
        if level is None:
            raise CheckError(
                f"a test file of an area is in no level (setting: proof.{area['name']}.levels)"
            )
        placed.setdefault(level["name"], []).append(path)
    groups: list[dict] = []
    notes: list[str] = []
    for level in levels:
        if level["name"] not in placed:
            continue
        label = f"{area['name']}:{level['name']}"
        absent = next((name for name in level["env"] if name not in have), None)
        if event not in level["when"]:
            notes.append(f"tests: {label} runs on {', '.join(level['when'])}")
        elif absent is not None:
            notes.append(f"not run: {label} (env {absent})")
        else:
            groups.append({"label": label, "level": level, "files": placed[level["name"]]})
    return groups, notes


def in_level(path: str, levels: list[dict], level: dict) -> bool:
    """Whether LEVEL is the first of LEVELS to hold test file PATH (SPEC-0055 rule 3)."""
    first = next((x for x in levels if is_test_file(path, x["dirs"], x["patterns"])), None)
    return first is level


def link_groups(
    found: Impact, areas: list[dict] | None, ran: set[str], env: str
) -> tuple[list[dict], list[str]]:
    """The levels FOUND's links add to the runs named RAN (SPEC-0055 rule 7), each with `label`,
    `level`, `files`, `reason` and `failed`, and the lines of what does not run. A `{files}` level
    takes the selected tests of that level, else all of it; with an environment absent the level is
    `not run`, and in CI (`CI` set) a group that must fail the step (Q-S0055-8)."""
    have = {name.strip() for name in env.split(",") if name.strip()}
    groups: list[dict] = []
    notes = list(found.link_notes)
    for link in found.linked:
        area_name, _, level_name = link.run.partition(":")
        area = next(a for a in areas or [] if a["name"] == area_name)
        if link.run in ran or (not area.get("levels") and area_name in ran):
            continue  # the selection already runs this level
        levels = area_levels(area)
        level = next(x for x in levels if x["name"] == level_name)
        reason = f"{LINK_REASON}{link.changed} matches code {link.code}"
        absent = next((name for name in level["env"] if name not in have), None)
        if absent is not None:
            notes.append(f"not run: {link.run} (env {absent})")
            if os.environ.get("CI"):
                groups.append(
                    {
                        "label": link.run,
                        "level": level,
                        "files": [],
                        "reason": LINK_ABSENT,
                        "failed": True,
                    }
                )
            continue

        selected = [] if found.full else [s.test for s in found.selected]
        files = [p for p in selected if in_level(p, levels, level)]
        files = files or [p for p in found.tracked if in_level(p, levels, level)]
        if files or "{files}" not in level["command"]:
            groups.append(
                {
                    "label": link.run,
                    "level": level,
                    "files": files,
                    "reason": reason,
                    "failed": False,
                }
            )
        else:
            notes.append(f"not run: {link.run} (no test file)")
    return groups, notes


def unmapped_lines(found: Impact) -> list[str]:
    """One line per unmapped file: with the count of the tests that name it where that was
    looked up (SPEC-0055 rule 6), else the line of a file that is only listed."""
    return [
        f"unmapped: {p} -> {found.named[p]} tests that name it"
        if p in found.named
        else f"unmapped (no [testing] map entry covers it): {p}"
        for p in found.unmapped
    ]
