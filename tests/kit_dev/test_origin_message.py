"""Kit-only tests of the message when `origin/<default branch>` cannot be read (issue #156, fix 5).

`intake.py ids` and `playbook.py start-ids` read the next numbers from `origin/<default branch>`.
With no remote the reason is the remote, not a missing requirements file. No network, no model.
"""

from __future__ import annotations

import pytest
from test_intake import SENTENCE
from test_intake import repo as intake_repo  # noqa: F401  (the fixture of test_intake)
from test_intake import run as intake_run
from test_playbook import run as playbook_run
from test_playbook import started as playbook_started  # noqa: F401  (the fixture of test_playbook)

TAIL = "cannot be read; steps 6 and 7 need the repository's remote"
OLD = "the base has no requirements file"


@pytest.fixture
def repo(request):
    return request.getfixturevalue("intake_repo")


@pytest.fixture
def started(request):
    return request.getfixturevalue("playbook_started")


def test_fix5_intake_ids_without_origin_says_the_remote_cannot_be_read(repo):
    """Issue #156 fix 5: no `origin` (the default ref is `origin/main`)."""
    proc = intake_run(repo, "ids", "--sentence", SENTENCE)
    assert proc.returncode == 1
    assert proc.stdout == f"FAIL intake: origin/main {TAIL}\n", proc.stdout
    assert OLD not in proc.stdout


def test_fix5_playbook_start_ids_without_origin_says_the_remote_cannot_be_read(started):
    """Issue #156 fix 5: the same for `start-ids` (its default ref is `origin/<default branch>`)."""
    proc = playbook_run("start-ids", "--statement", "A reading list.", "--root", str(started))
    assert proc.returncode == 1
    assert proc.stdout == f"FAIL playbook: origin/main {TAIL}\n", proc.stdout
    assert OLD not in proc.stdout


def test_fix5_a_readable_ref_without_a_requirements_file_keeps_its_own_message(started):
    """Issue #156 fix 5: only an unreadable `origin/` ref gets the new message."""
    (started / "docs" / "requirements.md").unlink()
    from conftest import git

    git(started, "add", "-A")
    git(started, "commit", "-q", "-m", "no requirements")
    proc = playbook_run(
        "start-ids", "--statement", "A reading list.", "--ref", "HEAD", "--root", str(started)
    )
    assert proc.returncode == 1 and OLD in proc.stdout and TAIL not in proc.stdout


def test_fix5_the_message_names_the_branch_of_agk_toml(started):
    """Issue #156 fix 5: the branch in the message is the configured default branch."""
    (started / "agk.toml").write_text('default_branch = "trunk"\n', encoding="utf-8")
    proc = playbook_run("start-ids", "--statement", "A reading list.", "--root", str(started))
    assert proc.stdout == f"FAIL playbook: origin/trunk {TAIL}\n", proc.stdout
