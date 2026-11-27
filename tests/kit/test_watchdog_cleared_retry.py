"""The supervisor's pass retries a cleared, not merged head once per new head or base (REQ-046).

Brief #2058 (ADR-0856) answer 3 (SPEC-0039 rule 9): after `pass_facts`, the pass reads the review
queue once with `--all`; a `#<n> <head7> cleared, not merged` line whose (number, head, default
branch commit) differs from the one the pass state kept for that number adds
`a cleared head is not merged` to the reasons of the pass, so a conductor job starts and runs
`merge_cleared.py` again. The same triple starts none; a new default-branch commit or a new head
starts one. A queue or a commit that cannot be read starts none and keeps nothing. Stubbed reads,
invented data, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import session  # noqa: E402

REPO = "example/project"
BASE, NEWER = "1" * 40, "2" * 40


@pytest.fixture
def reads(monkeypatch, tmp_path):
    """The queue prints FOUND["queue"]; the default branch's commit is FOUND["base"]."""
    found = {"queue": "#9 abcdef1 cleared, not merged\n#10 1234567 review: new head", "base": BASE}
    calls: list[str] = []

    def queue(root, mode):
        calls.append(mode)
        if found["queue"] is None:
            raise session.CheckError("rule 3: the open pull requests cannot be read")
        print(found["queue"])
        return 0

    def gh(endpoint, *extra, method="GET"):
        assert endpoint == f"repos/{REPO}/commits/main" and method == "GET"
        return None if found["base"] is None else {"sha": found["base"]}

    monkeypatch.setattr(session, "review_queue", queue)
    monkeypatch.setattr(session, "gh", gh)
    monkeypatch.setattr(conductor.launch, "default_branch", lambda root: "main")
    found["calls"] = calls
    return found


def test_a_cleared_not_merged_line_starts_one_job_and_keeps_its_triple(reads, tmp_path):
    state: dict = {}
    seen = conductor.cleared_due(tmp_path, REPO, state)
    assert seen == {"9": f"abcdef1 {BASE}"}
    assert reads["calls"] == ["--all"]
    assert conductor.CLEARED_WHY == "a cleared head is not merged"


def test_the_same_triple_starts_none(reads, tmp_path):
    state = {"cleared": {"9": f"abcdef1 {BASE}"}}
    assert conductor.cleared_due(tmp_path, REPO, state) is None


def test_a_new_default_branch_commit_starts_one(reads, tmp_path):
    state = {"cleared": {"9": f"abcdef1 {BASE}"}}
    reads["base"] = NEWER
    assert conductor.cleared_due(tmp_path, REPO, state) == {"9": f"abcdef1 {NEWER}"}


def test_a_new_head_starts_one(reads, tmp_path):
    state = {"cleared": {"9": f"abcdef1 {BASE}"}}
    reads["queue"] = "#9 fedcba9 cleared, not merged"
    assert conductor.cleared_due(tmp_path, REPO, state) == {"9": f"fedcba9 {BASE}"}


def test_no_cleared_line_starts_none(reads, tmp_path):
    reads["queue"] = "empty"
    assert conductor.cleared_due(tmp_path, REPO, {"cleared": {"9": "x"}}) is None


@pytest.mark.parametrize("gone", ["queue", "base"])
def test_an_unreadable_queue_or_commit_starts_none(reads, tmp_path, gone):
    reads[gone] = None
    assert conductor.cleared_due(tmp_path, REPO, {}) is None


def test_the_pass_reads_it_after_pass_facts_and_keeps_it_only_with_a_started_job():
    import inspect

    source = inspect.getsource(conductor.watchdog_pass)
    assert source.index("pass_facts(root)") < source.index("cleared_due(root, repo, state)")
    assert "(CLEARED_WHY, cleared is not None)" in source
    assert source.index("conductor_job(") < source.index("cleared=cleared")
