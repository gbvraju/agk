"""session.py watch wakes on an answer to the builder's question or an approval of its head
(brief #1112, ADR-0475; REQ-039).

After the builder's own `Question: Q-…`, a later `Answer:` or `Maintainer answer:` naming that id
by a listed verdict author or spec approver prints `answer <Q-id> (comment <id>)`; an
`Approve: <head> SPEC-nnnn` by a spec approver naming the current head prints `approve <head7>
SPEC-nnnn`. A `gh` stub serves saved copies of the GitHub responses; invented names, no network.
"""

from __future__ import annotations

import pytest
from test_session import SHA, Stub, comment, pull, session, watching

WATCH = ("watch", "--pr", "7", "--interval", "0", "--timeout", "5")
QUIET = ("watch", "--pr", "7", "--interval", "0", "--timeout", "0")
REPO = "acme/widgets"
ASKED = comment(10, "builder", "Question: Q-7-1 which reading?\n\nThe brief leaves it open.")


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write(
        "config/reviewers.yaml",
        "version: 1\nverdict_authors: [boss, second]\nspec_approvers: [owner]\n",
    )
    return repo


def test_1112d_an_answer_to_the_builders_own_question_ends_the_watch(proj, stub):
    """REQ-039: brief #1112 answer 2 and test (d)."""
    said = comment(11, "owner", "Maintainer answer: Q-7-1 the narrower one")
    watching(stub, [(pull(), [ASKED]), (pull(), [ASKED, said])], base=[ASKED])
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == "answer Q-7-1 (comment 11)"
    assert all(c[0] == "GET" for c in stub.calls())


def test_1112d_an_answer_by_a_verdict_author_counts_too(proj, stub):
    """REQ-039: brief #1112 answer 2 (a listed answerer)."""
    said = comment(11, "Boss", "Answer: Q-7-1 the narrower one")
    watching(stub, [(pull(), [ASKED, said])], base=[ASKED])
    out = session(proj, stub, *QUIET)
    assert out.stdout.strip() == "answer Q-7-1 (comment 11)"


def test_1112d_an_answer_posted_before_the_watch_started_is_printed_once(proj, stub, tmp_path):
    """REQ-039: brief #1112 answer 2: the floor of verdicts and corrections (the last `Report:`)."""
    said = comment(11, "owner", "Maintainer answer: Q-7-1 the narrower one")
    watching(stub, [(pull(), [ASKED, said])], base=[ASKED, said])
    out = session(proj, stub, *QUIET)
    assert out.stdout.strip() == "answer Q-7-1 (comment 11)"
    reported = comment(12, "builder", f"Report: {SHA[:7]} ready for review (Q-7-1 applied)")
    (tmp_path / "again").mkdir()
    again = Stub(tmp_path / "again")
    watching(again, [(pull(), [ASKED, said, reported])], base=[ASKED, said, reported])
    out = session(proj, again, *QUIET)
    assert out.returncode == 3 and out.stdout.strip() == "timeout"
    (tmp_path / "later").mkdir()
    later = Stub(tmp_path / "later")
    watching(later, [(pull(), [ASKED, said])], base=[ASKED, said])
    out = session(proj, later, *QUIET, "--since", "11")
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


@pytest.mark.parametrize(
    "said",
    [
        comment(11, "owner", "Maintainer answer: Q-7-2 another question"),
        comment(11, "stranger", "Answer: Q-7-1 not a listed answerer"),
        comment(11, "owner", "Answer: no id at all"),
        comment(11, "owner", "Q-7-1: answered in other words"),
    ],
)
def test_1112e_an_answer_to_another_question_or_by_another_author_prints_nothing(
    proj, stub, said
):
    """REQ-039: brief #1112 test (e)."""
    watching(stub, [(pull(), [ASKED, said])], base=[ASKED])
    out = session(proj, stub, *QUIET)
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


def test_1112e_an_answer_to_someone_elses_question_prints_nothing(proj, stub):
    """REQ-039: brief #1112 test (e): only the pull request author's own question."""
    other = comment(10, "visitor", "Question: Q-7-1 may I ask?")
    said = comment(11, "owner", "Maintainer answer: Q-7-1 yes")
    watching(stub, [(pull(), [other, said])], base=[other])
    out = session(proj, stub, *QUIET)
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


def test_1112e_an_answer_older_than_the_question_prints_nothing(proj, stub):
    """REQ-039: brief #1112 answer 2 (a later answer)."""
    said = comment(9, "owner", "Maintainer answer: Q-7-1 before it was asked")
    watching(stub, [(pull(), [said, ASKED])], base=[])
    out = session(proj, stub, *QUIET)
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


def test_1112f_an_approve_of_the_current_head_ends_the_watch(proj, stub):
    """REQ-039: brief #1112 answer 2 and test (f)."""
    said = comment(11, "Owner", f"Approve: {SHA[:9]} SPEC-0042")
    watching(stub, [(pull(), []), (pull(), [said])], base=[])
    out = session(proj, stub, *WATCH)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == f"approve {SHA[:7]} SPEC-0042"


@pytest.mark.parametrize(
    "said",
    [
        comment(11, "owner", "Approve: 0123456 SPEC-0042"),
        comment(11, "boss", f"Approve: {SHA[:7]} SPEC-0042"),
        comment(11, "owner", f"note\nApprove: {SHA[:7]} SPEC-0042"),
    ],
)
def test_1112f_an_approve_of_an_older_head_or_by_another_author_prints_nothing(proj, stub, said):
    """REQ-039: brief #1112 test (f)."""
    watching(stub, [(pull(), [said])], base=[])
    out = session(proj, stub, *QUIET)
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


def test_1112f_an_approve_already_there_when_the_watch_started_is_not_printed_again(proj, stub):
    """REQ-039: brief #1112 answer 2 (printed once: an approval needs no change, so a restarted
    watch does not wake on it again)."""
    said = comment(11, "owner", f"Approve: {SHA[:7]} SPEC-0042")
    watching(stub, [(pull(), [said])], base=[said])
    out = session(proj, stub, *QUIET)
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


# --- a wait ends at its timeout (brief #1368, found bug #1297) ----------------------------------


class Clock:
    """A fake clock for the module under test: `sleep` moves `monotonic` on; the rest is real."""

    def __init__(self) -> None:
        self.now = self.start = 1000.0
        self.naps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.naps.append(seconds)
        self.now += max(0.0, seconds)

    def __getattr__(self, name: str):
        import time

        return getattr(time, name)


def quiet_module(monkeypatch, issues: list | None = None):
    """session.py in this process with the fake clock and a quiet GitHub: an open pull request
    that never changes, no comments; GET only."""
    import sys

    from test_session import SCRIPTS

    sys.path.insert(0, str(SCRIPTS))
    import session as mod

    clock = Clock()
    monkeypatch.setattr(mod, "time", clock)
    monkeypatch.setattr(mod, "repo_name", lambda root: REPO)
    monkeypatch.setattr(mod, "gh", lambda endpoint, *a, **k: pull())
    monkeypatch.setattr(
        mod, "pages", lambda endpoint: list(issues or []) if "labels=" in endpoint else []
    )
    return mod, clock


@pytest.mark.parametrize("interval", ["60", "45", "300"])
def test_1368_watch_pr_ends_within_a_second_of_its_timeout(proj, monkeypatch, capsys, interval):
    """REQ-050: brief #1368 answer 2; `watch --pr 7 --interval <n> --timeout 90` on a quiet pull
    request ends by 91 s on the fake clock, never a whole interval past it."""
    mod, clock = quiet_module(monkeypatch)
    args = {"--pr": "7", "--interval": interval, "--timeout": "90"}
    assert mod.watch(proj.root, args) == 3
    assert capsys.readouterr().out.strip() == "timeout"
    assert 90 <= clock.now - clock.start <= 91, clock.naps


@pytest.mark.parametrize("interval", ["60", "45", "300"])
def test_1368_watch_assign_ends_within_a_second_of_its_timeout(
    proj, monkeypatch, capsys, interval
):
    """REQ-050: brief #1368 answer 2; `watch --assign` with `--timeout 90` ends by 91 s with its
    end line unchanged."""
    mod, clock = quiet_module(monkeypatch, [{"number": 3, "title": "conductor"}])
    args = {"--interval": interval, "--timeout": "90"}
    assert mod.wait_assign(proj.root, "s-me", args) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "assign-timeout"
    assert 90 <= clock.now - clock.start <= 91, clock.naps


def test_1368_a_wait_never_spins_past_its_timeout_without_a_floor(proj, monkeypatch, capsys):
    """REQ-050: brief #1368 answer 2; every pause is at least one second (or the interval when it
    is shorter), so a wait at its bound never polls in a tight loop."""
    mod, clock = quiet_module(monkeypatch)
    args = {"--pr": "7", "--interval": "60", "--timeout": "60.5"}
    assert mod.watch(proj.root, args) == 3
    assert all(n >= 1 for n in clock.naps), clock.naps
    assert 60.5 <= clock.now - clock.start <= 61.5, clock.naps
