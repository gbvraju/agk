"""The conductor's switch to `Assign:` lines and the stall ticks (brief #776 build (c); REQ-041).

`session.py plan` names slots, `doctor.py` prints and checks the schedule, `conductor.py watch`
ticks, `STALL` lines, the takeover of a stalled lease and the merge of main after a red branch.
Saved answers, invented names, no network.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_session import ISSUES, REPO, Stub, comment, issue, listing, posts
from test_session_flow import brief
from test_session_plan import data, free, plan

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import doctor as doctor_script  # noqa: E402

HEAD = "a" * 40
CHECK_RUNS = f"repos/{REPO}/commits/{HEAD}/check-runs?per_page=100"
ON = '[flow]\nbuilder_start = "assign"\nbuilder_slots = 2\nplan_issue = 61\n'


def stamp(minutes: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def said(cid: int, body: str, minutes: float = 1, login: str = "boss") -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": stamp(minutes)}


# --- the plan names slots (answer 1) ------------------------------------------------------------


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def two_briefs(proj, stub, slots: int = 2, third: bool = False) -> None:
    proj.write("agk.toml", f'[flow]\nbuilder_start = "assign"\nbuilder_slots = {slots}\n')
    numbers = [7, 8, 9] if third else [7, 8]
    listing(stub, [issue(n, brief(f"src/f{n}.py")) for n in numbers])
    free(stub, *numbers)


def test_with_assign_the_plan_starts_no_session_and_names_slots(proj, stub):
    """REQ-041: answer 1, `Assign:` lines in place of new session names."""
    two_briefs(proj, stub)
    found = data(proj, stub)
    assert found["start"] == []
    assert [(a["session"], a["brief"]) for a in found["assign"]] == [("s1", 7), ("s2", 8)]
    assert [a["line"] for a in found["assign"]] == ["Assign: s1 #7", "Assign: s2 #8"]
    assert posts(stub) == []


def test_the_words_of_the_plan_say_assign(proj, stub):
    """REQ-041"""
    two_briefs(proj, stub)
    out = plan(proj, stub).stdout
    assert "Assign 2: s1 #7, s2 #8." in out and "builder-a" not in out


def test_a_slot_with_a_live_take_is_not_assigned_and_the_plan_is_capped_by_the_free_ones(
    proj, stub
):
    """REQ-041"""
    two_briefs(proj, stub, third=True)
    stub.serve(f"{ISSUES}/9/comments", [comment(1, "boss", "taken: s1 2026-11-08")])
    found = data(proj, stub)
    assert [(a["session"], a["brief"]) for a in found["assign"]] == [("s2", 7)]


def test_builder_start_start_keeps_the_session_names(proj, stub):
    """REQ-041: answer 7, `builder_start = "start"` unchanged."""
    proj.write("agk.toml", "[flow]\n")
    listing(stub, [issue(7, brief("src/f7.py"))])
    free(stub, 7)
    found = data(proj, stub)
    assert [s["session"] for s in found["start"]] == ["builder-a"]
    assert "assign" not in found


# --- the schedule (answer 4) --------------------------------------------------------------------


class FakeReads:
    repo = REPO

    def __init__(self, comments, issues=None) -> None:
        self.comments = comments
        self.issues = [{"number": 204}] if issues is None else issues
        self.paths: list[str] = []

    def get(self, name: str, path: str, not_found=None):
        self.paths.append(path)
        return (self.issues if "labels=" in path else self.comments), ""


def setting(tmp_path: Path, text: str) -> Path:
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def test_the_schedule_is_four_staggered_starts_per_slot():
    """REQ-041: answer 4; the conductor's own minutes (:03, :18, :33, :48) stay clear."""
    assert doctor_script.slot_minutes(1) == [5, 20, 35, 50]
    assert doctor_script.slot_minutes(2) == [6, 21, 36, 51]
    assert doctor_script.slot_minutes(14)[0] == 3 + 1  # 14 slots wrap inside the quarter hour
    every = [m for n in range(1, 10) for m in doctor_script.slot_minutes(n)]
    assert len(set(every)) == len(every)


def test_doctor_reads_nothing_with_start(tmp_path):
    """REQ-041"""
    reads = FakeReads([])
    assert doctor_script.slot_schedule_result(setting(tmp_path, "[flow]\n"), reads).status == "ok"
    assert reads.paths == []


def test_doctor_prints_the_schedule_and_passes_when_each_slot_has_run(tmp_path):
    """REQ-041: answer 4; slots times starts per hour, and one marker per slot in the last hour."""
    markers = [said(1, f"Slot: active {stamp(2)} s1 r1"), said(2, f"Slot: released {stamp(9)} s2 r2")]
    result = doctor_script.slot_schedule_result(setting(tmp_path, ON), FakeReads(markers))
    assert result.status == "ok"
    assert "2 slots x 4 starts = 8 an hour" in result.message
    assert "s1 :05 :20 :35 :50" in result.message and "s2 :06 :21 :36 :51" in result.message


def test_doctor_names_a_slot_with_no_run_in_the_last_hour(tmp_path):
    """REQ-041: the kit cannot read an account's schedule; a slot that never ran has none."""
    markers = [said(1, f"Slot: active {stamp(2)} s1 r1")]
    result = doctor_script.slot_schedule_result(setting(tmp_path, ON), FakeReads(markers))
    assert result.status == "fail" and "no run in the last hour: s2" in result.message


def test_doctor_cannot_check_without_the_assignments_issue(tmp_path):
    """REQ-041: unknown is never ok."""
    result = doctor_script.slot_schedule_result(setting(tmp_path, ON), FakeReads([], issues=[]))
    assert result.status == "cannot-check"


def test_the_slot_schedule_check_is_a_warning():
    """REQ-041: a missing schedule must not fail a project that has just switched."""
    assert doctor_script.CHECKS["slot-schedule"][0] == "warn"


# --- the tick (addition of 11:20Z, items 1 and 4) -------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = self.start = 1000.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def ticking(monkeypatch, stalls=(), green=()):
    clock = Clock()
    monkeypatch.setattr(conductor, "time", clock)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    monkeypatch.setattr(conductor, "new_lines", lambda repo, since: [])
    monkeypatch.setattr(conductor, "green_lines", lambda root, repo, since: list(green))
    monkeypatch.setattr(conductor, "renew_lease", lambda root: 0)
    monkeypatch.setattr(conductor, "sweep_late", lambda root, repo: [])
    monkeypatch.setattr(conductor, "stall_report", lambda root, repo: list(stalls))
    return clock


def test_a_watch_with_no_event_returns_tick_within_five_minutes(monkeypatch, capsys):
    """REQ-041"""
    clock = ticking(monkeypatch)
    assert conductor.watch("root", datetime.now(UTC), False) == 0
    assert capsys.readouterr().out.strip() == "tick"
    assert clock.now - clock.start <= 300


def test_a_tick_carries_the_stall_lines(monkeypatch, capsys):
    """REQ-041: a stall is the absence of an event, so the tick is what finds it."""
    ticking(monkeypatch, stalls=["STALL #7 40m: restart s1"])
    conductor.watch("root", datetime.now(UTC), False)
    assert capsys.readouterr().out.splitlines() == ["tick", "STALL #7 40m: restart s1"]


def test_once_still_says_nothing_new(monkeypatch, capsys):
    """REQ-041"""
    ticking(monkeypatch, stalls=["STALL #7 40m: restart s1"])
    conductor.watch("root", datetime.now(UTC), True)
    assert capsys.readouterr().out.strip() == "nothing new"


def test_main_turning_green_ends_the_watch_at_once(monkeypatch, capsys):
    """REQ-041: addition of 13:25Z, rule 3."""
    clock = ticking(monkeypatch, green=["MAIN GREEN after #40: merge of main #7 (s1)"])
    conductor.watch("root", datetime.now(UTC), False)
    assert capsys.readouterr().out.strip() == "MAIN GREEN after #40: merge of main #7 (s1)"
    assert clock.now == clock.start


def test_a_stall_read_that_fails_still_ticks(monkeypatch, capsys):
    """REQ-041: unknown is never a stall, and it never loses the tick."""

    def broken(*a):
        raise conductor.CheckError("the comments cannot be read")

    monkeypatch.setattr(conductor, "stall_lines", broken)
    monkeypatch.setattr(conductor, "conductor_stall", broken)
    monkeypatch.setattr(conductor, "read", lambda *a: [])
    assert conductor.stall_report("root", REPO) == []


# --- STALL lines ----------------------------------------------------------------------------------


def draft(number: int = 7, brief_no: int | None = 3, **extra) -> dict:
    body = f"Brief: #{brief_no}\n" if brief_no else "no brief line\n"
    return {"number": number, "draft": True, "head": {"sha": HEAD}, "body": body} | extra


class Answers:
    """`session.pages` and `session.gh` from one table of saved answers."""

    def __init__(self, monkeypatch, tmp_path, text: str = "[flow]\nstall_minutes = 30\n") -> None:
        self.root = setting(tmp_path, text)
        self.table: dict = {}
        self.writes: list = []
        monkeypatch.setattr(conductor.session, "pages", self.pages)
        monkeypatch.setattr(conductor.session, "gh", self.gh)
        monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
        monkeypatch.setattr(conductor.session, "required_checks", lambda root: ["governance"])
        monkeypatch.setattr(conductor, "verdict_authors", lambda root: ["boss"])

    def pages(self, endpoint: str):
        return self.table.get(endpoint, self.table.get(endpoint.split("?")[0]))

    def gh(self, endpoint: str, *extra, method: str = "GET"):
        if method != "GET":
            self.writes.append((method, endpoint, extra))
            return {}
        return self.table.get(endpoint)

    def pull(self, comments, pushed: float = 40, runs=()) -> None:
        self.table[f"repos/{REPO}/issues/7/comments"] = comments
        self.table[f"repos/{REPO}/issues/3/comments"] = [said(1, "taken: s2 2026-11-09", 90)]
        date = {"commit": {"committer": {"date": stamp(pushed)}}}
        self.table[f"repos/{REPO}/commits/{HEAD}"] = date
        self.table[CHECK_RUNS] = {"check_runs": list(runs)}


def run(conclusion: str, name: str = "governance", minutes: float = 20) -> dict:
    return {"id": 1, "name": name, "status": "completed", "conclusion": conclusion,
            "completed_at": stamp(minutes), "started_at": stamp(minutes + 1)}  # fmt: skip


def lines(answers: Answers, pull: dict) -> list[str]:
    return conductor.stall_lines(answers.root, REPO, [pull], datetime.now(UTC))


def test_a_draft_with_no_push_for_30_minutes_yields_a_stall_line(monkeypatch, tmp_path):
    """REQ-041: addition of 11:20Z, items 2 and 4."""
    answers = Answers(monkeypatch, tmp_path)
    answers.pull([])
    assert lines(answers, draft()) == ["STALL #7 40m: restart s2"]


def test_a_recent_push_or_progress_is_no_stall(monkeypatch, tmp_path):
    """REQ-041"""
    answers = Answers(monkeypatch, tmp_path)
    answers.pull([], pushed=5)
    assert lines(answers, draft()) == []
    answers.pull([said(9, "Progress: abc done 1/7; next: x", 5)])
    assert lines(answers, draft()) == []


def test_a_ready_pull_request_or_one_of_no_brief_is_not_a_builder_stall(monkeypatch, tmp_path):
    """REQ-041: ready work waits for the conductor (`LATE`), not for a builder."""
    answers = Answers(monkeypatch, tmp_path)
    answers.pull([])
    assert lines(answers, draft(draft=False)) == []
    assert lines(answers, draft(brief_no=None)) == []


def test_a_builder_waiting_on_its_question_is_no_stall(monkeypatch, tmp_path):
    """REQ-041: session rule 21, it waits there; `LATE` is the conductor's line."""
    answers = Answers(monkeypatch, tmp_path)
    answers.pull([said(9, "Question: Q-776-7 which?", 35)])
    assert lines(answers, draft()) == []


def test_a_failed_required_check_with_no_progress_for_15_minutes(monkeypatch, tmp_path):
    """REQ-041: item 1 and the second form of item 2."""
    answers = Answers(monkeypatch, tmp_path)
    answers.pull([said(9, "Progress: abc done 1/7; next: x", 20)], pushed=22,
                 runs=[run("failure"), run("success", "proof")])  # fmt: skip
    assert lines(answers, draft()) == ["STALL #7: failed check governance"]


def test_a_failed_check_under_recent_progress_is_no_stall(monkeypatch, tmp_path):
    """REQ-041"""
    answers = Answers(monkeypatch, tmp_path)
    answers.pull([said(9, "Progress: abc done 1/7; next: x", 5)], pushed=22, runs=[run("failure")])
    assert lines(answers, draft()) == []


def test_owner_needed_is_said_once_and_the_stall_line_stays(monkeypatch, tmp_path):
    """REQ-041: item 3; a refused start yields one `Owner needed:`, and the line stays until a
    builder reports."""
    answers = Answers(monkeypatch, tmp_path)
    answers.pull([])
    assert lines(answers, draft()) == ["STALL #7 40m: restart s2"]  # post it: nothing says posted
    answers.pull([said(9, "Owner needed: #7 start with: Session name: s2.", 2)])
    assert lines(answers, draft()) == ["STALL #7 40m: restart s2 (owner needed posted)"]
    answers.pull([said(9, "Owner needed: #7", 35), said(10, "Report: abc escalate x", 2)])
    assert lines(answers, draft()) == []


def test_a_head_that_cannot_be_read_is_never_a_stall(monkeypatch, tmp_path):
    """REQ-041: unknown is never dead."""
    answers = Answers(monkeypatch, tmp_path)
    answers.pull([])
    del answers.table[f"repos/{REPO}/commits/{HEAD}"]
    assert lines(answers, draft()) == []


# --- the conductor's own stall (additions of 2026-11-09) ------------------------------------------


def held(name: str = "c1", renewed: float = 1, taken: float | None = 45) -> dict:
    since = "" if taken is None else f" since {stamp(taken)}"
    return said(5, f"Conductor: active {stamp(renewed)} {name}{since}", 60)


def holder(monkeypatch, tmp_path, comments, due: bool = True, marker: dict | None = None):
    answers = Answers(monkeypatch, tmp_path, ON + "stall_minutes = 30\n")
    answers.table[f"repos/{REPO}/issues/comments"] = comments
    answers.table[f"repos/{REPO}/issues/61/comments"] = [marker or held()]
    monkeypatch.setattr(conductor, "review_or_start_due", lambda root, repo, authors: due)
    return answers


def test_a_lease_renewed_with_no_comment_is_a_stall(monkeypatch, tmp_path):
    """REQ-041: addition of 04:43Z."""
    answers = holder(monkeypatch, tmp_path, [said(6, "Verdict: cleared abc", 40)])
    assert conductor.conductor_stall(answers.root, REPO, datetime.now(UTC)) == [
        "STALL conductor c1 40 min"
    ]


def test_a_conductor_that_spoke_recently_is_no_stall(monkeypatch, tmp_path):
    """REQ-041: a builder's `Report:` under the same account is not the conductor's."""
    answers = holder(monkeypatch, tmp_path, [said(6, "Assign: s1 #7", 5)])
    assert conductor.conductor_stall(answers.root, REPO, datetime.now(UTC)) == []
    answers = holder(monkeypatch, tmp_path, [said(6, "Report: abc ready for review", 5)])
    assert conductor.conductor_stall(answers.root, REPO, datetime.now(UTC)) != []


def test_nothing_due_is_no_stall(monkeypatch, tmp_path):
    """REQ-041: a quiet queue needs no comment."""
    answers = holder(monkeypatch, tmp_path, [], due=False)
    assert conductor.conductor_stall(answers.root, REPO, datetime.now(UTC)) == []


def test_a_conductor_that_has_just_taken_the_lease_is_no_stall(monkeypatch, tmp_path):
    """REQ-041: the count starts at its take, not at its predecessor's last comment."""
    answers = holder(monkeypatch, tmp_path, [said(6, "Verdict: x", 60)], marker=held(taken=3))
    assert conductor.conductor_stall(answers.root, REPO, datetime.now(UTC)) == []


def test_a_marker_without_since_counts_from_its_own_time(monkeypatch, tmp_path):
    """REQ-041: a marker of the older form is never read as a stall."""
    answers = holder(monkeypatch, tmp_path, [], marker=held(taken=None))
    assert conductor.conductor_stall(answers.root, REPO, datetime.now(UTC)) == []


def taking(monkeypatch, answers) -> list:
    written: list = []
    monkeypatch.setattr(conductor, "lease_mark", lambda root: None)
    monkeypatch.setattr(conductor, "write_marker", lambda *a: written.append(a[3]))
    return written


def test_the_next_relay_takes_a_stalled_lease_after_posting_the_line(monkeypatch, tmp_path, capsys):
    """REQ-041: additions of 04:43Z and 13:25Z (rule 2), the line on the plan issue."""
    answers = holder(monkeypatch, tmp_path, [])
    written = taking(monkeypatch, answers)
    assert conductor.lease(answers.root, "--take", "c2") == 0
    assert answers.writes[0][1] == f"repos/{REPO}/issues/61/comments"
    assert answers.writes[0][2][1].startswith("body=STALL conductor c1 ")
    assert written[0].startswith("body=Conductor: active ") and " c2 since " in written[0]
    assert "taken by c2" in capsys.readouterr().out


def test_a_live_holder_keeps_the_lease(monkeypatch, tmp_path, capsys):
    """REQ-041"""
    answers = holder(monkeypatch, tmp_path, [said(6, "Tell: s1 go", 5)])
    written = taking(monkeypatch, answers)
    assert conductor.lease(answers.root, "--take", "c2") == conductor.merge_cleared.EXIT_HELD
    assert written == [] and answers.writes == []


def test_a_watch_renewal_never_takes_over(monkeypatch, tmp_path):
    """REQ-041: only a relay's own `--take` does; a renewal of an older mark ends its watch."""
    answers = holder(monkeypatch, tmp_path, [])
    written = taking(monkeypatch, answers)
    monkeypatch.setattr(conductor, "own_name", lambda root: "c2")
    assert conductor.renew_lease(answers.root) == conductor.merge_cleared.EXIT_HELD
    assert written == [] and answers.writes == []


def test_a_renewal_keeps_the_time_of_the_take(monkeypatch, tmp_path):
    """REQ-041"""
    answers = holder(monkeypatch, tmp_path, [], marker=held(renewed=4, taken=20))
    written = taking(monkeypatch, answers)
    since = answers.table[f"repos/{REPO}/issues/61/comments"][0]["body"].split(" since ")[1]
    assert conductor.lease(answers.root, "--take", "c1") == 0
    assert written[0].endswith(f" c1 since {since}")


# --- main green (addition of 13:25Z, rule 3) ------------------------------------------------------


def red_issue(number: int, opened: float, closed: float | None) -> dict:
    return {"number": number, "title": conductor.session.RED_TITLE,
            "body": "Sentence: red\nPriority: 0\n", "user": {"login": "x"},
            "created_at": stamp(opened), "closed_at": None if closed is None else stamp(closed)}  # fmt: skip


def greening(monkeypatch, tmp_path, issues, pulls, runs) -> Answers:
    answers = Answers(monkeypatch, tmp_path)
    answers.table[f"repos/{REPO}/issues"] = issues
    answers.table[f"repos/{REPO}/pulls?state=open"] = pulls
    answers.table[CHECK_RUNS] = {"check_runs": runs}
    answers.table[f"repos/{REPO}/issues/3/comments"] = [said(1, "taken: s2 2026-11-09", 90)]
    monkeypatch.setattr(conductor.session, "is_red", lambda item: True)
    return answers


def since(minutes: float) -> datetime:
    return datetime.now(UTC) - timedelta(minutes=minutes)


def test_main_turning_green_names_the_pull_requests_whose_only_failure_was_the_red_main(
    monkeypatch, tmp_path
):
    """REQ-041"""
    answers = greening(monkeypatch, tmp_path, [red_issue(40, 60, 2)], [draft(draft=False)],
                       [run("failure", minutes=30)])  # fmt: skip
    assert conductor.green_lines(answers.root, REPO, since(5)) == [
        "MAIN GREEN after #40: merge of main #7 (s2)"
    ]


def test_a_failure_outside_the_red_window_is_the_pull_requests_own(monkeypatch, tmp_path):
    """REQ-041"""
    answers = greening(monkeypatch, tmp_path, [red_issue(40, 60, 2)], [draft(draft=False)],
                       [run("failure", minutes=1)])  # fmt: skip
    assert conductor.green_lines(answers.root, REPO, since(5)) == []


def test_an_issue_still_open_or_closed_before_the_watch_is_no_event(monkeypatch, tmp_path):
    """REQ-041"""
    runs = [run("failure", minutes=30)]
    open_red = greening(monkeypatch, tmp_path, [red_issue(40, 60, None)], [draft()], runs)
    assert conductor.green_lines(open_red.root, REPO, since(5)) == []
    old = greening(monkeypatch, tmp_path, [red_issue(40, 60, 20)], [draft()], runs)
    assert conductor.green_lines(old.root, REPO, since(5)) == []


def test_a_closed_issues_read_that_fails_is_no_event(monkeypatch, tmp_path):
    """REQ-041"""
    answers = Answers(monkeypatch, tmp_path)
    assert conductor.green_lines(answers.root, REPO, since(5)) == []


# --- the sweep carries the lines ------------------------------------------------------------------


def test_the_sweep_prints_the_stall_lines(monkeypatch, tmp_path, capsys):
    """REQ-041: the first pass and every notification read the same lines as a tick."""
    answers = Answers(monkeypatch, tmp_path)
    answers.table[f"repos/{REPO}/pulls?state=open"] = []
    answers.table[f"repos/{REPO}"] = {"default_branch": "main"}
    answers.table[f"repos/{REPO}/issues?state=open"] = []
    monkeypatch.setattr(conductor, "proof_lines", lambda *a: [])
    monkeypatch.setattr(conductor.caps, "over_lines", lambda *a: [])
    monkeypatch.setattr(conductor, "branch_line", lambda *a: "main: success at abc")
    monkeypatch.setattr(conductor, "slot_lines", lambda *a: [])
    monkeypatch.setattr(conductor, "spec_approvers", lambda root: [])
    monkeypatch.setattr(conductor, "stall_report", lambda root, repo: ["STALL conductor c1 40 min"])
    assert conductor.sweep(answers.root) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "STALL conductor c1 40 min"
