"""Builders as short jobs, resumed from a sectioned summary, held after two failures.

REQ-071 AC2: *every AI session is a short job that ends* (SPEC-0064 rules 4 and 9, build (c),
brief #1389, ADR-0586). An ended builder waits for its event with no session open; the supervisor
starts one `fix` job on a verdict, a correction, an answer, a conflict or a red check, whose prompt
says to end at its `Report:` and never run `watch`; a job that fails or ends with no progress twice
in a row is held until the head or a listed author's comment changes; `session.py summary`
refuses a summary missing a fixed section. The recorded double of `test_watchdog_builders` (saved
GitHub answers through the `gh` stub, an adapter double, a fake process table); invented names,
no network.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_conductor_watchdog import starts, stub, world  # noqa: F401
from test_session import REPO, SHA, Stub, comment, iso, pull, session
from test_watchdog_builders import builder_line, builders, pr_comments, watchdog  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import conductor  # noqa: E402
import launch  # noqa: E402

NEW = "b" * 40


def fix_list(builders, minutes: int = 60, *more: dict) -> None:  # noqa: F811
    """Its `Report:` two hours ago, then a fix list MINUTES ago, then MORE."""
    pr_comments(
        builders,
        comment(2, "builder", "Report: aaaaaaa ready for review", iso(timedelta(hours=-2))),
        comment(3, "boss", "Verdict: fix list aaaaaaa", iso(timedelta(minutes=-minutes))),
        *more,
    )


def age_restart(builders) -> None:  # noqa: F811
    """Move the last restart two hours back, past the one restart per hour."""
    root = builders["repo"].root
    memo = conductor.builder_memo(root)
    memo["restarts"][builders["name"]] = conductor.stamp_of(datetime.now(UTC) - timedelta(hours=2))
    conductor.keep_builder_memo(root, memo)


def new_head(builders, sha: str = NEW) -> None:  # noqa: F811
    head = {"sha": sha, "ref": "claude/brief-7"}
    builders["stub"].serve(
        f"repos/{REPO}/pulls",
        [{"number": 70, "state": "open", "body": "Brief: #7", "head": head, "labels": [],
          "user": {"login": "builder"}, "created_at": iso(timedelta(hours=-2))}],
    )  # fmt: skip
    builders["stub"].serve(
        f"repos/{REPO}/commits/{sha}", {"commit": {"committer": {"date": iso(timedelta(hours=-2))}}}
    )


# --- rule 4: a builder job ends at ready; the next starts only on its event -------------------


def test_an_ended_builder_whose_report_is_newest_waits_with_no_session(builders, capsys):  # noqa: F811
    """REQ-071 AC2: a build job ends at ready with its Report:; no job starts until the verdict."""
    builders["table"].clear()
    pr_comments(builders, comment(2, "builder", "Report: aaaaaaa ready for review", iso()))
    code, out = watchdog(builders, capsys)
    assert code == 0
    assert (
        builder_line(out)
        == f"watchdog: builder {builders['name']} #7 ended -> left (waits for an event)"
    )
    assert starts(builders) == []
    assert conductor.held_builder_lines(builders["repo"].root) == []  # nothing waits on a person


def test_a_verdict_starts_one_fix_job_that_ends_without_watch(builders, capsys, monkeypatch):  # noqa: F811
    """REQ-071 AC2: the next job starts only on the verdict, as a `fix` job of the pull request,
    resumed from the summary, and its prompt says it never runs `session.py watch`."""
    seen: list = []
    real = launch.start_with

    def spy(*args):
        seen.append(args[5] if len(args) > 5 else None)
        return real(*args)

    monkeypatch.setattr(launch, "start_with", spy)
    builders["table"].clear()
    fix_list(builders)
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 ended -> restarted"
    got = starts(builders)
    assert len(got) == 1 and seen == [[("fix", 70)]]
    prompt = got[0]["prompt"]
    assert "resume --pr 70" in prompt and "one short job" in prompt
    assert "never run `session.py watch`" in prompt and "working summary" in prompt
    _, out = watchdog(builders, capsys)  # a second pass within the hour starts none
    assert len(starts(builders)) == 1


@pytest.mark.parametrize("label", ["agk:conflict", "agk:ci-red"])
def test_a_conflict_or_a_red_check_starts_the_next_job(builders, capsys, label):  # noqa: F811
    """REQ-071 AC2: a merge-of-main or conflict need and a red check are events too."""
    builders["table"].clear()
    pr_comments(
        builders,
        comment(2, "builder", "Report: aaaaaaa ready for review", iso(timedelta(hours=-2))),
    )
    head = {"sha": "a" * 40, "ref": "claude/brief-7"}
    builders["stub"].serve(
        f"repos/{REPO}/pulls",
        [{"number": 70, "state": "open", "body": "Brief: #7", "head": head,
          "labels": [{"name": label}], "user": {"login": "builder"}, "created_at": iso()}],
    )  # fmt: skip
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 ended -> restarted"


def test_a_job_with_a_fresh_lock_heartbeat_is_never_stopped():
    """REQ-071 AC2: #1355's signs of work keep a job live, so the supervisor never cuts it."""
    now = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    args = (True, False, now - timedelta(hours=3), now - timedelta(hours=2), now, 60, True)
    assert conductor.builder_state(*args) == "idle"
    assert conductor.builder_state(*args, busy=["lock"]) == "live"
    assert conductor.builder_action("live", final=False, parked=False, recent=False, room=True,
                                    safe=True) == ("left", None)  # fmt: skip


# --- rule 9: a job failing twice for one pull request is held ---------------------------------


def test_a_job_failing_twice_is_held_until_the_head_changes(builders, capsys):  # noqa: F811
    """REQ-071 AC2: no progress twice in a row is `held (failed twice)`, named for the next
    conductor pass and `agk status`, not retried until a new head."""
    builders["table"].clear()
    name = builders["name"]
    fix_list(builders)
    _, out = watchdog(builders, capsys)  # the fix job starts
    assert builder_line(out) == f"watchdog: builder {name} #7 ended -> restarted"
    age_restart(builders)
    _, out = watchdog(builders, capsys)  # it ended with nothing new: one failure, one retry
    assert builder_line(out) == f"watchdog: builder {name} #7 ended -> restarted"
    age_restart(builders)
    for _ in range(2):  # the second failure holds it, and it stays held
        _, out = watchdog(builders, capsys)
        assert builder_line(out) == f"watchdog: builder {name} #7 ended -> held (failed twice)"
        age_restart(builders)
    assert len(starts(builders)) == 2
    assert conductor.held_builder_lines(builders["repo"].root) == [
        f"NEEDS-YOU: builder {name} #7 held (failed twice)"
    ]
    new_head(builders)
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {name} #7 ended -> restarted"
    assert conductor.held_builder_lines(builders["repo"].root) == []


def test_a_held_job_is_retried_on_a_new_comment_by_a_listed_author(builders, capsys):  # noqa: F811
    """REQ-071 AC2: a listed author's newer comment releases the hold."""
    builders["table"].clear()
    fix_list(builders, 90)
    for _ in range(3):
        watchdog(builders, capsys)
        age_restart(builders)
    _, out = watchdog(builders, capsys)
    assert out.count("held (failed twice)") == 1
    fix_list(
        builders, 90, comment(4, "boss", "Verdict: fix list aaaaaaa", iso(timedelta(minutes=-5)))
    )
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {builders['name']} #7 ended -> restarted"


def test_a_job_that_made_progress_clears_the_count_and_waits(builders, capsys):  # noqa: F811
    """REQ-071 AC2: a job that posted its Report: is no failure; its pull request waits."""
    builders["table"].clear()
    fix_list(builders)
    watchdog(builders, capsys)
    age_restart(builders)
    done = comment(5, "builder", "Report: aaaaaaa fix list applied", iso())
    fix_list(builders, 60, done)
    _, out = watchdog(builders, capsys)
    assert (
        builder_line(out)
        == f"watchdog: builder {builders['name']} #7 ended -> left (waits for an event)"
    )
    assert conductor.builder_memo(builders["repo"].root)["jobs"][builders["name"]]["fails"] == 0


@pytest.mark.parametrize(
    "code, mark, fails", [("0", "moved", 0), ("1", "moved", 1), (None, "same", 1), ("0", "same", 1)]
)
def test_a_job_fails_on_an_exit_code_or_no_progress(code, mark, fails):
    """REQ-071 AC2: a code other than 0, or the same head, posts and summary, is a failure;
    an end is counted once."""
    job = {"open": True, "mark": "same", "fails": 0}
    facts = {"mark": mark}
    conductor.job_ended(job, facts, code)
    assert job["fails"] == fails and job["open"] is False
    conductor.job_ended(job, facts, code)
    assert job["fails"] == fails


# --- the summary's fixed sections (Q-S0064-1 as ruled) -----------------------------------------

SECTIONED = (
    "Built: the short jobs.\n"
    "Decisions and why: one job per event, so no session waits.\n"
    "Alternatives rejected: one session across fix lists.\n"
    "Risks: a label that stays after the fix.\n"
    "How to run the tests: pytest tests/kit/test_autopilot_build_jobs.py\n"
    "Where it is stuck: nowhere.\n"
)
PR = f"repos/{REPO}/pulls/7"
COMMENTS = f"repos/{REPO}/issues/7/comments"


@pytest.fixture
def proj(repo, tmp_path):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss]\n")
    return repo


def test_a_summary_with_every_section_is_posted(proj, tmp_path):
    """REQ-071 AC2: the five sections fit `[flow] summary_lines` and the summary is accepted."""
    double = Stub(tmp_path)
    double.serve(PR, pull())
    double.serve(COMMENTS, [])
    text = tmp_path / "summary.md"
    text.write_text(SECTIONED, encoding="utf-8")
    out = session(proj, double, "summary", "--pr", "7", "--file", str(text))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == f"summary: posted at {SHA[:7]}"


@pytest.mark.parametrize(
    "section",
    ["Decisions and why:", "Alternatives rejected:", "Risks:", "How to run the tests:",
     "Where it is stuck:"],
)  # fmt: skip
def test_a_summary_missing_a_section_is_refused_naming_it(proj, tmp_path, section):
    """REQ-071 AC2: a summary missing one fixed section is refused naming it; nothing posted."""
    double = Stub(tmp_path)
    double.serve(PR, pull())
    double.serve(COMMENTS, [])
    text = tmp_path / "summary.md"
    text.write_text(
        "".join(x + "\n" for x in SECTIONED.splitlines() if not x.startswith(section)),
        encoding="utf-8",
    )
    out = session(proj, double, "summary", "--pr", "7", "--file", str(text))
    assert out.returncode == 1
    assert f"summary: refused: the section `{section}` is missing" in out.stdout
    assert [c for c in double.calls() if c[0] != "GET"] == []


# --- the texts: session rules 10 and 18 and the builder's task --------------------------------


def test_the_rules_and_the_builder_text_say_a_job_ends_and_never_watches():
    """REQ-071 AC2: no job runs `session.py watch`; the builder text names the five sections."""
    rules = (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")
    ten = next(x for x in rules.splitlines() if x.startswith("10. "))
    assert "short job" in ten and "never running `watch`" in ten and "failed twice" in ten
    eighteen = next(x for x in rules.splitlines() if x.startswith("18. "))
    assert "A short job (rule 10) ends at its `Report:`" in eighteen
    body = (ROOT / "kit" / "templates" / "runtime" / "builder.txt").read_text(encoding="utf-8")
    jobs = next(x for x in body.split("\n\n") if x.startswith("SHORT JOBS"))
    assert "Never run `session.py watch`" in jobs and "held" in jobs
    for words in ("Decisions and why:", "Alternatives rejected:", "Risks:",
                  "How to run the tests:", "Where it is stuck:"):  # fmt: skip
        assert words in body, words
