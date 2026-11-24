"""The reference guide is a shared index of this repository (brief #1873, ADR-0775; REQ-057).

`docs/guides/reference.md` is listed in this repository's `agk.toml` `[flow] shared_indexes`
beside the five defaults of `session_plan.SHARED_INDEXES`, so a clean merge whose only re-prove
file is the reference takes the light re-prove of SPEC-0050 amendment 171. A set list replaces the
default (rule 3, `Q-RL-2`), so the list must keep all five; `merge_cleared.py` runs the
reference's whole-file command test on every would-be merge (`[testing] pre_merge_tests`,
`Q-RL-3`); and the list never widens to code, a decision record or a pattern without a change of
this test (answer 8). The kit default stays the five (`Q-RL-1`). Every git test runs in
`tmp_path` on invented files; no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path

import pytest
from conftest import KIT_ROOT

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import merge_cleared  # noqa: E402
import session_plan  # noqa: E402
from common import CheckError  # noqa: E402

REFERENCE = "docs/guides/reference.md"
REFERENCE_TEST = "tests/kit_dev/test_reference_commands.py"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Example",
    "GIT_AUTHOR_EMAIL": "example@example.com",
    "GIT_COMMITTER_NAME": "Example",
    "GIT_COMMITTER_EMAIL": "example@example.com",
}
GUIDE = "# Reference\n\n## First\n\n| a | one |\n\n## Middle\n\nText.\n\n## Last\n\n| z | two |\n"
BRANCH_ROW = GUIDE.replace("| a | one |\n", "| a | one |\n| b | the branch |\n")
MAIN_ROW = GUIDE.replace("| z | two |\n", "| z | two |\n| y | main |\n")
SAME_ROW = GUIDE.replace("| a | one |\n", "| a | one |\n| b | main |\n")
SCRIPT = "scripts/agk/example.py"
CODE = "".join(f"# line {i}\n" for i in range(1, 6))


def config() -> dict:
    return tomllib.loads((KIT_ROOT / "agk.toml").read_text(encoding="utf-8"))


def listed() -> list[str]:
    return config().get("flow", {}).get("shared_indexes", [])


# answer 3 and answer 8: the guard of this repository's list


def test_the_list_keeps_every_default_and_adds_the_reference():
    value = listed()
    missing = [p for p in (*session_plan.SHARED_INDEXES, REFERENCE) if p not in value]
    assert not missing, f"[flow] shared_indexes of agk.toml lacks {missing}"
    assert session_plan.shared_indexes(KIT_ROOT) == value
    assert merge_cleared.shared_of(config()) == value


def test_the_kit_default_stays_the_five():
    assert REFERENCE not in session_plan.SHARED_INDEXES
    assert len(session_plan.SHARED_INDEXES) == 5


def test_each_listed_path_is_a_tracked_file_and_never_a_decision_record():
    tracked = set(
        subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "ls-files"], cwd=KIT_ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    )
    for path in listed():
        assert path in tracked, path
        assert not path.startswith(("docs/specs/", "docs/adr/")), path
        assert not session_plan.has_wildcard(path) and not path.endswith("/"), path


def test_the_merge_runs_the_reference_command_test():
    tests = config()["testing"]["pre_merge_tests"]
    assert REFERENCE_TEST in tests
    assert all((KIT_ROOT / name).is_file() for name in tests)


# answers 5 to 7: what the list does on a merge


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True,
        env={**os.environ, **GIT_ENV},
    ).stdout.strip()  # fmt: skip


def commit(root: Path, files: dict, message: str) -> str:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def world(tmp_path: Path, head_files: dict, main_files: dict) -> tuple[Path, str, str]:
    """A checkout whose `main` and branch `feature` each change the shared base: (the checkout,
    the branch's head, main's head)."""
    root = tmp_path / "work"
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    commit(root, {REFERENCE: GUIDE, SCRIPT: CODE, "agk.toml": CODE}, "base")
    git(root, "checkout", "-q", "-b", "feature")
    head = commit(root, {**head_files, "docs/feature.md": "the feature\n"}, "feature")
    git(root, "checkout", "-q", "main")
    main = commit(root, main_files, "main")
    return root, head, main


def merged(root: Path, head: str, main: str, extra: dict | None = None) -> str:
    """The merge commit of MAIN into HEAD (first parent HEAD), with EXTRA on top when given."""
    git(root, "checkout", "-q", "--detach", head)
    git(root, "merge", "-q", "--no-ff", "--no-edit", main)
    if extra:
        for name, text in extra.items():
            (root / name).write_text(text, encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-q", "--amend", "--no-edit")
    sha = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-q", "main")
    return sha


FIVE = list(session_plan.SHARED_INDEXES)
SIX = [*FIVE, REFERENCE]


def test_rows_in_two_sections_are_full_with_the_five_and_light_with_this_list(tmp_path):
    root, head, _ = world(tmp_path, {REFERENCE: BRANCH_ROW}, {REFERENCE: MAIN_ROW})
    assert session_plan.reprove_kind(root, "main", head, FIVE) == ("full", [REFERENCE])
    assert session_plan.reprove_kind(root, "main", head, listed()) == ("light", [REFERENCE])


def test_the_same_row_is_a_conflict(tmp_path):
    root, head, _ = world(tmp_path, {REFERENCE: BRANCH_ROW}, {REFERENCE: SAME_ROW})
    assert session_plan.reprove_kind(root, "main", head, SIX) == ("conflict", [REFERENCE])


def test_a_code_file_beside_the_reference_is_full(tmp_path):
    root, head, _ = world(
        tmp_path,
        {REFERENCE: BRANCH_ROW, SCRIPT: CODE.replace("line 1", "the branch")},
        {REFERENCE: MAIN_ROW, SCRIPT: CODE.replace("line 5", "main")},
    )
    assert session_plan.reprove_kind(root, "main", head, SIX) == (
        "full",
        [REFERENCE, SCRIPT],
    )


def test_light_merge_holds_only_for_the_clean_merge_tree(tmp_path):
    root, head, main = world(tmp_path, {REFERENCE: BRANCH_ROW}, {REFERENCE: MAIN_ROW})
    clean = merged(root, head, main)
    assert session_plan.light_merge(root, head, clean, "main", SIX)
    assert not session_plan.light_merge(root, head, clean, "main", FIVE)
    more = merged(root, head, main, {"docs/feature.md": "something more\n"})
    assert not session_plan.light_merge(root, head, more, "main", SIX)


def test_a_list_of_the_reference_alone_replaces_the_default(tmp_path):
    root, head, _ = world(
        tmp_path,
        {"agk.toml": CODE.replace("line 1", "x")},
        {"agk.toml": CODE.replace("line 5", "y")},
    )
    assert session_plan.reprove_kind(root, "main", head, FIVE) == ("light", ["agk.toml"])
    assert session_plan.reprove_kind(root, "main", head, [REFERENCE]) == ("full", ["agk.toml"])


def flow_root(tmp_path: Path, line: str | None) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    text = "[flow]\n" + (f"shared_indexes = {line}\n" if line is not None else "")
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def test_an_absent_setting_is_the_five(tmp_path):
    assert session_plan.shared_indexes(flow_root(tmp_path, None)) == FIVE
    assert merge_cleared.shared_of({"flow": {}}) == FIVE


@pytest.mark.parametrize(
    "line,value",
    [
        ('"docs/guides/reference.md"', "docs/guides/reference.md"),
        ('["agk.toml", ""]', ["agk.toml", ""]),
        ('["docs/guides/*.md"]', ["docs/guides/*.md"]),
        ('["docs/guides/"]', ["docs/guides/"]),
    ],
)
def test_a_value_that_is_not_exact_paths_is_refused_naming_the_setting(tmp_path, line, value):
    with pytest.raises(CheckError) as caught:
        session_plan.shared_indexes(flow_root(tmp_path, line))
    assert (
        str(caught.value) == "setting: flow.shared_indexes must be a list of exact repository paths"
    )
    assert "docs/guides" not in str(caught.value)
    assert merge_cleared.shared_of({"flow": {"shared_indexes": value}}) is None
