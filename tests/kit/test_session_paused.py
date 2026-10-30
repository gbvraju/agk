"""session.py refuses claim, next, queue and watch while the default branch is paused (brief #348
build (c), Q-348-2; ADR-0218; REQ-009).

The setting is read on the default branch (`origin/<default_branch>`, which session rule 33's fetch
keeps current), never on the session's own branch, so a branch made before the pause merged is
still refused and the branch that adds the pause is not. No network: `gh` is the stub of
test_session.py, which records every call.
"""

from __future__ import annotations

import pytest
from test_session import REPO, Stub, session

LINE = "agk paused"
BASE_TOML = 'version = "0.60.0"\ndefault_branch = "main"\n'
PAUSED_TOML = BASE_TOML + "paused = true\n"
REFUSED = 5
COMMANDS = [
    ("claim", "--session", "b1", "--brief", "12", "--build", "c"),
    ("next", "--session", "b1"),
    ("queue", "--role", "builder"),
    ("watch", "--pr", "7", "--interval", "0", "--timeout", "1"),
    ("watch", "--merged", "7", "--interval", "0", "--timeout", "1"),
    ("watch", "--assign", "b1", "--interval", "0", "--timeout", "1"),
    ("after", "--session", "b1"),
]


@pytest.fixture
def stub(tmp_path) -> Stub:
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.commit(
        {
            "config/reviewers.yaml": "version: 1\nverdict_authors: [boss]\n",
            "agk.toml": BASE_TOML,
        },
        "base",
    )
    return repo


def default_branch(proj, toml: str) -> None:
    """Make origin/main a commit whose agk.toml is TOML, leaving the checkout as it is."""
    head = proj.git("rev-parse", "HEAD").strip()
    proj.write("agk.toml", toml)
    proj.git("commit", "-q", "--allow-empty", "-am", "default branch")
    proj.git("update-ref", "refs/remotes/origin/main", proj.git("rev-parse", "HEAD").strip())
    proj.git("reset", "-q", "--hard", head)


@pytest.mark.parametrize("args", COMMANDS, ids=lambda a: " ".join(a[:2]))
def test_each_command_is_refused_while_the_default_branch_is_paused(proj, stub, args):
    """REQ-009: Q-348-2 (claim, next, queue and watch take, list and wait on nothing)."""
    default_branch(proj, PAUSED_TOML)
    out = session(proj, stub, *args)
    assert out.returncode == REFUSED, out.stdout + out.stderr
    assert out.stdout.splitlines()[0].startswith(LINE)
    assert "setting: paused in agk.toml" in out.stdout
    assert stub.calls() == []  # nothing read, nothing posted


def test_a_branch_made_before_the_pause_is_still_refused(proj, stub):
    """REQ-009: Q-348-2 (the default branch decides, not the session's own branch)."""
    default_branch(proj, PAUSED_TOML)
    assert "paused" not in (proj.root / "agk.toml").read_text(encoding="utf-8")
    out = session(proj, stub, "queue", "--role", "builder")
    assert out.returncode == REFUSED
    assert stub.calls() == []


def test_the_branch_that_adds_the_pause_is_not_refused(proj, stub):
    """REQ-009: Q-348-2 (the pull request that pauses still claims, waits and is reviewed)."""
    default_branch(proj, BASE_TOML)
    proj.commit({"agk.toml": PAUSED_TOML}, "pause")
    stub.serve(f"repos/{REPO}/pulls", [])
    out = session(proj, stub, "queue", "--role", "builder")
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == "empty"


def test_removing_the_line_resumes(proj, stub):
    """REQ-009: answer 1 (removing the line resumes the kit)."""
    default_branch(proj, PAUSED_TOML)
    assert session(proj, stub, "queue", "--role", "builder").returncode == REFUSED
    default_branch(proj, BASE_TOML + "paused = false\n")
    stub.serve(f"repos/{REPO}/pulls", [])
    out = session(proj, stub, "queue", "--role", "builder")
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == "empty"


def test_without_a_fetched_default_branch_the_checkout_is_read(proj, stub):
    """REQ-009: Q-348-4 (no origin/<default_branch> ref: the checkout's agk.toml decides)."""
    proj.commit({"agk.toml": PAUSED_TOML}, "pause")
    out = session(proj, stub, "next", "--session", "b1")
    assert out.returncode == REFUSED
    assert stub.calls() == []


def test_a_bad_value_is_refused_by_the_setting_name_never_the_value(proj, stub):
    """REQ-009: answer 1 (a refusal names the setting, never the value; principle 8)."""
    default_branch(proj, BASE_TOML + 'paused = "sure-thing"\n')
    out = session(proj, stub, "queue", "--role", "builder")
    assert out.returncode == 2
    assert "setting: paused in agk.toml" in out.stdout
    assert "sure-thing" not in out.stdout + out.stderr
    assert stub.calls() == []


def test_the_other_commands_still_run_while_paused(proj, stub):
    """REQ-009: Q-348-2 names four commands; reading one's own messages is not refused."""
    default_branch(proj, PAUSED_TOML)
    out = session(proj, stub, "ids")
    assert out.returncode != REFUSED, out.stdout + out.stderr
    assert LINE not in out.stdout
    assert stub.calls()  # it went on to read GitHub
