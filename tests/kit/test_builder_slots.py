"""Builder slots: the setting, the slot lease and the next step (brief #776 build (a); REQ-041).

Saved comments through a `gh` stub on `PATH`, invented names, no network.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from test_session import (
    ISSUES,
    REPO,
    comment,
    iso,
    posts,
    session,
)
from test_session import (
    proj as session_proj,  # noqa: F401  (the fixtures of test_session)
)
from test_session import (
    stub as session_stub,  # noqa: F401
)

COMMENTS = f"{ISSUES}/204/comments"
PULLS = f"repos/{REPO}/pulls"
ALL = f"{ISSUES}/comments"
ON = '[flow]\nbuilder_start = "assign"\nbuilder_slots = 2\n'
REVIEWERS = "version: 1\nverdict_authors: [boss, second]\nspec_approvers: [owner]\n"
DAY = iso()[:10]


@pytest.fixture
def stub(request):
    found = request.getfixturevalue("session_stub")
    found.serve(ISSUES, [{"number": 204, "title": "Conductor: assignments"}])
    found.serve(PULLS, [])
    found.serve(ALL, [])
    found.serve(COMMENTS, [])
    return found


@pytest.fixture
def proj(request):
    found = request.getfixturevalue("session_proj")
    found.write("config/reviewers.yaml", REVIEWERS)
    found.write("agk.toml", ON)
    return found


def ago(minutes: float) -> str:
    return iso(timedelta(minutes=-minutes))


def marker(cid, run="other", minutes=1, state="active", slot="s1", login="boss") -> dict:
    return comment(cid, login, f"Slot: {state} {ago(minutes)} {slot} {run}")


def mark(proj, run: str = "mine", slot: str = "s1") -> Path:
    path = Path(proj.root) / ".git" / "agk" / f"slot-{slot}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{run}\n", encoding="utf-8")
    return path


def slot(proj, stub, flag: str, name: str = "s1"):
    return session(proj, stub, "slot", flag, name)


def writes(stub) -> list[list]:
    return [c for c in stub.calls() if c[0] in ("POST", "PATCH")]


def last(out) -> str:
    return out.stdout.strip().splitlines()[-1]


def held(proj, stub, *others: dict) -> None:
    """This checkout holds s1, with the other comments of the assignments issue."""
    mark(proj)
    stub.serve(COMMENTS, [marker(1, "mine"), *others])
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")


def owned(stub, number=7, brief=5, state="clean", said=(), author="bot") -> None:
    """Pull request `number` by `author`, of a brief this slot took, with the comments `said`."""
    pull = {
        "number": number,
        "state": "open",
        "body": f"Brief: #{brief}",
        "user": {"login": author},
    }
    stub.serve(PULLS, [pull])
    stub.serve(f"{PULLS}/{number}", {**pull, "mergeable_state": state, "head": {"sha": "a" * 40}})
    stub.serve(f"{ISSUES}/{brief}/comments", [comment(50, "boss", f"taken: s1 {DAY}")])
    stub.serve(f"{ISSUES}/{number}/comments", list(said))


# --- the setting -----------------------------------------------------------------------------


def test_builder_start_defaults_to_start_and_no_slot_exists(proj, stub):
    """REQ-041"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    out = slot(proj, stub, "--take")
    assert out.returncode == 3
    assert "slot: off" in out.stdout and "builder_start" in out.stdout
    assert stub.calls() == []


def test_a_bad_builder_start_is_refused_naming_the_setting_only(proj, stub):
    """REQ-041"""
    proj.write("agk.toml", '[flow]\nbuilder_start = "launch-it"\n')
    out = slot(proj, stub, "--take")
    assert out.returncode == 2
    assert "builder_start" in out.stdout and "launch-it" not in out.stdout


@pytest.mark.parametrize("value", ["0", "true", '"2"'])
def test_a_bad_builder_slots_is_refused_naming_the_setting_only(proj, stub, value):
    """REQ-041"""
    proj.write("agk.toml", f'[flow]\nbuilder_start = "assign"\nbuilder_slots = {value}\n')
    out = slot(proj, stub, "--take")
    assert out.returncode == 2 and "builder_slots" in out.stdout


@pytest.mark.parametrize("name", ["s3", "s0", "builder-a", "s01"])
def test_a_name_outside_the_slots_is_refused(proj, stub, name):
    """REQ-041"""
    out = slot(proj, stub, "--take", name)
    assert out.returncode == 2 and "builder_slots" in out.stdout
    assert name not in out.stdout and stub.calls() == []


def test_builder_slots_defaults_to_max_builders(proj, stub):
    """REQ-041"""
    proj.write("agk.toml", '[flow]\nbuilder_start = "assign"\nmax_builders = 3\n')
    assert slot(proj, stub, "--take", "s4").returncode == 2
    mark(proj, slot="s3")
    stub.serve(COMMENTS, [marker(1, "mine", slot="s3")])
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")
    assert slot(proj, stub, "--take", "s3").returncode == 0


# --- the lease -------------------------------------------------------------------------------


def test_take_posts_one_marker_on_the_assignments_issue(proj, stub):
    """REQ-041"""
    mark(proj)
    stub.serve(COMMENTS, [marker(9, "mine")], nth=2)
    out = slot(proj, stub, "--take")
    assert out.returncode == 0, out.stdout
    done = posts(stub)
    assert len(done) == 1 and done[0][1] == COMMENTS
    assert done[0][2][1].startswith(f"body=Slot: active {DAY}") and done[0][2][1].endswith(
        " s1 mine"
    )


def test_a_take_mints_a_run_name_kept_in_the_git_directory(proj, stub):
    """REQ-041"""
    # The read-back sees a marker of another run, so this run keeps nothing and ends.
    stub.serve(COMMENTS, [marker(9, "other")], nth=2)
    out = slot(proj, stub, "--take")
    assert out.returncode == 3
    run = posts(stub)[0][2][1].rsplit(" ", 1)[1]
    assert len(run) >= 8
    assert not (Path(proj.root) / ".git" / "agk" / "slot-s1").exists()


def test_a_held_slot_ends_the_run_and_writes_nothing(proj, stub):
    """REQ-041"""
    stub.serve(COMMENTS, [marker(1, "other", minutes=9)])
    out = slot(proj, stub, "--take")
    assert out.returncode == 3
    assert "held" in out.stdout and "builder_slots" not in out.stdout
    assert writes(stub) == []


def test_an_expired_lease_is_taken_by_editing_its_marker(proj, stub):
    """REQ-041"""
    mark(proj)
    old = marker(1, "other", minutes=11)
    stub.serve(COMMENTS, [old], nth=1)
    stub.serve(COMMENTS, [marker(1, "mine")], nth=2)
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")
    out = slot(proj, stub, "--take")
    assert out.returncode == 0, out.stdout
    assert [c[0] for c in writes(stub)] == ["PATCH"]


def test_a_marker_by_an_unlisted_author_holds_nothing(proj, stub):
    """REQ-041"""
    mark(proj)
    forged = marker(1, "other", login="stranger")
    stub.serve(COMMENTS, [forged], nth=1)
    stub.serve(COMMENTS, [forged, marker(9, "mine")], nth=2)
    assert slot(proj, stub, "--take").returncode == 0
    assert [c[0] for c in writes(stub)] == ["POST"]


def test_two_takes_at_once_leave_the_oldest_marker_the_winner(proj, stub):
    """REQ-041"""
    path = mark(proj)
    stub.serve(COMMENTS, [marker(8, "other"), marker(9, "mine")], nth=2)
    out = slot(proj, stub, "--take")
    assert out.returncode == 3 and "held" in out.stdout
    assert not path.exists()


def test_renew_edits_the_holders_marker(proj, stub):
    """REQ-041"""
    held(proj, stub)
    out = slot(proj, stub, "--renew")
    assert out.returncode == 0, out.stdout
    assert [c[0] for c in writes(stub)] == ["PATCH"]
    assert " s1 mine" in writes(stub)[0][2][1]


def test_renew_by_another_run_ends_it(proj, stub):
    """REQ-041"""
    mark(proj, "stale")
    stub.serve(COMMENTS, [marker(1, "other")])
    assert slot(proj, stub, "--renew").returncode == 3
    assert writes(stub) == []


def test_release_marks_it_released_and_forgets_the_run(proj, stub):
    """REQ-041"""
    path = mark(proj)
    held(proj, stub)
    out = slot(proj, stub, "--release")
    assert out.returncode == 0, out.stdout
    assert "Slot: released" in writes(stub)[0][2][1]
    assert not path.exists()


def test_release_by_another_run_writes_nothing(proj, stub):
    """REQ-041"""
    stub.serve(COMMENTS, [marker(1, "other")])
    assert slot(proj, stub, "--release").returncode == 3
    assert writes(stub) == []


# --- the slot's next step --------------------------------------------------------------------


def test_next_ends_a_run_that_does_not_hold_the_slot(proj, stub):
    """REQ-041"""
    stub.serve(COMMENTS, [marker(1, "other")])
    assert slot(proj, stub, "--next").returncode == 3


def test_next_renews_on_every_pass(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"))
    assert slot(proj, stub, "--next").returncode == 0
    assert [c[0] for c in writes(stub)] == ["PATCH"]


def test_a_fix_list_comes_before_new_work(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"))
    owned(stub, said=[comment(60, "boss", f"Verdict: fix list {'a' * 40}")])
    assert last(slot(proj, stub, "--next")) == "follow-up pr #7 fix list"


def test_a_fix_list_with_a_report_after_it_is_answered(proj, stub):
    """REQ-041"""
    held(proj, stub)
    said = [
        comment(60, "boss", f"Verdict: fix list {'a' * 40}"),
        comment(61, "boss", f"Report: {'b' * 12} fix list applied"),
    ]
    owned(stub, said=said)
    assert last(slot(proj, stub, "--next")) == "wait pr #7"


ESCALATE = f"Report: {'d' * 7} escalate Q-5-1 Q-5-2; Usage: not shown"


def test_an_answered_escalation_is_a_follow_up(proj, stub):
    """REQ-041 REQ-040"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"))
    said = [comment(60, "bot", ESCALATE), comment(61, "boss", "Answer: Q-5-2 keep the order")]
    owned(stub, said=said)
    assert last(slot(proj, stub, "--next")) == "follow-up pr #7 answer"


@pytest.mark.parametrize(
    "asked, answer",
    [
        ("Report: 1234567 blocked Q-5-1", "Maintainer answer: Q-5-1 yes"),
        ("Question: Q-5-1 which order?", "Correction: Q-5-1 the order is kept"),
    ],
)
def test_a_blocked_report_or_a_question_answered_is_a_follow_up(proj, stub, asked, answer):
    """REQ-041"""
    held(proj, stub)
    owned(stub, said=[comment(60, "bot", asked), comment(61, "owner", answer)])
    assert last(slot(proj, stub, "--next")) == "follow-up pr #7 answer"


def test_a_question_answered_under_the_same_login_is_a_follow_up(proj, stub):
    """REQ-041"""
    held(proj, stub)
    said = [
        comment(60, "boss", "Question: Q-5-1 which order?"),
        comment(61, "boss", "Answer: Q-5-1"),
    ]
    owned(stub, said=said, author="boss")
    assert last(slot(proj, stub, "--next")) == "follow-up pr #7 answer"


def test_an_answer_with_a_newer_report_is_spent(proj, stub):
    """REQ-041"""
    held(proj, stub)
    said = [
        comment(60, "bot", ESCALATE),
        comment(61, "boss", "Answer: Q-5-2 keep the order"),
        comment(62, "bot", f"Report: {'e' * 7} ready for review; Usage: not shown"),
    ]
    owned(stub, said=said)
    assert last(slot(proj, stub, "--next")) == "wait pr #7"


def test_an_answer_by_an_unlisted_author_is_not_a_follow_up(proj, stub):
    """REQ-041"""
    held(proj, stub)
    said = [comment(60, "bot", ESCALATE), comment(61, "stranger", "Answer: Q-5-2 keep it")]
    owned(stub, said=said)
    assert last(slot(proj, stub, "--next")) == "wait pr #7"


@pytest.mark.parametrize(
    "said",
    [
        [comment(60, "bot", ESCALATE), comment(61, "boss", "Answer: Q-9-1 another question")],
        [comment(61, "boss", "Answer: Q-5-2 before"), comment(62, "bot", ESCALATE)],
        [
            comment(60, "bot", f"Report: {'d' * 7} ready Q-5-1"),
            comment(61, "boss", "Answer: Q-5-1"),
        ],
    ],
)
def test_an_answer_that_names_no_open_question_is_not_a_follow_up(proj, stub, said):
    """REQ-041"""
    held(proj, stub)
    owned(stub, said=said)
    assert last(slot(proj, stub, "--next")) == "wait pr #7"


def test_a_conflict_comes_before_new_work(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"))
    owned(stub, state="dirty")
    assert last(slot(proj, stub, "--next")) == "follow-up pr #7 conflict"


def test_a_pull_request_of_another_slot_is_not_a_follow_up(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"))
    owned(stub, state="dirty")
    stub.serve(f"{ISSUES}/5/comments", [comment(50, "boss", f"taken: s2 {DAY}")])
    assert last(slot(proj, stub, "--next")) == "assign #12"


def test_a_follow_up_assign_names_the_pull_request(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #5 pr #7 merge of main"))
    stub.serve(f"{ISSUES}/7/comments", [])
    assert last(slot(proj, stub, "--next")) == "follow-up pr #7 merge of main"


def test_a_follow_up_assign_with_a_later_report_is_spent(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #5 pr #7 fix list", ago(1)))
    stub.serve(
        f"{ISSUES}/7/comments", [comment(90, "boss", f"Report: {'b' * 12} fix list applied")]
    )
    assert last(slot(proj, stub, "--next")) == "wait"


def test_the_newest_assign_is_the_work(proj, stub):
    """REQ-041"""
    held(
        proj,
        stub,
        comment(2, "boss", "Assign: s1 #11"),
        comment(3, "boss", "Assign: s1 #12 build (b)"),
        comment(4, "boss", "Assign: s2 #13"),
    )
    assert last(slot(proj, stub, "--next")) == "assign #12 build (b)"


def test_an_assign_by_an_unlisted_author_is_not_work(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "stranger", "Assign: s1 #12"))
    assert last(slot(proj, stub, "--next")) == "request"


def test_a_spent_assign_is_not_taken_again(proj, stub):
    """REQ-041"""
    line = comment(2, "boss", "Assign: s1 #12", ago(30))
    held(proj, stub, line)
    stub.serve(ALL, [comment(70, "boss", f"taken: s1 {DAY}")])
    assert last(slot(proj, stub, "--next")) == "take"


def test_an_open_pull_request_waits_before_a_new_assign(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"))
    owned(stub)
    assert last(slot(proj, stub, "--next")) == "wait pr #7"


@pytest.mark.parametrize(("minutes", "want"), [(5, "wait"), (9.5, "wait"), (11, "take")])
def test_next_take_only_after_ten_idle_minutes(proj, stub, minutes, want):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Request: s1 finished #5", ago(minutes)))
    assert last(slot(proj, stub, "--next")) == want


def test_the_idle_clock_counts_from_the_newest_assign_or_request(proj, stub):
    """REQ-041"""
    held(
        proj,
        stub,
        comment(2, "boss", "Request: s1 finished #5", ago(60)),
        comment(3, "boss", "Assign: s1 none", ago(2)),
    )
    assert last(slot(proj, stub, "--next")) == "wait"


def test_a_slot_with_no_clock_asks_first(proj, stub):
    """REQ-041"""
    held(proj, stub)
    assert last(slot(proj, stub, "--next")) == "request"


def test_pool_stop_by_an_approver_ends_the_loop(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"), comment(3, "owner", "Pool: stop"))
    assert last(slot(proj, stub, "--next")) == "stop"


def test_pool_stop_by_anyone_else_is_ignored(proj, stub):
    """REQ-041"""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"), comment(3, "boss", "Pool: stop"))
    assert last(slot(proj, stub, "--next")) == "assign #12"


def test_watch_assign_ends_on_a_follow_up_line(proj, stub):
    """REQ-041"""
    stub.serve(COMMENTS, [comment(1, "boss", "Request: s1 finished #5")], nth=1)
    line = comment(2, "boss", "Assign: s1 #5 pr #7 fix list")
    stub.serve(COMMENTS, [comment(1, "boss", "Request: s1 finished #5"), line])
    out = session(proj, stub, "watch", "--assign", "s1", "--interval", "0", "--timeout", "30")
    assert last(out) == "assign #5 pr #7 fix list"


def test_a_paused_kit_takes_no_slot(proj, stub):
    """REQ-041"""
    proj.write(
        "agk.toml", 'default_branch = "main"\npaused = true\n[flow]\nbuilder_start = "assign"\n'
    )
    proj.git("add", "-A")
    proj.git("commit", "-qm", "x")
    proj.git("update-ref", "refs/remotes/origin/main", "HEAD")
    out = slot(proj, stub, "--take")
    assert out.returncode == 5 and writes(stub) == []


# --- the lease of 10 minutes and the release (brief #776, the 09:36Z addition) ------------------


def released(stub) -> list[str]:
    return [c[2][1] for c in writes(stub) if c[0] == "PATCH" and "Slot: released" in c[2][1]]


def test_a_slot_lease_not_renewed_for_ten_minutes_reads_free(proj, stub):
    """REQ-041"""
    stub.serve(COMMENTS, [marker(1, "other", minutes=11)], nth=1)
    stub.serve(COMMENTS, [marker(1, "other", minutes=0)], nth=2)
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")
    out = slot(proj, stub, "--take")
    assert [c[0] for c in writes(stub)] == ["PATCH"], out.stdout


def test_stop_releases_the_lease_of_the_run(proj, stub):
    """REQ-041: every exit path releases."""
    held(proj, stub, comment(3, "owner", "Pool: stop"))
    out = slot(proj, stub, "--next")
    assert last(out) == "stop"
    assert len(released(stub)) == 1


def test_a_slots_watch_renews_its_lease_before_it_waits(proj, stub):
    """REQ-041: an event at once still renews first."""
    asked = comment(2, "boss", "Request: s1 finished #3")
    held(proj, stub, asked, comment(3, "boss", "Assign: s1 #12"))
    out = session(proj, stub, "watch", "--assign", "s1", "--interval", "0", "--timeout", "30")
    assert last(out) == "assign #12", out.stdout
    assert [c[0] for c in writes(stub)] == ["PATCH"]
    assert "Slot: active" in writes(stub)[0][2][1]


# --- a slot alive when it ran on time (brief #960, ADR-0412) -----------------------------------

import test_pool_health as health  # noqa: E402  (its gh stub and router, no fixtures)

NINE = '[flow]\nbuilder_start = "assign"\nbuilder_slots = 9\nplan_issue = 61\n'
ON_THREE = NINE.replace("builder_slots = 9", "builder_slots = 3")


def pool(tmp_path: Path, toml: str = NINE):
    """A project and the pool's gh stub, as `test_pool_health` builds them."""
    root = tmp_path / "proj"
    (root / "config").mkdir(parents=True)
    (root / "config" / "reviewers.yaml").write_text(
        "version: 1\nverdict_authors: [boss]\nspec_approvers: [owner]\n", encoding="utf-8"
    )
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    health.subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)  # nosec B603 B607 - fixed argument list, no shell
    return root, health.Stub(tmp_path)


def pool_body(stub) -> str:
    made = next(c for c in stub.writes() if c[1] == health.ISSUES)
    return next(f[5:] for f in made[2] if f.startswith("body="))


def test_nine_slots_released_twenty_minutes_ago_are_alive(tmp_path):
    """REQ-041: brief #960 (a): an idle pool that ran on time is not down."""
    root, stub = pool(tmp_path)
    released = [health.slot(f"s{n}", n + 1, 20, "released") for n in range(1, 10)]
    stub.fixtures[health.ASSIGNMENTS] = released
    out = health.router(root, stub, tmp_path, "--health", "--dry-run")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "health: Builder pool down: ok" in out.stdout


def test_a_slot_last_seen_three_hours_ago_is_dead_and_its_time_is_printed(tmp_path):
    """REQ-041: brief #960 (b): dead means not seen within slot_seen_minutes; never is said."""
    root, stub = pool(tmp_path, ON_THREE)
    gone = health.slot("s2", 3, 180, "released")
    stub.fixtures[health.ASSIGNMENTS] = [health.slot("s1", 2, 20, "released"), gone]
    out = health.router(root, stub, tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    assert health.opened(stub) == ["Builder pool down"]
    body = pool_body(stub)
    seen = gone["body"].split()[2]
    assert f"s2 (last seen {seen})" in body and "s3 (never)" in body
    assert "s1" not in body and "slot_seen_minutes" in body


def test_an_open_pool_issue_is_updated_not_duplicated(tmp_path):
    """REQ-041: brief #960 (c): one issue per title, as brief #916 did for the red alarm."""
    root, stub = pool(tmp_path, ON_THREE)
    stub.fixtures[health.ASSIGNMENTS] = [health.slot("s1", 2, 180, "released")]
    stub.fixtures[health.HEALTH] = [{"number": 88, "title": "Builder pool down", "body": "older"}]
    out = health.router(root, stub, tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    assert health.opened(stub) == []
    assert [c[:2] for c in stub.writes()] == [["PATCH", f"{health.ISSUES}/88"]]


def test_a_bad_slot_seen_minutes_skips_the_health_naming_the_setting_only(tmp_path):
    """REQ-041: the new key is a whole number, 1 or more; the refusal names it, not the value."""
    root, stub = pool(tmp_path, ON_THREE + "slot_seen_minutes = 0\n")
    out = health.router(root, stub, tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "slot_seen_minutes" in out.stdout and stub.writes() == []


# --- the slot log: each run's decision in its marker, unacted assignments (brief #998) -----------

import sys  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

from test_session import SCRIPTS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import conductor  # noqa: E402


def logged(cid, decided: str, minutes: float = 30, state: str = "released", slot="s1") -> dict:
    """A marker whose run started `minutes` ago, a minute before its stamp, deciding `decided`."""
    start, end = ago(minutes), ago(minutes - 1)
    body = f"Slot: {state} {end} {slot} r{cid}\nlast run: {start} to {end}\ndecided: {decided}"
    return comment(cid, "boss", body, start)


def test_a_runs_decision_is_written_into_its_marker_and_no_comment_is_added(proj, stub):
    """REQ-041, REQ-054: brief #998 (a)."""
    held(proj, stub, comment(2, "boss", "Assign: s1 #12"))
    out = slot(proj, stub, "--next")
    assert last(out) == "assign #12", out.stdout
    done = writes(stub)
    assert [c[0] for c in done] == ["PATCH"] and posts(stub) == []
    body = done[0][2][1][5:].splitlines()
    assert body[0].startswith("Slot: active ") and body[0].endswith(" s1 mine")
    assert body[1].startswith("last run: 20") and " to 20" in body[1]
    assert body[2] == "decided: assign #12"


def test_an_idle_run_writes_its_decision_with_its_release_in_one_edit(proj, stub):
    """REQ-041: brief #998 answer 1: an idle run still costs one edit."""
    held(proj, stub, comment(3, "owner", "Pool: stop"))
    out = slot(proj, stub, "--next")
    assert last(out) == "stop"
    done = writes(stub)
    assert len(done) == 1 and "Slot: released" in done[0][2][1]
    assert done[0][2][1].endswith("\ndecided: stop")


def test_a_release_keeps_the_decision_and_closes_the_run(proj, stub):
    """REQ-041: brief #998 answer 1: `slot --release` writes the end of the run."""
    path = mark(proj)
    path.write_text("mine 2026-11-10T15:09:00Z\n", encoding="utf-8")
    body = "Slot: active 2026-11-10T15:09:30Z s1 mine\nlast run: 2026-11-10T15:09:00Z to "
    body += "2026-11-10T15:09:30Z\ndecided: wait"
    stub.serve(COMMENTS, [comment(1, "boss", body.replace("2026-11-10T15:09:30Z", ago(1)))])
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")
    out = slot(proj, stub, "--release")
    assert out.returncode == 0, out.stdout
    lines = writes(stub)[0][2][1][5:].splitlines()
    assert lines[0].startswith("Slot: released ")
    assert lines[1].startswith("last run: 2026-11-10T15:09:00Z to ") and lines[1][-1] == "Z"
    assert lines[1] != "last run: 2026-11-10T15:09:00Z to 2026-11-10T15:09:30Z"
    assert lines[2] == "decided: wait"


def test_a_renewal_keeps_the_log_lines(proj, stub):
    """REQ-041: a renewal mid-build edits the lease and keeps the decision."""
    mark(proj)
    body = f"Slot: active {ago(1)} s1 mine\nlast run: {ago(2)} to {ago(1)}\ndecided: assign #12"
    stub.serve(COMMENTS, [comment(1, "boss", body)])
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")
    assert slot(proj, stub, "--renew").returncode == 0
    assert writes(stub)[0][2][1].endswith("\ndecided: assign #12")


def began(marker_comment: dict) -> datetime:
    """The start a logged marker records."""
    stamp = marker_comment["body"].splitlines()[1].split()[2]
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


class Pool:
    """`session.pages` and `session.gh` of the conductor, in process, from saved answers."""

    def __init__(self, monkeypatch, tmp_path, comments: list) -> None:
        self.root = tmp_path / "proj"
        (self.root / "config").mkdir(parents=True)
        (self.root / "config" / "reviewers.yaml").write_text(REVIEWERS, encoding="utf-8")
        (self.root / "agk.toml").write_text(ON, encoding="utf-8")
        self.table: dict = {
            f"repos/{REPO}/issues?state=open&labels=agk-conductor": [
                {"number": 204, "title": "Assignments", "labels": [{"name": "agk-conductor"}]}
            ],
            f"repos/{REPO}/issues/204/comments": comments,
            f"repos/{REPO}/issues/comments": [],
        }
        monkeypatch.setattr(conductor.session, "pages", self.pages)
        monkeypatch.setattr(conductor.session, "gh", lambda e, *x, method="GET": self.pages(e))
        monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
        monkeypatch.setattr(conductor.session, "conductor_issue", lambda repo: 204)

    def pages(self, endpoint: str):
        return self.table.get(endpoint, self.table.get(endpoint.split("?")[0]))


def test_the_sweep_prints_each_slots_last_run_and_decision(monkeypatch, tmp_path, capsys):
    """REQ-041, REQ-054: brief #998 (b)."""
    run = logged(1, "wait pr #977", 2, "active")
    found = Pool(monkeypatch, tmp_path, [run])
    monkeypatch.setattr(conductor, "proof_lines", lambda *a: [])
    monkeypatch.setattr(conductor.caps, "over_lines", lambda *a: [])
    monkeypatch.setattr(conductor, "branch_line", lambda *a: "main: success at abc")
    monkeypatch.setattr(conductor, "stall_report", lambda root, repo: [])
    found.table[f"repos/{REPO}/pulls?state=open"] = []
    found.table[f"repos/{REPO}"] = {"default_branch": "main"}
    found.table[f"repos/{REPO}/issues?state=open"] = []
    assert conductor.sweep(found.root) == 0
    out = capsys.readouterr().out.splitlines()
    start = began(run)
    row = [x for x in out if x.startswith("slot s1: ")]
    assert row == [f"slot s1: idle, last run {start:%H:%M} decided wait pr #977"], out
    assert [x for x in out if x.startswith("slot s2: ")] == ["slot s2: dead (no lease yet)"]


def unacted(monkeypatch, tmp_path, comments: list) -> list[str]:
    found = Pool(monkeypatch, tmp_path, comments)
    return conductor.unacted_lines(found.root, REPO, datetime.now(UTC))


def test_an_assign_older_than_a_run_that_decided_otherwise_is_unacted(monkeypatch, tmp_path):
    """REQ-041, REQ-054: brief #998 (c)."""
    run = logged(3, "wait", 40)
    said = [comment(2, "boss", "Assign: s1 #846 pr #965 fix list", ago(50)), run]
    found = Pool(monkeypatch, tmp_path, said)
    found.table[f"repos/{REPO}/issues/965/comments"] = []  # no `Report:` since the assignment
    lines = conductor.unacted_lines(found.root, REPO, datetime.now(UTC))
    start = began(run)
    assert lines == [
        f"UNACTED: Assign: s1 #846 pr #965 fix list (50 min; last run {start:%H:%M} decided wait)"
    ]


def test_an_assign_the_run_acted_on_is_not_unacted(monkeypatch, tmp_path):
    """REQ-041: the run that decided the assignment acted on it."""
    said = [comment(2, "boss", "Assign: s1 #12", ago(50)), logged(3, "assign #12", 40)]
    assert unacted(monkeypatch, tmp_path, said) == []


def test_an_assign_spent_by_an_earlier_run_is_not_unacted(monkeypatch, tmp_path):
    """REQ-041: a later run that waits on the pull request of the assigned brief is no miss."""
    found = Pool(monkeypatch, tmp_path, [comment(2, "boss", "Assign: s1 #12", ago(90)),
                                         logged(3, "wait pr #20", 40)])  # fmt: skip
    found.table[f"repos/{REPO}/issues/comments"] = [comment(5, "boss", f"taken: s1 {DAY}")]
    assert conductor.unacted_lines(found.root, REPO, datetime.now(UTC)) == []


def test_an_assign_newer_than_the_last_run_under_75_minutes_prints_nothing(monkeypatch, tmp_path):
    """REQ-041, REQ-054: brief #998 (d)."""
    said = [logged(2, "wait", 80), comment(3, "boss", "Assign: s1 #12", ago(74))]
    assert unacted(monkeypatch, tmp_path, said) == []


def test_an_assign_newer_than_the_last_run_over_75_minutes_is_unacted(monkeypatch, tmp_path):
    """REQ-041: brief #998 answer 2: no run in 75 minutes since the assignment."""
    said = [logged(2, "wait", 120), comment(3, "boss", "Assign: s1 #12", ago(76))]
    lines = unacted(monkeypatch, tmp_path, said)
    assert len(lines) == 1 and lines[0].startswith("UNACTED: Assign: s1 #12 (76 min; last run ")
    assert lines[0].endswith(" decided wait)")


def test_an_assign_none_or_by_an_unlisted_author_is_never_unacted(monkeypatch, tmp_path):
    """REQ-041"""
    said = [
        comment(2, "boss", "Assign: s1 none", ago(200)),
        comment(3, "stranger", "Assign: s2 #12", ago(200)),
        logged(4, "wait", 100),
    ]
    assert unacted(monkeypatch, tmp_path, said) == []


# --- reviewer slots (brief #1013 answer 2, ADR-0431) -----------------------------------------

HEAD = "c0ffee" + "1" * 34


def reviewer(proj, stub, *said: dict, pushed: tuple[str, ...] = (), run: str = "mine") -> None:
    """This checkout holds r1; #7 has the comments `said` and commits with the messages `pushed`."""
    mark(proj, run, "r1")
    stub.serve(COMMENTS, [marker(1, run, slot="r1"), comment(2, "boss", f"Review: r1 #7 {HEAD}")])
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")
    stub.serve(f"{ISSUES}/7/comments", list(said))
    commits = [{"sha": f"{i:040x}", "commit": {"message": m}} for i, m in enumerate(pushed, 1)]
    stub.serve(f"{PULLS}/7/commits", commits)


def test_d_a_review_line_gives_review_pr_n_sha(proj, stub):
    """REQ-046, REQ-054: brief #1013 (d)."""
    reviewer(proj, stub, pushed=("checkpoint: tests\n\nClaude-Session: https://example.com/s/9",))
    out = slot(proj, stub, "--next", "r1")
    assert out.returncode == 0, out.stdout + out.stderr
    assert last(out) == f"review pr #7 {HEAD}"
    assert all(c[1] == f"{ISSUES}/comments/1" for c in writes(stub))  # the lease, nothing else


def test_d_a_review_line_for_another_slot_or_by_an_unlisted_author_gives_wait(proj, stub):
    """REQ-046"""
    mark(proj, "mine", "r1")
    stub.serve(
        COMMENTS,
        [
            marker(1, "mine", slot="r1"),
            comment(2, "boss", f"Review: r2 #7 {HEAD}"),
            comment(3, "stranger", f"Review: r1 #7 {HEAD}"),
            comment(4, "boss", "Review: r1 #7 c0ffee"),  # not a full head
        ],
    )
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")
    assert last(slot(proj, stub, "--next", "r1")) == "wait"


def test_e_a_later_verdict_on_that_head_gives_wait(proj, stub):
    """REQ-046: brief #1013 (e); a verdict by any listed author answers the line."""
    for line in (f"Verdict: cleared {HEAD}", f"Verdict: fix list {HEAD[:12]} (conductor fallback)"):
        reviewer(proj, stub, comment(3, "second", line))
        assert last(slot(proj, stub, "--next", "r1")) == "wait", line


def test_e_a_verdict_on_another_head_or_by_an_unlisted_author_leaves_the_line_open(proj, stub):
    """REQ-046"""
    said = (comment(3, "boss", f"Verdict: cleared {'d' * 40}"),
            comment(4, "stranger", f"Verdict: cleared {HEAD}"))  # fmt: skip
    reviewer(proj, stub, *said)
    assert last(slot(proj, stub, "--next", "r1")) == f"review pr #7 {HEAD}"


@pytest.mark.parametrize(
    "message",
    [
        "checkpoint: tests\n\nSlot: r1",
        "fix\n\nthe r1 run pushed this",
        "fix\n\nClaude-Session: https://example.com/s/mine",
    ],
)
def test_f_a_reviewer_that_pushed_the_branch_is_refused(proj, stub, message):
    """REQ-046: brief #1013 (f); the slot's or this run's name in a commit's body or trailer."""
    reviewer(proj, stub, pushed=("first", message))
    out = slot(proj, stub, "--next", "r1")
    assert last(out) == "stop: reviewer pushed this branch"
    released = [c for c in writes(stub) if c[1] == f"{ISSUES}/comments/1"]
    assert released and "Slot: released" in " ".join(released[-1][2])


def test_f_a_name_inside_another_word_is_not_a_push(proj, stub):
    """REQ-046"""
    reviewer(proj, stub, pushed=("fix r10 and minecraft",))
    assert last(slot(proj, stub, "--next", "r1")) == f"review pr #7 {HEAD}"


def test_a_reviewer_slot_takes_its_lease_like_a_builder_slot(proj, stub):
    """REQ-046"""
    mark(proj, "mine", "r1")
    stub.serve(COMMENTS, [marker(9, "mine", slot="r1")], nth=2)
    out = slot(proj, stub, "--take", "r1")
    assert out.returncode == 0, out.stdout
    assert posts(stub)[0][2][1].endswith(" r1 mine")


# --- a stale `Assign:` frees its slot (brief #1020, ADR-0402) --------------------------------

import session_plan  # noqa: E402


def board(monkeypatch, *said: dict) -> None:
    """The assignments issue of `pending_assigns`, in process, with the comments `said`."""
    monkeypatch.setattr(session_plan, "conductor_comments", lambda repo: list(said))


def brief_pull(number: int, state: str = "open") -> dict:
    return {"number": 900 + number, "state": state, "title": f"brief #{number}",
            "body": f"Brief: #{number}\n"}  # fmt: skip


def plan_survey(comments: dict | None = None, prs: list | None = None) -> session_plan.Survey:
    return session_plan.Survey(REPO, "", 9, 8, prs or [], [], comments=comments or {})


def test_1020_a_an_assign_whose_brief_is_closed_leaves_the_slot_free(monkeypatch):
    """REQ-041: brief #1020 (a): #31 is not among the open briefs the plan read."""
    board(monkeypatch, comment(10, "boss", "Assign: s2 #31"), comment(11, "boss", "Assign: s3 #32"))
    found = session_plan.pending_assigns(plan_survey(), ["boss"], {32})
    assert found == {"s3": (32, None)}


def test_1020_b_an_assign_another_slot_took_later_leaves_the_slot_free(monkeypatch):
    """REQ-041: brief #1020 (b): s5 took #33 after the line to s8."""
    board(monkeypatch, comment(10, "boss", "Assign: s8 #33"))
    said = {33: [comment(12, "bot", f"taken: s5 {DAY}")]}
    assert session_plan.pending_assigns(plan_survey(said), ["boss"], {33}) == {}


def test_1020_b_a_take_before_the_line_or_released_still_holds_the_slot(monkeypatch):
    """REQ-041: only a live take after the line spends it."""
    board(monkeypatch, comment(10, "boss", "Assign: s8 #33"))
    said = {33: [comment(9, "bot", f"taken: s5 {DAY}"), comment(12, "bot", f"taken: s6 {DAY}"),
                 comment(13, "bot", "released: s6")]}  # fmt: skip
    assert session_plan.pending_assigns(plan_survey(said), ["boss"], {33}) == {"s8": (33, None)}


def test_1020_an_assign_whose_brief_has_an_open_pull_request_leaves_the_slot_free(monkeypatch):
    """REQ-041: brief #1020 answer 1, the third test; a closed pull request holds as before."""
    board(monkeypatch, comment(10, "boss", "Assign: s4 #34"), comment(11, "boss", "Assign: s5 #35"))
    prs = [brief_pull(34), brief_pull(35, "closed")]
    found = session_plan.pending_assigns(plan_survey(prs=prs), ["boss"], {34, 35})
    assert found == {"s5": (35, None)}


def test_1020_c_an_assign_with_an_open_brief_and_no_take_still_holds_the_slot(monkeypatch):
    """REQ-041: brief #1020 (c): today's behaviour."""
    board(monkeypatch, comment(10, "boss", "Assign: s3 #36"))
    said = {36: [comment(8, "bot", f"taken: s1 {DAY}")]}
    assert session_plan.pending_assigns(plan_survey(said), ["boss"], {36}) == {"s3": (36, None)}


def test_1020_d_when_the_briefs_cannot_be_read_the_slot_stays_held(monkeypatch):
    """REQ-041: brief #1020 (d): no open briefs read, so nothing is guessed free."""
    board(monkeypatch, comment(10, "boss", "Assign: s2 #31"))
    assert session_plan.pending_assigns(plan_survey(), ["boss"]) == {"s2": (31, None)}
    assert session_plan.pending_assigns(plan_survey(), ["boss"], None) == {"s2": (31, None)}


def stale(monkeypatch, tmp_path, line: str, issues, pulls, said=None) -> list[str]:
    """`unacted_lines` for one `Assign:` 90 minutes old, after a run that decided `wait`."""
    said_here = [logged(2, "wait", 100), comment(3, "boss", line, ago(90))]
    place = tmp_path / f"run{len(list(tmp_path.iterdir()))}"
    found = Pool(monkeypatch, place, said_here)
    if said is not None:
        found.table[f"repos/{REPO}/issues/33/comments"] = said
    return conductor.unacted_lines(found.root, REPO, datetime.now(UTC), issues, pulls)


def test_1020_b_the_sweep_prints_no_unacted_for_an_assign_another_slot_took(monkeypatch, tmp_path):
    """REQ-041, REQ-054: brief #1020 (b) and answer 2."""
    said = [comment(5, "bot", f"taken: s2 {DAY}")]
    assert stale(monkeypatch, tmp_path, "Assign: s1 #33", [{"number": 33}], [], said) == []


def test_1020_the_sweep_prints_no_unacted_for_a_closed_brief_or_an_open_pull(monkeypatch, tmp_path):
    """REQ-041: brief #1020 answer 2, the first and third tests."""
    assert stale(monkeypatch, tmp_path, "Assign: s1 #33", [{"number": 40}], []) == []
    open_pull = [brief_pull(33)]
    assert stale(monkeypatch, tmp_path, "Assign: s1 #33", [{"number": 33}], open_pull, []) == []


def test_1020_c_the_sweep_still_prints_unacted_for_an_open_untaken_brief(monkeypatch, tmp_path):
    """REQ-041: brief #1020 (c) and (d): an open brief, and briefs that cannot be read."""
    for issues in ([{"number": 33}], None):
        lines = stale(monkeypatch, tmp_path, "Assign: s1 #33", issues, [], [])
        assert len(lines) == 1 and lines[0].startswith("UNACTED: Assign: s1 #33 (90 min"), issues


# --- the shadow slot (brief #1014 answer 1, ADR-0432) ----------------------------------------

SAMPLED = "00000005" + "e" * 32  # 5 mod 5 is 0
SKIPPED = "00000006" + "e" * 32  # 6 mod 5 is 1
SHADOW_ISSUE = 219


def test_a_the_one_in_five_rule_picks_the_same_heads_from_the_same_shas():
    """REQ-054: brief #1014 (a): the first 8 hex characters as a number, mod 5, is 0."""
    import hashlib

    import session as kit_session

    shas = [hashlib.sha1(str(i).encode(), usedforsecurity=False).hexdigest() for i in range(500)]
    first = [s for s in shas if kit_session.shadow_sampled(s)]
    assert first == [
        s for s in shas if kit_session.shadow_sampled(s)
    ]  # the same shas, the same heads
    assert first == [s for s in shas if int(s[:8], 16) % 5 == 0]
    assert 70 <= len(first) <= 130  # about one in five
    assert kit_session.shadow_sampled("00000000" + "1" * 32)
    assert kit_session.shadow_sampled(SAMPLED) and not kit_session.shadow_sampled(SKIPPED)
    assert not kit_session.shadow_sampled("0000000")  # under 8 characters is never sampled
    assert not kit_session.shadow_sampled("not-hex-")


def shadowed(proj, stub, *lines: dict, answered: tuple[dict, ...] = ()) -> None:
    """This checkout holds s-shadow; the conductor issue has `lines`, the shadow's `answered`."""
    mark(proj, "mine", "s-shadow")
    stub.serve(COMMENTS, [marker(1, "mine", slot="s-shadow"), *lines])
    stub.serve(f"{ISSUES}/comments/1", {"id": 1}, method="PATCH")
    shadow_issue = {"number": SHADOW_ISSUE, "labels": [{"name": "agk-shadow"}]}
    stub.serve(ISSUES, [shadow_issue], nth=3)  # the lease's and the decision's reads come first
    stub.serve(f"{ISSUES}/{SHADOW_ISSUE}/comments", list(answered))


def test_a_shadow_line_gives_shadow_pr_n_sha_and_reads_no_verdict(proj, stub):
    """REQ-054: brief #1014 answer 1: the shadow slot's next step, blind."""
    shadowed(proj, stub, comment(2, "boss", f"Shadow: s-shadow #7 {SAMPLED}"))
    out = slot(proj, stub, "--next", "s-shadow")
    assert out.returncode == 0, out.stdout + out.stderr
    assert last(out) == f"shadow pr #7 {SAMPLED}"
    read = [c[1] for c in stub.calls() if c[0] == "GET"]
    assert not any(path.startswith(f"{ISSUES}/7") or path.startswith(PULLS) for path in read)
    assert all(c[1] == f"{ISSUES}/comments/1" for c in writes(stub))  # the lease, nothing else


def test_a_shadow_line_answered_unsampled_or_unlisted_gives_wait(proj, stub):
    """REQ-054: an answered head, a head outside the sample, another author or a short sha."""
    shadowed(
        proj,
        stub,
        comment(2, "boss", f"Shadow: s-shadow #7 {SAMPLED}"),
        comment(3, "boss", f"Shadow: s-shadow #8 {SKIPPED}"),
        comment(4, "stranger", f"Shadow: s-shadow #9 {SAMPLED}"),
        comment(5, "boss", "Shadow: s-shadow #10 00000005"),
        answered=(comment(6, "boss", f"Shadow: #7 {SAMPLED[:12]} fix list\nS1. a.py:1 x"),),
    )
    assert last(slot(proj, stub, "--next", "s-shadow")) == "wait"


def test_a_pool_stop_stops_the_shadow_slot(proj, stub):
    """REQ-054"""
    shadowed(
        proj,
        stub,
        comment(2, "boss", f"Shadow: s-shadow #7 {SAMPLED}"),
        comment(3, "owner", "Pool: stop"),
    )
    assert last(slot(proj, stub, "--next", "s-shadow")) == "stop"
