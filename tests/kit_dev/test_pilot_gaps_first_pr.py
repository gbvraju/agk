"""Brief #263 build (b) (REQ-039): the first pull request of a new project, answers 4 to 6.

Kit-only: `playbook.py`, `intake.py`, `pr_body.py` and the skills are not installed in a project.
Answer 4 for `check_pr_body.py` itself is tested in `tests/kit/test_pilot_gaps.py`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env, git, make_repo
from test_intake import draft
from test_intake import repo as intake_repo  # noqa: F401 - a fixture, used by name
from test_intake import run as intake_run
from test_playbook import (
    good_start,
    started,  # noqa: F401 - a fixture, used by name
)
from test_playbook import run as playbook_run

sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import pr_body  # noqa: E402

SKILLS = KIT_ROOT / "skills"
WORKFLOW = KIT_ROOT / ".github" / "workflows" / "governance.yml"
RED_BODY = (
    'Sentence: "The default branch is red: the required checks of its head fail."\n'
    "Answers:\n1. Failing check: governance\n2. Head: abc\n3. Run: u\n"
    "Priority: 0\nAdvances: none\nTouches: **\nSize: S\n"
)


def red() -> dict:
    """The router's red-branch issue, as `route.red_body` writes it."""
    return {
        "number": 9,
        "title": "The default branch is red",
        "user": {"login": "github-actions[bot]"},
        "labels": [{"name": "agk-brief"}],
        "body": RED_BODY,
    }


def brief() -> dict:
    return {"number": 12, "title": "Brief: t", "labels": [{"name": "agk-brief"}], "body": "x\n"}


def skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


# --- answer 4: the red-branch issue is not a brief -----------------------------------------------


def test_answer4_the_prepared_body_needs_no_brief_line_for_the_red_branch_issue(tmp_path):
    """REQ-039: brief #263 answer 4 (`pr_body.open_briefs`, which the next steps of a skill use)."""
    saved = tmp_path / "briefs.json"
    saved.write_text(json.dumps([red()]), encoding="utf-8")
    assert pr_body.open_briefs(str(saved)) is False
    assert pr_body.brief_line(None, str(saved), None) is None
    saved.write_text(json.dumps([red(), brief()]), encoding="utf-8")
    assert pr_body.open_briefs(str(saved)) is True


def test_answer4_governance_saves_more_than_one_open_brief():
    """REQ-039: brief #263 answer 4 (with one brief per page, the red-branch issue could hide
    another open brief, and the body would pass without `Brief:`)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if "labels=agk-brief&state=open" in ln)
    found = re.search(r"per_page=(\d+)", line)
    assert found and int(found.group(1)) >= 2


# --- answer 5: the branch does not track the default branch; push HEAD -------------------------


@pytest.mark.parametrize("name", ["start", "spec"])
def test_answer5_the_skill_creates_its_branch_without_tracking_the_default_branch(name):
    """REQ-039: brief #263 answer 5."""
    lines = [ln for ln in skill(name).splitlines() if "git switch" in ln]
    assert lines, name
    for line in lines:
        assert "--no-track" in line, line


def test_answer5_the_vision_skill_names_the_branch_without_tracking():
    """REQ-039: brief #263 answer 5 (`/agk:vision` is `/agk:start` for an idea)."""
    assert "--no-track" in skill("vision")


def test_answer5_a_branch_made_as_the_skills_say_pushes_with_the_printed_command(tmp_path):
    """REQ-039: brief #263 answer 5: the printed push makes the branch on the remote, and the
    default branch of the remote is unchanged."""
    remote = make_repo(tmp_path / "remote")
    git(remote, "config", "receive.denyCurrentBranch", "ignore")
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True)
    git(work, "config", "user.email", "t@example.invalid")
    git(work, "config", "user.name", "t")
    git(work, "switch", "-q", "--no-track", "-c", "start/a-list", "origin/main")
    upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "start/a-list@{upstream}"],
        cwd=work,
        capture_output=True,
        text=True,
    )
    assert upstream.returncode != 0  # no upstream: a bare `git push` cannot offer HEAD:main
    (work / "a.md").write_text("a\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "a")
    before = subprocess.run(
        ["git", "rev-parse", "main"], cwd=remote, capture_output=True, text=True
    ).stdout
    git(work, "push", "-q", "-u", "origin", "HEAD")
    after = subprocess.run(
        ["git", "rev-parse", "main", "start/a-list"], cwd=remote, capture_output=True, text=True
    ).stdout.split()
    assert after[0] == before.strip() and len(after) == 2


def test_answer5_start_next_steps_print_push_head(started):  # noqa: F811
    """REQ-039: brief #263 answer 5."""
    good_start(started)
    proc = playbook_run("next-steps", "--base", "main", "--brief", "none", "--root", str(started))
    assert proc.returncode == 0, proc.stdout
    assert "git push -u origin HEAD\n" in proc.stdout
    assert "HEAD:main" not in proc.stdout and "origin start/" not in proc.stdout


def test_answer5_intake_next_steps_print_push_head(intake_repo):  # noqa: F811
    """REQ-039: brief #263 answer 5."""
    draft(intake_repo)
    proc = intake_run(intake_repo, "next-steps", "--base", "main", "--brief", "none")
    assert proc.returncode == 0, proc.stdout
    assert "git push -u origin HEAD\n" in proc.stdout
    assert "HEAD:main" not in proc.stdout and "origin intake/" not in proc.stdout


# --- answer 6: the charter is shown; the pull request is offered with the body file -------------


def fake_gh(tmp_path, code: int) -> dict[str, str]:
    """An environment whose `gh` answers `auth status` with CODE and does nothing else."""
    folder = tmp_path / f"bin{code}"
    folder.mkdir()
    gh = folder / "gh"
    gh.write_text(f'#!/bin/sh\n[ "$1 $2" = "auth status" ] && exit {code}\nexit 9\n')
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    env = clean_env()
    env["PATH"] = f"{folder}{os.pathsep}{env.get('PATH', '')}"
    return env


def next_steps(root, env):
    return subprocess.run(
        [
            sys.executable,
            str(KIT_ROOT / "scripts" / "agk" / "playbook.py"),
            "next-steps",
            "--base",
            "main",
            "--brief",
            "none",
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.mark.skipif(os.name == "nt", reason="the fake gh is a shell script")
def test_answer6_the_charter_and_the_vision_are_shown_before_the_commit_steps(
    started,
    tmp_path,  # noqa: F811
):
    """REQ-039: brief #263 answer 6."""
    good_start(started)
    out = next_steps(started, fake_gh(tmp_path, 1)).stdout
    commit = out.index("Commit message:")
    charter = out.index("docs/adr/0002-project-charter.md")
    assert charter < commit
    assert out.index("- Status: Proposed") < commit and out.index("**Milestones**") < commit
    assert out.index("## What this is for") < commit
    assert out.index("constitution/vision.md") < charter


@pytest.mark.skipif(os.name == "nt", reason="the fake gh is a shell script")
def test_answer6_with_gh_logged_in_the_pull_request_is_offered_with_the_body_file(
    started,
    tmp_path,  # noqa: F811
):
    """REQ-039: brief #263 answer 6."""
    good_start(started)
    proc = next_steps(started, fake_gh(tmp_path, 0))
    assert proc.returncode == 0, proc.stdout
    path = re.search(r"(?m)^Pull request body file: (.+)$", proc.stdout).group(1)
    offer = [ln for ln in proc.stdout.splitlines() if ln.startswith("gh pr create")]
    assert len(offer) == 1
    assert f'--body-file "{path}"' in offer[0] and "--base main" in offer[0]
    assert "--head" not in offer[0] or "start/a-reading-list" in offer[0]
    assert proc.stdout.index("git push -u origin HEAD") < proc.stdout.index("gh pr create")


@pytest.mark.skipif(os.name == "nt", reason="the fake gh is a shell script")
def test_answer6_without_gh_logged_in_no_gh_command_is_offered(started, tmp_path):  # noqa: F811
    """REQ-039: brief #263 answer 6 (`gh` not logged in, or not installed)."""
    good_start(started)
    proc = next_steps(started, fake_gh(tmp_path, 1))
    assert proc.returncode == 0 and "gh pr create" not in proc.stdout
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "git").symlink_to(shutil.which("git"))
    env = clean_env()
    env["PATH"] = str(bare)
    proc = next_steps(started, env)
    assert proc.returncode == 0 and "gh pr create" not in proc.stdout


def test_answer6_the_start_skill_shows_the_charter_and_never_opens_the_pull_request():
    """REQ-039: brief #263 answer 6 (the skill shows what the script prints; the person runs it)."""
    body = skill("start")
    assert "charter" in body and "before the commit steps" in body
    assert "Do not commit or push, and do not open a pull request" in body
