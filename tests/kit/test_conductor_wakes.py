"""conductor.py watch wakes on an owner's answer or approval (brief #1112, ADR-0475; REQ-039).

`new_lines` also returns a new `Answer: Q-…` or `Maintainer answer: Q-…` and a new `Approve:` by a
spec approver; `waiting_on` keeps reading `Question:` and `Report:` only. A `gh` stub serves saved
copies of the GitHub responses; invented names, no network, GET only.
"""

from __future__ import annotations

import sys
from pathlib import Path

from test_conductor_commands import SHORT, ago, brief, pr, proj, run, serve_pr, stub  # noqa: F401
from test_session import REPO, comment

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import conductor  # noqa: E402


def watch_once(proj, stub) -> list[str]:  # noqa: F811
    out = run(proj, stub, "watch", "--since", ago(60), "--once")
    assert out.returncode == 0, out.stderr
    assert all(c[0] == "GET" for c in stub.calls())
    return out.stdout.splitlines()


def test_1112a_a_maintainer_answer_or_an_answer_naming_a_q_id_wakes_the_watch(proj, stub):  # noqa: F811
    """REQ-039: brief #1112 answer 1 and test (a)."""
    stub.serve(f"repos/{REPO}/issues", [brief(9)])
    stub.serve(
        f"repos/{REPO}/issues/9/comments",
        [
            comment(1, "builder", "Question: Q-9-1 which spec?", ago(20)),
            comment(2, "owner", "Maintainer answer: Q-9-1 the second one\n\nmore", ago(5)),
            comment(3, "boss", "Answer: Q-9-2 yes", ago(4)),
            comment(4, "owner", "Answer: no id here", ago(3)),
            comment(5, "owner", "Maintainer answer: Q-9-3 too old", ago(120)),
        ],
    )
    assert watch_once(proj, stub) == [
        "9 Question: Q-9-1 which spec?",
        "9 Maintainer answer: Q-9-1 the second one",
        "9 Answer: Q-9-2 yes",
    ]


def test_1112b_an_approve_wakes_the_watch_only_from_a_spec_approver(proj, stub):  # noqa: F811
    """REQ-039: brief #1112 answer 1 and test (b)."""
    serve_pr(
        stub,
        pr(7),
        [
            comment(1, "owner", f"Approve: {SHORT} SPEC-0001", ago(5)),
            comment(2, "stranger", f"Approve: {SHORT} SPEC-0002", ago(4)),
            comment(3, "boss", f"Approve: {SHORT} SPEC-0003", ago(3)),
        ],
    )
    assert watch_once(proj, stub) == [f"7 Approve: {SHORT} SPEC-0001"]


def test_1112b_with_nothing_but_an_unlisted_approve_the_watch_has_nothing_new(proj, stub):  # noqa: F811
    """REQ-039: brief #1112 test (b), the other author wakes nothing."""
    serve_pr(stub, pr(7), [comment(1, "stranger", f"Approve: {SHORT} SPEC-0001", ago(5))])
    assert watch_once(proj, stub) == ["nothing new"]


def test_1112c_waiting_on_still_ignores_an_answer_and_an_approve():
    """REQ-039: brief #1112 answer 1 and test (c): `waiting_on` keeps `TRIGGERS`."""
    asked = comment(1, "builder", "Question: Q-9-1 which spec?", "2026-11-12T10:00:00Z")
    said = [
        asked,
        comment(2, "owner", "Maintainer answer: Q-9-1 the second", "2026-11-12T10:05:00Z"),
        comment(3, "owner", "Answer: Q-9-1 the second", "2026-11-12T10:06:00Z"),
        comment(4, "owner", f"Approve: {SHORT} SPEC-0001", "2026-11-12T10:07:00Z"),
    ]
    assert conductor.waiting_on(said, {"boss"}) == asked
    assert conductor.TRIGGERS == ("Question:", "Report:")
    assert conductor.WAKES[:2] == conductor.TRIGGERS
