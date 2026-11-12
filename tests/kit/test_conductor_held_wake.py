"""conductor.py watch ends on a held review (brief #1125, ADR-0482; REQ-039).

When a poll of `watch` finds no new line, and at most once per 5 minutes, it returns the
`HELD VERDICT #<n>` of each open, ready pull request whose ready report waits with no verdict on its
head (`held_verdict_line`, brief #854); one held pull request is returned again only after a further
`HELD_MINUTES`. The marks live in the git directory, never tracked. A `gh` stub serves saved copies
of the GitHub responses; invented names, no network, GET only.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_conductor_commands import SHA, SHORT, ago, pr, proj, run, serve_pr, stub  # noqa: F401
from test_pool_health import Clock
from test_session import REPO, comment

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import conductor  # noqa: E402

READY = f"Report: {SHORT} ready for review"


@pytest.fixture(autouse=True)
def judged(request):
    """The proof check is required, so a green proof run is a green head (`check_state`)."""
    if "proj" in request.fixturenames:
        toml = 'required_checks = ["proof"]\n[flow]\nconductor_poll_seconds = 1\n'
        request.getfixturevalue("proj").write("agk.toml", toml)


def watch_once(proj, stub) -> list[str]:  # noqa: F811
    out = run(proj, stub, "watch", "--since", ago(1), "--once")
    assert out.returncode == 0, out.stderr
    assert all(c[0] == "GET" for c in stub.calls())
    return out.stdout.splitlines()


def mark(proj) -> Path:  # noqa: F811
    return proj.root / ".git" / "agk" / "held"


def write_mark(proj, checked: int, said: dict[int, int]) -> None:  # noqa: F811
    stamp = lambda minutes: ago(minutes)  # noqa: E731
    mark(proj).parent.mkdir(parents=True, exist_ok=True)
    data = {"checked": stamp(checked), "said": {str(n): stamp(m) for n, m in said.items()}}
    mark(proj).write_text(json.dumps(data), encoding="utf-8")


def waiting(stub, draft: bool = False, extra: list | None = None) -> None:  # noqa: F811
    serve_pr(stub, pr(7, draft=draft), [comment(1, "builder", READY, ago(20)), *(extra or [])])


def test_1125a_a_ready_green_head_waiting_20_minutes_ends_the_watch(proj, stub):  # noqa: F811
    """REQ-039: brief #1125 answer 1 and test (a)."""
    waiting(stub)
    assert watch_once(proj, stub) == ["HELD VERDICT #7"]
    said = json.loads(mark(proj).read_text(encoding="utf-8"))
    assert set(said) == {"checked", "said"} and set(said["said"]) == {"7"}


def test_1125b_a_verdict_on_the_head_holds_nothing(proj, stub):  # noqa: F811
    """REQ-039: brief #1125 test (b)."""
    waiting(stub, extra=[comment(2, "boss", f"Verdict: fix list {SHA}\n\n1. A finding.", ago(18))])
    assert watch_once(proj, stub) == ["nothing new"]


def test_1125c_a_draft_holds_nothing(proj, stub):  # noqa: F811
    """REQ-039: brief #1125 test (c)."""
    waiting(stub, draft=True)
    assert watch_once(proj, stub) == ["nothing new"]


def test_1125d_the_check_runs_at_most_once_per_5_minutes(proj, stub):  # noqa: F811
    """REQ-039: brief #1125 test (d): after a check 4 minutes ago no head's checks are read."""
    waiting(stub)
    write_mark(proj, checked=4, said={})
    assert watch_once(proj, stub) == ["nothing new"]
    assert not any("/check-runs" in str(c[1]) for c in stub.calls())
    write_mark(proj, checked=6, said={})
    assert watch_once(proj, stub) == ["HELD VERDICT #7"]


def test_1125d_a_returned_pull_request_returns_again_only_after_held_minutes(proj, stub):  # noqa: F811
    """REQ-039: brief #1125 answer 1: once returned, again only after a further HELD_MINUTES."""
    waiting(stub)
    assert watch_once(proj, stub) == ["HELD VERDICT #7"]
    write_mark(proj, checked=6, said={7: 10})
    assert watch_once(proj, stub) == ["nothing new"]
    write_mark(proj, checked=6, said={7: conductor.HELD_MINUTES + 1})
    assert watch_once(proj, stub) == ["HELD VERDICT #7"]


def test_1125d_a_new_line_wins_and_the_held_check_waits(proj, stub):  # noqa: F811
    """REQ-039: brief #1125 answer 1: the check runs only when a poll finds no new line."""
    said = [comment(1, "builder", READY, ago(20)), comment(2, "x", "Report: y", ago(0))]
    serve_pr(stub, pr(7), said)
    assert watch_once(proj, stub) == ["7 Report: y"]
    assert not mark(proj).exists()


def test_1125_a_held_line_ends_the_bounded_watch_before_its_tick(monkeypatch, capsys):
    """REQ-039: the polling watch returns the held line the way it returns a new line."""
    clock = Clock()
    checks: list[float] = []

    def held(root, repo):
        checks.append(clock.spent)
        return ["HELD VERDICT #7"]

    monkeypatch.setattr(conductor, "time", clock)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    monkeypatch.setattr(conductor, "spec_approvers", lambda root: [])
    monkeypatch.setattr(conductor, "new_lines", lambda repo, since, approvers=(): [])
    monkeypatch.setattr(conductor, "renew_lease", lambda root: 0)
    monkeypatch.setattr(conductor, "green_lines", lambda root, repo, since: [])
    monkeypatch.setattr(conductor, "stall_report", lambda root, repo: [])
    monkeypatch.setattr(conductor, "sweep_late", lambda root, repo: [])
    monkeypatch.setattr(conductor, "held_lines", held)
    assert conductor.watch("root", datetime.now(UTC) - timedelta(minutes=1), False) == 0
    assert capsys.readouterr().out.strip() == "HELD VERDICT #7"
    assert checks and checks[0] <= 300
