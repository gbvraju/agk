"""review_bundle.py: the one document a reviewer slot reads (brief #1013 answer 1, ADR-0431; REQ-046).

Saved REST replies through a `gh` stub on `PATH`, a git repository in `tmp_path`, invented names,
no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_session import REPO, clean_env, comment
from test_session import proj, stub  # noqa: F401  (the fixtures of test_session)

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "review_bundle.py"
PULL = f"repos/{REPO}/pulls/7"
ISSUES = f"repos/{REPO}/issues"
BRIEF_TEXT = "Sentence: \"The widget counts invented rows.\"\nAdvances: REQ-001\n"


@pytest.fixture
def world(proj, stub):  # noqa: F811
    """A pull request #7 of brief #5 whose head is this checkout's HEAD, with saved comments."""
    proj.commit(
        {
            "docs/requirements.md": "# Requirements\n\n### REQ-001\n\n- Status: Approved\n",
            "constitution/principles.md": "# Principles\n\n1. One.\n",
            "CLAUDE.md": "# Rules\n",
        },
        "base",
    )
    proj.branch("claude/brief-5")
    proj.commit({"widget.py": "ROWS = 3\n"}, "the widget")
    sha = proj.git("rev-parse", "HEAD").strip()
    body = "Brief: #5\nAdvances: REQ-001\nSummary: The widget counts rows.\n"
    stub.serve(
        PULL,
        {"number": 7, "body": body, "head": {"sha": sha}, "base": {"ref": "main"}},
    )
    stub.serve(f"{ISSUES}/5", {"number": 5, "body": BRIEF_TEXT})
    stub.serve(
        f"{ISSUES}/5/comments",
        [
            comment(11, "boss", "taken: s1 2026-11-10", "2026-11-10T09:00:00Z"),
            comment(12, "boss", "Answer: Q-5-1 three rows", "2026-11-10T09:05:00Z"),
            comment(13, "bot", "Progress: abc done 1/2; next: PROGRESS-TEXT", "2026-11-10T09:06:00Z"),
        ],
    )
    stub.serve(
        f"{ISSUES}/7/comments",
        [
            comment(21, "bot", f"Report: {sha[:7]} ready REPORT-TEXT", "2026-11-10T10:00:00Z"),
            comment(22, "boss", f"Verdict: fix list {sha}\n\n1. Name the rows.", "2026-11-10T10:10:00Z"),
            comment(23, "boss", "Correction: the rows are three", "2026-11-10T10:20:00Z"),
            comment(24, "owner", "Approve: abc SPEC-0001", "2026-11-10T10:30:00Z"),
            comment(25, "boss", "Maintainer answer: Q-5-2 yes", "2026-11-10T10:40:00Z"),
        ],
    )
    stub.serve(
        f"repos/{REPO}/commits/{sha}/check-runs",
        {
            "total_count": 2,
            "check_runs": [
                {"name": "tests", "status": "completed", "conclusion": "success"},
                {"name": "governance", "status": "completed", "conclusion": "failure"},
            ],
        },
    )
    return proj, stub, sha


def bundle(proj, stub, sha: str, *extra: str):
    env = clean_env()
    env.update(PATH=f"{stub.bin}{os.pathsep}{os.environ['PATH']}", GH_STUB_DIR=str(stub.dir))
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--pr", "7", "--sha", sha, "--base", "main", *extra],
        cwd=proj.root,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_a_the_bundle_holds_the_brief_and_the_rulings_and_no_progress_or_report(world):
    """REQ-046"""
    proj, stub, sha = world
    out = bundle(proj, stub, sha)
    assert out.returncode == 0, out.stdout + out.stderr
    text = out.stdout
    assert "# Review context" in text and "widget.py" in text  # review_context.py for the head
    assert "The widget counts invented rows." in text  # the brief's body
    for line in (
        "Answer: Q-5-1 three rows",
        f"Verdict: fix list {sha}",
        "Correction: the rows are three",
        "Approve: abc SPEC-0001",
        "Maintainer answer: Q-5-2 yes",
    ):
        assert line in text, line
    assert "boss at 2026-11-10T09:05:00Z" in text  # each ruling with its author and time
    assert "owner at 2026-11-10T10:30:00Z" in text
    assert "tests: success" in text and "governance: failure" in text  # the head's checks
    for hidden in ("PROGRESS-TEXT", "REPORT-TEXT", "taken: s1"):
        assert hidden not in text, hidden


def test_a_it_only_reads_and_reads_no_other_issue(world):
    """REQ-046"""
    proj, stub, sha = world
    assert bundle(proj, stub, sha).returncode == 0
    calls = stub.calls()
    assert {c[0] for c in calls} == {"GET"}
    issues = {c[1].split("?")[0] for c in calls if "/issues" in c[1]}
    assert issues == {f"{ISSUES}/5", f"{ISSUES}/5/comments", f"{ISSUES}/7/comments"}


def test_b_a_sha_that_is_not_the_head_is_refused_naming_the_rule(world):
    """REQ-046"""
    proj, stub, _ = world
    out = bundle(proj, stub, "b" * 40)
    assert out.returncode == 1
    assert "not the head of the pull request" in out.stdout and "ADR-0431" in out.stdout
    assert "# Review context" not in out.stdout


def test_b_a_checkout_that_is_not_at_the_head_is_refused(world):
    """REQ-046"""
    proj, stub, sha = world
    proj.commit({"widget.py": "ROWS = 4\n"}, "a later commit")
    out = bundle(proj, stub, sha)
    assert out.returncode == 1
    assert "the checkout is not at the head" in out.stdout


def test_b_a_malformed_sha_is_a_usage_error(world):
    """REQ-046"""
    proj, stub, sha = world
    out = bundle(proj, stub, sha[:12])
    assert out.returncode == 2
    assert stub.calls() == []


def test_c_the_same_inputs_give_the_same_bytes(world):
    """REQ-046"""
    proj, stub, sha = world
    first = bundle(proj, stub, sha)
    second = bundle(proj, stub, sha)
    assert first.returncode == 0
    assert first.stdout.encode() == second.stdout.encode()
