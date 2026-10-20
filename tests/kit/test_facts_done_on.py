"""Tests of `done_on` in scripts/agk/facts.py (SPEC-0017 rules 1 and 2, REQ-024). No network.

Each repository here is the `ok` fixture tree with `docs/requirements.md` changed by later commits
that carry a chosen committer date, so the history, not the work tree, gives the date.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

from test_facts import DROP, ENV_GIT, FACTS, NO_BACKGROUND_WORK, no_gh_path, tree_of

HEADER = "# Requirements\n\n"
ONE = "### REQ-001 — First thing\n\n- Acceptance: AC1 given a, when b, then c\n- Status: {}\n\n"
TWO = "### REQ-002 — Second thing\n\n- Acceptance: AC1 given g, when h, then i\n- Status: {}\n"


def git(root: Path, *args: str, date: str = "2026-10-01T12:00:00+0000") -> str:
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = date
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *NO_BACKGROUND_WORK, *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return proc.stdout


def requirements(one: str, two: str) -> str:
    return HEADER + ONE.format(one) + TWO.format(two)


def commit(root: Path, one: str, two: str, date: str, message: str = "change") -> None:
    (root / "docs" / "requirements.md").write_text(requirements(one, two), encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message, date=date)


def repo(tmp_path: Path, one: str = "planned", two: str = "planned") -> Path:
    """The `ok` fixture tree committed once on 2026-09-01, with REQ-001 and REQ-002 as given."""
    root = tmp_path / "work"
    shutil.copytree(tree_of("ok"), root)
    (root / "docs" / "requirements.md").write_text(requirements(one, two), encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture", date="2026-09-01T12:00:00+0000")
    return root


def facts(root: Path, tmp_path: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in DROP} | ENV_GIT
    env["PATH"] = no_gh_path(tmp_path)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(FACTS), "--today", "2026-10-14", "--repo", "demo-org/demo-repo"]
        + [str(root)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def done_on(doc: dict) -> dict:
    return {r["id"]: r["done_on"] for r in doc["requirements"]}


def test_ac1_the_date_is_that_of_the_commit_that_set_the_status_to_done(tmp_path):
    """REQ-024 AC1: SPEC-0017 rule 1 (the committer date, UTC, of the commit that set `done`)."""
    root = repo(tmp_path)
    commit(root, "done", "planned", "2026-10-08T10:00:00+0000")
    commit(root, "done", "done", "2026-10-09T10:00:00+0000")
    assert done_on(facts(root, tmp_path)) == {"REQ-001": "2026-10-08", "REQ-002": "2026-10-09"}


def test_ac1_a_later_unrelated_change_does_not_move_the_date(tmp_path):
    """REQ-024 AC2: SPEC-0017 rule 1 (only a change to `done` counts, not an edit elsewhere)."""
    root = repo(tmp_path)
    commit(root, "done", "planned", "2026-09-10T10:00:00+0000")
    commit(root, "done", "in-progress", "2026-10-09T10:00:00+0000")
    assert done_on(facts(root, tmp_path))["REQ-001"] == "2026-09-10"


def test_ac3_the_latest_change_to_done_decides(tmp_path):
    """REQ-024 AC3: SPEC-0017 rule 1 (done, then planned, then done again)."""
    root = repo(tmp_path)
    commit(root, "done", "planned", "2026-09-10T10:00:00+0000")
    commit(root, "planned", "planned", "2026-09-20T10:00:00+0000")
    commit(root, "done", "planned", "2026-10-08T10:00:00+0000")
    assert done_on(facts(root, tmp_path))["REQ-001"] == "2026-10-08"


def test_ac1_the_committer_date_is_read_in_utc(tmp_path):
    """REQ-024 AC1: SPEC-0017 rule 1 (23:30 at UTC-5 is the next day in UTC)."""
    root = repo(tmp_path)
    commit(root, "done", "planned", "2026-10-08T23:30:00-0500")
    assert done_on(facts(root, tmp_path))["REQ-001"] == "2026-10-09"


def test_ac1_a_requirement_added_as_done_became_done_in_its_first_commit(tmp_path):
    """REQ-024 AC1: SPEC-0017 rule 1 (Q-S0017-2: the commit that created its section)."""
    root = repo(tmp_path, one="planned", two="planned")
    (root / "docs" / "requirements.md").write_text(
        requirements("planned", "planned") + "\n### REQ-003 — Third\n\n"
        "- Acceptance: AC1 given j, when k, then l\n- Status: done\n",
        encoding="utf-8",
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "add", date="2026-10-07T10:00:00+0000")
    assert done_on(facts(root, tmp_path))["REQ-003"] == "2026-10-07"


def test_ac1_the_first_parent_history_gives_the_merge_commit_date(tmp_path):
    """REQ-024 AC1: SPEC-0017 rule 1 (a merge of a branch is one change on the default branch)."""
    root = repo(tmp_path)
    git(root, "switch", "-q", "-c", "side")
    commit(root, "done", "planned", "2026-09-02T10:00:00+0000")
    git(root, "switch", "-q", "main")
    git(root, "merge", "-q", "--no-ff", "-m", "merge", "side", date="2026-10-08T10:00:00+0000")
    assert done_on(facts(root, tmp_path))["REQ-001"] == "2026-10-08"


def test_ac6_a_requirement_that_is_not_done_has_no_date_and_the_schema_is_still_1(tmp_path):
    """REQ-024 AC6: SPEC-0017 rule 2 (the field is `null`, not `unknown`, when nothing is done)."""
    root = repo(tmp_path)
    commit(root, "done", "planned", "2026-10-08T10:00:00+0000")
    doc = facts(root, tmp_path)
    assert doc["schema"] == 1
    assert done_on(doc) == {"REQ-001": "2026-10-08", "REQ-002": None}


def test_ac6_a_shallow_history_gives_unknown_for_every_done_requirement(tmp_path):
    """REQ-024 AC6: SPEC-0017 rule 1 (Q-S0017-1: `unknown` for every `done_on`, nothing more)."""
    (tmp_path / "o").mkdir()
    origin = repo(tmp_path / "o")
    commit(origin, "done", "done", "2026-10-08T10:00:00+0000")
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "-q", "--depth", "1", f"file://{origin}", str(shallow))
    assert git(shallow, "rev-parse", "--is-shallow-repository").strip() == "true"
    assert done_on(facts(shallow, tmp_path)) == {"REQ-001": "unknown", "REQ-002": "unknown"}


def test_ac1_a_done_requirement_with_no_change_to_done_in_history_is_unknown(tmp_path):
    """REQ-024 AC4: SPEC-0017 rule 1 (an uncommitted edit is no commit: `unknown`)."""
    root = repo(tmp_path)
    (root / "docs" / "requirements.md").write_text(
        requirements("done", "planned"), encoding="utf-8"
    )
    assert done_on(facts(root, tmp_path))["REQ-001"] == "unknown"


def test_ac1_the_same_history_gives_the_same_document_twice(tmp_path):
    """REQ-024 AC1: SPEC-0017 rule 1 (no clock, no network: a function of the history)."""
    root = repo(tmp_path)
    commit(root, "done", "done", "2026-10-08T10:00:00+0000")
    assert facts(root, tmp_path) == facts(root, tmp_path)
