"""`conductor.py over --pr N`, the counts of an overrun and its cause (SPEC-0049 rules 8, 10 to 12,
brief #781, build (d), ADR-0366).

REQ-056 AC4 and AC5: from saved pull request data the command prints one count per line and the
cause of the first matching rule, in the order `loop`, `wander`, `estimate`, `blocked`, `unknown`;
evidence that cannot be read prints `unknown`, never 0. The guard allows exactly the one form and
the conductor's role file holds the stop, the parking and the lesson row. A `gh` stub serves saved
copies of the GitHub responses: invented data, no network, GET only, nothing written. The tests
were written first (answer 1).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import test_conductor_commands as tcc
from test_conductor_commands import ago, pr, run
from test_conductor_guard_queue import RULE, reason, run_hook
from test_session import REPO, comment

stub = tcc.stub  # the fixtures of the sweep tests, shared
proj = tcc.proj

BRIEF = 9
PULL = 5
GOOD = "src/app.py"
ROLE = Path(__file__).resolve().parents[2] / ".claude" / "agents" / "conductor.md"
GREEN = [{"name": "proof", "status": "completed", "conclusion": "success"}]
RED = [{"name": "proof", "status": "completed", "conclusion": "failure"}]
SKIPPED = [{"name": "proof", "status": "completed", "conclusion": "skipped"}]
KEYS = [
    "loop-red-heads",
    "loop-file-commits",
    "wander-files",
    "counted-hours",
    "blocked-hours",
    "unreadable",
]


def sha(n: int) -> str:
    return f"{n:040x}"


def serve(
    stub,
    commits: list[tuple] | None = None,
    pull_comments: list | None = None,
    brief_comments: list | None = None,
    files: tuple[str, ...] = (GOOD,),
    touches: str | None = "src/**",
) -> None:
    """One builder pull request; a commit is (runs, files, minutes ago[, number of parents])."""
    item = pr(PULL, body=f"Brief: #{BRIEF}\n")
    item["created_at"] = ago(290)
    stub.serve(f"repos/{REPO}/pulls/{PULL}", item)
    body = "Size: M\n" + (f"Touches: {touches}\n" if touches else "")
    stub.serve(f"repos/{REPO}/issues/{BRIEF}", {"number": BRIEF, "body": body})
    take = [comment(1, "builder", "taken: s1 2026-11-07", ago(300))]
    stub.serve(f"repos/{REPO}/issues/{BRIEF}/comments", take + (brief_comments or []))
    stub.serve(f"repos/{REPO}/issues/{PULL}/comments", pull_comments or [])
    stub.serve(f"repos/{REPO}/pulls/{PULL}/files", [{"filename": f} for f in files])
    listed = []
    for n, (runs, changed, minutes, *parents) in enumerate(commits or [], start=1):
        date = {"committer": {"date": ago(minutes)}}
        count = parents[0] if parents else 1
        listed.append({"sha": sha(n), "commit": date, "parents": [{"sha": "p"}] * count})
        stub.serve(f"repos/{REPO}/commits/{sha(n)}", {"files": [{"filename": f} for f in changed]})
        stub.serve(f"repos/{REPO}/commits/{sha(n)}/check-runs", {"check_runs": runs})
    stub.serve(f"repos/{REPO}/pulls/{PULL}/commits", listed)


def over(proj, stub) -> dict[str, str]:
    out = run(proj, stub, "over", "--pr", str(PULL))
    assert out.returncode == 0, out.stdout + out.stderr
    assert all(c[0] == "GET" for c in stub.calls())
    lines = out.stdout.splitlines()
    assert lines[0] == f"over #{PULL} brief #{BRIEF}"
    pairs = [line.split(" ") for line in lines[1:]]
    assert all(len(p) == 2 for p in pairs), lines
    assert [p[0] for p in pairs] == [*KEYS, "cause"]  # one line each, in this order
    return dict(pairs)


def test_loop_the_same_check_red_on_two_heads_in_a_row(proj, stub):
    """REQ-056 AC5: rule 12, `loop` by the check."""
    serve(stub, [(RED, ["a.py"], 200), (RED, ["b.py"], 100)], files=(GOOD,))
    found = over(proj, stub)
    assert found["loop-red-heads"] == "2"
    assert found["cause"] == "loop"


def test_a_green_head_breaks_the_run_of_red_heads(proj, stub):
    """REQ-056 AC5: rule 12, `in a row`."""
    serve(stub, [(RED, ["a.py"], 200), (GREEN, ["b.py"], 150), (RED, ["c.py"], 100)])
    found = over(proj, stub)
    assert found["loop-red-heads"] == "1"
    assert found["cause"] == "estimate"


def test_a_commit_with_no_run_or_only_skipped_runs_is_not_a_head(proj, stub):
    """REQ-056 AC5: rule 12, a checkpoint that was not a head does not break or lengthen a run."""
    commits = [(RED, ["a.py"], 200), ([], ["b.py"], 170), (SKIPPED, ["c.py"], 150), (RED, ["d.py"], 100)]
    serve(stub, commits)
    assert over(proj, stub)["loop-red-heads"] == "2"


def test_loop_the_same_file_in_three_commits_with_no_green_run_between(proj, stub):
    """REQ-056 AC5: rule 12, `loop` by the file."""
    serve(stub, [([], [GOOD], 200), ([], [GOOD], 150), ([], [GOOD], 100)])
    found = over(proj, stub)
    assert found["loop-file-commits"] == "3"
    assert found["cause"] == "loop"


def test_a_green_run_between_commits_resets_the_count_of_a_file(proj, stub):
    """REQ-056 AC5: rule 12, `no green run between`; a merge commit changes no file of the build."""
    commits = [
        ([], [GOOD], 200),
        (GREEN, [GOOD], 150),
        ([], [GOOD], 120),
        ([], [GOOD], 100, 2),  # a merge of the default branch
    ]
    serve(stub, commits)
    found = over(proj, stub)
    assert found["loop-file-commits"] == "2"
    assert found["cause"] == "estimate"


def test_wander_a_file_outside_the_touches_of_the_brief(proj, stub):
    """REQ-056 AC5: rule 12, `wander`, after `loop` in the order."""
    serve(stub, [(GREEN, ["x"], 100)], files=(GOOD, "docs/other.md", "docs/more.md"))
    found = over(proj, stub)
    assert found["wander-files"] == "2"
    assert found["cause"] == "wander"


def test_loop_goes_before_wander(proj, stub):
    """REQ-056 AC5: rule 12, the first matching rule in the order written."""
    serve(stub, [(RED, ["a"], 200), (RED, ["b"], 100)], files=("docs/other.md",))
    found = over(proj, stub)
    assert (found["wander-files"], found["cause"]) == ("1", "loop")


def test_estimate_when_no_rule_before_it_matches_and_little_is_blocked(proj, stub):
    """REQ-056 AC5: rule 12 `estimate`, Q-781-2's reading (at most half the hours blocked)."""
    serve(stub, [(GREEN, [GOOD], 100)])
    found = over(proj, stub)
    assert found == {
        "loop-red-heads": "0",
        "loop-file-commits": "1",
        "wander-files": "0",
        "counted-hours": found["counted-hours"],
        "blocked-hours": "0.0",
        "unreadable": "0",
        "cause": "estimate",
    }
    assert float(found["counted-hours"]) >= 4.9


@pytest.mark.parametrize("line", ["push refused by the proxy", "tool error in the runner"])
def test_blocked_when_more_than_half_the_hours_lie_after_a_reported_block(proj, stub, line):
    """REQ-056 AC5: rule 12 `blocked`, from the report to the next push."""
    said = [
        comment(11, "builder", f"Report: abc1234 {line}", ago(270)),
        comment(12, "builder", "Report: abc1234 over cap 5/4 hours", ago(20)),
    ]
    serve(stub, [(GREEN, [GOOD], 280), (GREEN, ["src/b.py"], 30)], said)
    found = over(proj, stub)
    assert (found["counted-hours"], found["blocked-hours"]) == ("4.7", "4.0")
    assert found["cause"] == "blocked"


def test_time_waiting_for_an_answer_is_neither_counted_nor_blocked(proj, stub):
    """REQ-056 AC5: rule 6 holds inside rule 12: the conductor's time is not the builder's."""
    said = [
        comment(11, "builder", "Question: Q-9-1 tool error in the runner", ago(270)),
        comment(12, "boss", "Verdict: fix list abc1234", ago(40)),
        comment(13, "builder", "Report: abc1234 over cap 5/4 hours", ago(20)),
    ]
    serve(stub, [(GREEN, [GOOD], 280), (GREEN, ["src/b.py"], 30)], said)
    found = over(proj, stub)
    assert (found["counted-hours"], found["blocked-hours"]) == ("0.8", "0.2")
    assert found["cause"] == "estimate"


def test_hours_after_the_over_cap_report_are_not_counted(proj, stub):
    """REQ-056 AC5: rule 6, the time a person takes to rule is not the builder's."""
    said = [comment(11, "builder", "Report: abc1234 over cap 5/4 hours", ago(240))]
    serve(stub, [(GREEN, [GOOD], 280)], said)
    assert over(proj, stub)["counted-hours"] == "1.0"


def test_unknown_when_the_commits_cannot_be_read_never_0(proj, stub):
    """REQ-056 AC5: answer 1, `unknown` and never 0."""
    serve(stub, [(GREEN, [GOOD], 100)])
    stub.serve(f"repos/{REPO}/pulls/{PULL}/commits", "FAIL")
    found = over(proj, stub)
    assert found["loop-red-heads"] == "unknown"
    assert found["loop-file-commits"] == "unknown"
    assert found["blocked-hours"] == "unknown"
    assert found["unreadable"] == "3"
    assert found["cause"] == "unknown"


def test_unknown_when_the_check_runs_of_a_head_cannot_be_read(proj, stub):
    """REQ-056 AC5: answer 1, a green run that cannot be read resets nothing."""
    serve(stub, [(GREEN, [GOOD], 100)])
    stub.serve(f"repos/{REPO}/commits/{sha(1)}/check-runs", "FAIL")
    found = over(proj, stub)
    assert (found["loop-red-heads"], found["loop-file-commits"]) == ("unknown", "unknown")
    assert found["cause"] == "unknown"


def test_unknown_when_a_commit_cannot_be_read(proj, stub):
    """REQ-056 AC5: answer 1."""
    serve(stub, [(GREEN, [GOOD], 100)])
    stub.serve(f"repos/{REPO}/commits/{sha(1)}", "FAIL")
    found = over(proj, stub)
    assert (found["loop-red-heads"], found["loop-file-commits"]) == ("0", "unknown")
    assert found["cause"] == "unknown"


def test_unknown_when_the_brief_has_no_touches_line(proj, stub):
    """REQ-056 AC5: answer 1, `wander` has no evidence, so the walk stops there."""
    serve(stub, [(GREEN, [GOOD], 100)], touches=None)
    found = over(proj, stub)
    assert (found["wander-files"], found["cause"]) == ("unknown", "unknown")


def test_unknown_when_the_take_cannot_be_read(proj, stub):
    """REQ-056 AC5: rule 6, no take gives no hours; `estimate` needs them (Q-781-2)."""
    serve(stub, [(GREEN, [GOOD], 100)])
    stub.serve(f"repos/{REPO}/issues/{BRIEF}/comments", [])
    found = over(proj, stub)
    assert (found["counted-hours"], found["blocked-hours"]) == ("unknown", "unknown")
    assert found["cause"] == "unknown"


def test_a_rule_that_matches_goes_before_evidence_that_cannot_be_read(proj, stub):
    """REQ-056 AC5: rule 12, an unread count later in the walk does not undo a `loop`."""
    serve(stub, [(RED, ["a"], 200), (RED, ["b"], 100)], touches=None)
    found = over(proj, stub)
    assert (found["wander-files"], found["cause"]) == ("unknown", "loop")


def test_a_pull_request_that_cannot_be_read_prints_unknown_for_everything(proj, stub):
    """REQ-056 AC5: answer 1, and the command still exits 0 with the lines."""
    stub.serve(f"repos/{REPO}/pulls/{PULL}", "FAIL")
    out = run(proj, stub, "over", "--pr", str(PULL))
    assert out.returncode == 0, out.stderr
    lines = out.stdout.splitlines()
    assert lines[0] == f"over #{PULL} brief unknown"
    assert lines[-1] == "cause unknown"
    assert all(line.endswith(" unknown") for line in lines[1:4])


@pytest.mark.parametrize(
    "args",
    [["over"], ["over", "--pr"], ["over", "--pr", "x"], ["over", "--pr", "5", "--apply"]],
)
def test_another_form_of_the_command_is_refused(proj, stub, args):
    """REQ-056 AC5: answer 1."""
    out = run(proj, stub, *args)
    assert out.returncode == 2 and "usage:" in out.stderr
    assert stub.calls() == []


def test_the_command_writes_no_file(proj, stub):
    """REQ-056 AC5: rule 16, GET only and nothing written."""
    serve(stub, [(GREEN, [GOOD], 100)])
    before = sorted(p for p in proj.root.rglob("*") if ".git" not in p.parts)
    over(proj, stub)
    assert sorted(p for p in proj.root.rglob("*") if ".git" not in p.parts) == before


# --- the guard --------------------------------------------------------------------------------

CONDUCTOR = "scripts/agk/conductor.py"


@pytest.fixture
def guarded(tmp_path):
    root = tmp_path / "project"
    (root / "scripts" / "agk").mkdir(parents=True)
    (root / CONDUCTOR).write_text("print('the project script')\n", encoding="utf-8")
    (root / ".git").mkdir()
    return root


def test_the_guard_allows_exactly_the_one_form(guarded):
    """REQ-056 AC5: answer 1."""
    result = run_hook(f"python3 {CONDUCTOR} over --pr 12", guarded)
    assert result.returncode == 0 and result.stdout == "", result.stdout


@pytest.mark.parametrize(
    "rest",
    [
        "over",
        "over --pr",
        "over --pr x",
        "over --pr 12 --apply",
        "over --pr 12 13",
        "over 12",
        "over --since 12",
    ],
)
def test_the_guard_refuses_any_other_form(guarded, rest):
    """REQ-056 AC5: answer 1."""
    assert reason(run_hook(f"python3 {CONDUCTOR} {rest}", guarded).stdout) == RULE


def test_the_shadow_reviewer_may_not_run_it(guarded):
    """REQ-056 AC5: the allowance is the conductor's."""
    out = run_hook(f"python3 {CONDUCTOR} over --pr 12", guarded, shadow=True).stdout
    assert reason(out) is not None


# --- the conductor's role ---------------------------------------------------------------------


def role() -> str:
    return " ".join(ROLE.read_text(encoding="utf-8").split())


def test_the_role_sends_the_stop_on_an_over_line():
    """REQ-056 AC4: rule 8."""
    text = role()
    assert "`OVER` line" in text
    assert '--text "stop: over cap <used>/<cap> <unit>"' in text
    assert "newest `taken:` or `taken over:` comment" in text


def test_the_role_gives_no_clearing_verdict_while_parked():
    """REQ-056 AC4: rule 10."""
    text = role()
    assert "parked" in text and "no clearing verdict" in text
    assert "`over cap` report" in text


def test_the_role_records_one_lesson_row_with_its_cause():
    """REQ-056 AC5: rules 11 and 12, the row goes in a report or a brief, never a project file."""
    text = role()
    assert "`conductor.py over --pr <n>`" in text
    assert "`over-cap` row" in text
    assert "only with the count" in text
