"""Every job has one record and one log, and `agk status` shows them (brief #1386, ADR-0584).

REQ-071. SPEC-0064 build (a), rules 3, 5 and 10. The adapters' process record `.agk-session-pid`
gains `kind=`, `item=` and `head=`, which `launch.py` hands them; `autopilot.py status` lists the
running jobs, the queue, the owner's waits, the held jobs and the quiet reason from the records and
the reads of one pass, posting nothing; each pass appends one line of numbers to
`agk-autopilot.jsonl` in the temp folder and `status --week` prints the week. The process table,
the GitHub reads and the clock are test doubles; sessions are invented (`cb-example-1`).
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_conductor_watchdog import ROOT, posix, start_posix  # noqa: F401

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
PLAN = "Start 1: cb-example-3 takes #12.\nCapacity: 1 slot."
QUIET_PLAN = "Start 0: no brief is ready.\nCapacity: 1 slot."
SWEEP = (
    "#40 waits for a verdict\n"
    "NEEDS-YOU: #41 a question for the maintainers\n"
    "NEEDS-YOU: builder cb-example-9 #44 held (unpushed work)"
)


def record(worktree: Path, session: str, pid: int, **extra: str) -> None:
    worktree.mkdir(parents=True, exist_ok=True)
    lines = [f"session={session}", f"pid={pid}", "started_utc=2026-11-16T10:00:00Z", "brief=7"]
    lines += [f"{k}={v}" for k, v in extra.items()]
    (worktree / ".agk-session-pid").write_text("\n".join(lines) + "\n", encoding="utf-8")


def reads(monkeypatch, plan: str = PLAN, sweep: str = SWEEP) -> list:
    """The pass's GitHub reads as doubles; returns the functions that status asked for."""
    import conductor
    import session
    import session_plan

    asked: list = []
    said = {session_plan.plan: (0, plan), conductor.sweep: (0, sweep)}

    def quietly(act, *args):
        asked.append(act)
        return said.get(act, (0, "fingerprint abc"))

    monkeypatch.setattr(session, "quietly", quietly)
    return asked


# --- rule 3: the job record ---------------------------------------------------------------


def test_launch_hands_each_job_its_kind_item_and_head(tmp_path):
    """REQ-071 AC3: rule 3 (a start is a `build` of its brief; a resume with a pull request a `fix`)."""
    import launch

    root = tmp_path / "proj"
    root.mkdir()
    seen = tmp_path / "env.jsonl"
    adapter = (
        f"{sys.executable} -c \"import json,os; open({str(seen)!r}, 'a').write(json.dumps("
        "{k: os.environ.get(k, '') for k in ('AGK_JOB_KIND', 'AGK_ITEM', 'AGK_HEAD')}) + '\\n')\""
    )
    found = [("cb-example-1", 7, None), ("cb-example-2", 8, None)]
    assert launch.start_with(adapter, found, root=root, jobs=[None, ("fix", 1392)]) == 0
    got = [json.loads(x) for x in seen.read_text(encoding="utf-8").splitlines()]
    assert got[0] == {"AGK_JOB_KIND": "build", "AGK_ITEM": "#7", "AGK_HEAD": ""}
    assert got[1] == {"AGK_JOB_KIND": "fix", "AGK_ITEM": "#1392", "AGK_HEAD": ""}


def test_the_record_reads_its_kind_item_and_head_and_an_older_one_still_reads(tmp_path):
    """REQ-071 AC3: rule 3 (a #1355 record without the new fields stays a record)."""
    import launch

    record(tmp_path / "a", "cb-example-1", 42, kind="fix", item="#1392", head="abc1234")
    record(tmp_path / "b", "cb-example-2", 43)
    record(tmp_path / "c", "cb-example-3", 44, kind="painter", item="x")
    a, b, c = (launch.read_record(tmp_path / x) for x in "abc")
    assert (a["kind"], a["item"], a["head"]) == ("fix", "#1392", "abc1234")
    assert (b["kind"], b["item"], b["head"]) == (None, None, None)
    assert (c["kind"], c["item"]) == (None, None)  # an unknown kind or item is not read


def test_a_second_job_of_a_live_name_is_refused_naming_the_session(tmp_path, capsys):
    """REQ-071 AC1: rule 3 (a name with a live record is never started twice)."""
    import launch

    root = tmp_path / "proj"
    root.mkdir()
    record(tmp_path / "agk-cb-example-1", "cb-example-1", os.getpid(), kind="build", item="#7")
    calls = tmp_path / "calls.txt"
    adapter = f"{sys.executable} -c \"open({str(calls)!r}, 'a').write('x')\""
    assert launch.start_with(adapter, [("cb-example-1", 7, None)], root=root) == 1
    err = capsys.readouterr().err
    assert "session cb-example-1 is still running" in err and str(tmp_path) not in err
    assert not calls.exists()


def test_the_posix_adapter_records_the_job_and_keeps_its_log_out_of_git(posix):  # noqa: F811
    """REQ-071 AC3: rule 3 (kind=, item=, head= in the record; the log file is excluded)."""
    posix["env"].update(AGK_BRIEF="7", AGK_JOB_KIND="fix", AGK_ITEM="#1392", AGK_HEAD="abc1234")
    done = start_posix(posix)
    assert done.returncode == 0, done.stderr
    for _ in range(300):
        if (posix["worktree"] / ".agk-session-exit").exists():
            break
        time.sleep(0.1)
    lines = (posix["worktree"] / ".agk-session-pid").read_text(encoding="utf-8").splitlines()
    assert lines[4:] == ["kind=fix", "item=#1392", "head=abc1234"]
    assert (posix["worktree"] / ".agk-session.log").exists()
    status = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(posix["worktree"]), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert status.stdout == ""


def test_the_windows_adapter_records_the_job_and_excludes_its_log():
    """REQ-071 AC3: rule 3 (no PowerShell runs here: the template's lines)."""
    text = (ROOT / "kit" / "templates" / "start-session-windows.ps1").read_text(encoding="utf-8")
    assert "kind=$Kind" in text and "item=$Item" in text and "head=$Head" in text
    assert "AGK_JOB_KIND" in text and "'.agk-session.log'" in text


# --- rule 5: agk status ---------------------------------------------------------------------


def test_status_lists_jobs_queue_owner_waits_held_and_reports_an_unrecorded_process(
    tmp_path, monkeypatch, capsys
):
    """REQ-071 AC3 and AC1: rules 3 and 5 (each field; an unrecorded session is never adopted)."""
    import autopilot
    import launch

    root = tmp_path / "proj"
    root.mkdir()
    live = tmp_path / "agk-cb-example-1"
    record(live, "cb-example-1", 101, kind="build", item="#7", head="abc1234")
    (live / ".agk-session.log").write_text("working\n", encoding="utf-8")
    record(tmp_path / "agk-cb-example-2", "cb-example-2", 102, kind="review", item="#40")
    monkeypatch.setattr(launch, "process_alive", lambda pid: pid == 101)
    table = [
        (101, 1, "bash -c wrapper"),
        (201, 101, "claude -p go"),  # inside a recorded job: not reported
        (301, 1, "claude --agent steward"),  # a person's own steward
        (401, 1, "claude -p something"),  # no record
    ]
    monkeypatch.setattr(autopilot, "claude_processes", lambda: table)
    reads(monkeypatch)
    assert autopilot.main(["status", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "job cb-example-1 build #7 head abc1234 since 2026-11-16T10:00:00Z last log" in out
    assert "cb-example-2" not in out  # its process is gone: not a running job
    assert "queue: Start 1: cb-example-3 takes #12." in out
    assert "owner: NEEDS-YOU: #41 a question for the maintainers" in out
    assert "held: NEEDS-YOU: builder cb-example-9 #44 held (unpushed work)" in out
    assert "unrecorded: process 401 (not adopted)" in out
    assert "process 201" not in out and "process 301" not in out
    assert "quiet:" not in out and str(tmp_path) not in out


@pytest.mark.parametrize(
    "toml, plan, quiet",
    [
        ("", QUIET_PLAN, "quiet: no brief is ready"),
        ("paused = true\n", PLAN, "quiet: paused (setting: paused)"),
    ],
)
def test_status_says_why_the_supervisor_is_quiet(tmp_path, monkeypatch, capsys, toml, plan, quiet):
    """REQ-071 AC3: rule 5 (the quiet reason, said once)."""
    import autopilot

    root = tmp_path / "proj"
    root.mkdir()
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    monkeypatch.setattr(autopilot, "claude_processes", lambda: [])
    reads(monkeypatch, plan=plan)
    assert autopilot.main(["status", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert out.count("quiet:") == 1 and quiet in out and "jobs: none" in out


def test_status_makes_at_most_the_reads_of_one_pass_and_posts_nothing(tmp_path, monkeypatch):
    """REQ-071 AC3: rule 5 (its reads are a subset of the pass's; the script holds no write)."""
    import autopilot
    import conductor

    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setattr(autopilot, "claude_processes", lambda: [])
    asked = reads(monkeypatch)
    autopilot.main(["status", "--root", str(root)])
    mine = list(asked)
    asked.clear()
    conductor.pass_facts(root)
    assert mine and set(mine) <= set(asked) and len(mine) <= len(asked)
    text = (ROOT / "scripts" / "agk" / "autopilot.py").read_text(encoding="utf-8")
    for word in ("POST", "PATCH", "PUT", "DELETE", "-X", "--method", "-f "):
        assert word not in text


# --- rule 10: the health file ---------------------------------------------------------------


def test_each_pass_appends_one_line_to_the_temp_folder_and_none_to_the_checkout(
    tmp_path, monkeypatch
):
    """REQ-071 AC7: rule 10 (numbers, kinds and times only)."""
    import autopilot

    temp, root = tmp_path / "temp", tmp_path / "proj"
    temp.mkdir()
    root.mkdir()
    monkeypatch.setattr(autopilot.tempfile, "gettempdir", lambda: str(temp))
    autopilot.append_health(
        {"started": {"build": 2}, "ended": 1, "failed": 0, "held": 1, "merged": 1, "waits": [60]},
        NOW,
    )
    autopilot.append_health({"started": {}, "ended": 0, "failed": 0, "held": 0}, NOW)
    lines = (temp / "agk-autopilot.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["at"] == "2026-11-16T12:00:00Z"
    assert list(root.iterdir()) == []
    with pytest.raises(autopilot.CheckError, match="numbers"):
        autopilot.append_health({"started": {"build": "a comment's text"}}, NOW)
    with pytest.raises(autopilot.CheckError, match="kind"):
        autopilot.append_health({"started": {"painter": 1}}, NOW)


def test_status_week_prints_the_week_and_unknown_for_what_it_cannot_read(
    tmp_path, monkeypatch, capsys
):
    """REQ-071 AC7: rule 10 (a figure that cannot be read is `unknown`, never 0)."""
    import autopilot

    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(autopilot.tempfile, "gettempdir", lambda: str(temp))
    old = {"started": {"build": 9}, "ended": 9, "failed": 9, "held": 9, "merged": 9}
    autopilot.append_health(old, NOW - timedelta(days=8))
    autopilot.append_health(
        {"started": {"build": 2, "review": 1}, "ended": 2, "failed": 1, "held": 1, "merged": 2,
         "waits": [60, 180]},
        NOW - timedelta(days=1),
    )  # fmt: skip
    (temp / "agk-autopilot.jsonl").open("a", encoding="utf-8").write("not json\n")
    monkeypatch.setattr(autopilot, "week_tokens", lambda root, since: 5000)
    assert autopilot.week(tmp_path, NOW) == 0
    out = capsys.readouterr().out
    assert "jobs: started 3 (build 2, review 1), ended 2, failed 1, held 1" in out
    assert "event to start: median 2 min, longest 3 min" in out
    assert "tokens per merged pull request: 2500 (2 merged)" in out
    monkeypatch.setattr(autopilot, "week_tokens", lambda root, since: None)
    (temp / "agk-autopilot.jsonl").write_text("", encoding="utf-8")
    assert autopilot.week(tmp_path, NOW) == 0
    out = capsys.readouterr().out
    assert "event to start: unknown" in out and "tokens per merged pull request: unknown" in out
