"""Every mode runs the same autopilot jobs (brief #1391, SPEC-0064 build (f), rule 13, ADR-0589).

REQ-071 AC8: *the same in every mode, solo or team.* `autopilot.pick` chooses the jobs of a pass
from GitHub-shaped records of any forge: CI mode's launcher reads them with `autopilot.py jobs`,
a local machine's builders get the same fix rule as build (c)'s `conductor.job_gate`, and
`agk next` runs one of them in the foreground in personal mode, posting nothing. A job another
machine claimed is held until its take lapses. Saved records, a `gh` stub that keeps its calls, a
stub adapter and a fake clock only; invented data (`cb-example-1`, `example.com`); no network.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import autopilot  # noqa: E402
import conductor  # noqa: E402
import personal_state as ps  # noqa: E402
from forge import FilesForge  # noqa: E402

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
RUNTIME = ROOT / "kit" / "templates" / "runtime"


def at(minutes: int) -> str:
    return (NOW + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def said(cid: int, body: str, minutes: int, login: str = "builder") -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": at(minutes)}


def pr(number: int, brief: int, labels: tuple[str, ...] = (), draft: bool = False) -> dict:
    return {"number": number, "state": "open", "draft": draft, "body": f"Brief: #{brief}",
            "created_at": at(-600), "labels": [{"name": x} for x in labels],
            "user": {"login": "builder"}, "head": {"sha": "a" * 40}}  # fmt: skip


def brief(number: int, body: str = "") -> dict:
    return {"number": number, "state": "open", "body": body, "labels": [{"name": "agk-brief"}]}


def records() -> tuple[list, list, dict]:
    """#71 waits for review, #72 has a fix list, #73 is a draft being built, #9 and #10 free,
    #11 waits on the open #10, #8 is named by #73."""
    pulls = [pr(71, 5), pr(72, 6), pr(73, 8, draft=True)]
    comments = {
        71: [said(1, "Report: aaaaaaa ready for review", -30)],
        72: [said(2, "Report: aaaaaaa ready for review", -120),
             said(3, "Verdict: fix list aaaaaaa", -60, "boss")],
        73: [said(4, "Progress: aaaaaaa done 1/5; next: tests", -30)],
    }  # fmt: skip
    briefs = [brief(8), brief(9), brief(10), brief(11, "Depends-on: #10")]
    return pulls, briefs, comments


def kinds(jobs: list) -> list[tuple]:
    return [(j["kind"], j["item"], j["session"]) for j in jobs]


# --- the jobs of a pass, by the supervisor's rules -----------------------------------------------


def test_one_pass_picks_one_review_one_fix_and_the_free_builds():
    """REQ-071 AC8: review first, then the fix list's job, then the briefs nobody holds."""
    pulls, briefs, comments = records()
    jobs, held = autopilot.pick(pulls, briefs, comments, NOW)
    assert kinds(jobs) == [
        ("review", 71, "conductor"), ("fix", 72, "cb6"), ("build", 9, "cb9"), ("build", 10, "cb10"),
    ]  # fmt: skip
    assert held == []


def test_the_plan_decides_the_builds_where_github_has_one():
    """REQ-071 AC8: with the plan's starts (team and CI mode), only those, with their build."""
    pulls, briefs, comments = records()
    jobs, _ = autopilot.pick(pulls, briefs, comments, NOW, {10: "b"})
    assert [j for j in kinds(jobs) if j[0] == "build"] == [("build", 10, "cb10b")]


def test_the_fix_rule_is_build_c_s_job_gate():
    """REQ-071 AC8: the CI pass starts the same fix jobs as a local pass: a fix job exactly where
    `conductor.job_gate` sees an event (an owed verdict, a conflict or red-check label)."""
    for labels, owed in (
        ((), True),
        ((), False),
        (("agk:conflict",), False),
        (("agk:ci-red",), False),
    ):
        comments = {72: [said(2, "Report: aaaaaaa fix list applied", -120)]}
        if owed:
            comments[72].append(said(3, "Correction: the cause is elsewhere", -60, "boss"))
        own = datetime.strptime(at(-120), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        facts = {"own": own, "owed": conductor.newest(comments[72], conductor.OWED),
                 "labels": set(labels)}  # fmt: skip
        local = conductor.job_gate(None, facts, NOW) is None
        jobs, _ = autopilot.pick([pr(72, 6, labels)], [], comments, NOW)
        assert (("fix", 72, "cb6") in kinds(jobs)) is local, (labels, owed)


def test_a_clearing_verdict_starts_no_builder_job():
    """REQ-071 AC8: a cleared pull request waits for its merge; no fix job and no review loop."""
    comments = {72: [said(2, "Report: aaaaaaa ready for review", -120),
                     said(3, "Verdict: cleared aaaaaaa", -60, "boss")]}  # fmt: skip
    assert autopilot.pick([pr(72, 6)], [], comments, NOW) == ([], [])


def test_another_machines_claim_holds_the_job_until_its_take_lapses():
    """REQ-071 AC8: two machines never run one job, and one never restarts the other's before
    its take lapses (Q-S0064-4)."""
    pulls, briefs, comments = records()
    first, _ = autopilot.pick(pulls, briefs, comments, NOW)
    for job in first:  # machine A claims each build and fix job before it starts it
        if job["kind"] != "review":
            body = f"Started: {job['session']} {at(0)} by the supervisor ({job['kind']})"
            comments.setdefault(job["item"], []).append(said(90 + job["item"], body, 0, "a"))
    second, held = autopilot.pick(pulls, briefs, comments, NOW + timedelta(minutes=1))
    assert kinds(second) == [("review", 71, "conductor")]
    assert sorted((h["item"], h["by"]) for h in held) == [(9, "cb9"), (10, "cb10"), (72, "cb6")]
    later = NOW + timedelta(hours=conductor.START_HOURS, minutes=1)
    lapsed, held = autopilot.pick(pulls, briefs, comments, later)
    assert held == [] and len(lapsed) == len(first)


def test_a_new_event_after_a_claim_starts_the_next_job():
    """REQ-071 AC8: a claim holds only the event it was made for; a newer verdict is a new job."""
    pulls, briefs, comments = records()
    comments[72].append(said(7, "Started: cb6 x by the supervisor (fix)", -50, "a"))
    assert autopilot.pick(pulls, [], comments, NOW)[1][0]["item"] == 72
    comments[72].append(said(8, "Verdict: fix list aaaaaaa", -10, "boss"))
    jobs, held = autopilot.pick(pulls, [], comments, NOW)
    assert ("fix", 72, "cb6") in kinds(jobs) and held == []


def test_solo_and_team_start_the_same_jobs(tmp_path, monkeypatch, capsys):
    """REQ-071 AC8: the review mode changes who answers, never which jobs start."""
    out = []
    for mode in ("solo", "team"):
        root = tmp_path / mode
        root.mkdir()
        (root / "agk.toml").write_text(f'review_mode = "{mode}"\n', encoding="utf-8")
        monkeypatch.setattr(autopilot.session, "repo_name", lambda r: "example/widgets")
        monkeypatch.setattr(autopilot, "github_records", lambda r, repo: (*records(), None))
        monkeypatch.setattr(autopilot.conductor, "plan_issue", lambda r: None)
        assert autopilot.main(["jobs", "--root", str(root)], NOW) == 0
        out.append(capsys.readouterr().out)
    assert out[0] == out[1] and "job: fix #72 cb6" in out[0]


def test_jobs_claims_before_it_names_a_job_and_the_setting_gates_it(tmp_path, monkeypatch, capsys):
    """REQ-071 AC8 and AC5: `jobs --claim` posts one `Started:` per build or fix job first;
    `mode = "off"` names the setting and claims nothing."""
    posted = []
    monkeypatch.setattr(autopilot.session, "repo_name", lambda r: "example/widgets")
    monkeypatch.setattr(autopilot, "github_records", lambda r, repo: (*records(), None))
    monkeypatch.setattr(autopilot.conductor, "plan_issue", lambda r: None)
    monkeypatch.setattr(autopilot.session, "gh", lambda e, *x, method="GET": posted.append(e) or {})
    root = tmp_path / "proj"
    root.mkdir()
    (root / "agk.toml").write_text("", encoding="utf-8")
    assert autopilot.main(["jobs", "--claim", "--root", str(root)], NOW) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[:4] == ["job: review #71 conductor", "job: fix #72 cb6", "job: build #9 cb9",
                         "job: build #10 cb10"]  # fmt: skip
    assert posted == [f"repos/example/widgets/issues/{n}/comments" for n in (72, 9, 10)]
    posted.clear()
    (root / "agk.toml").write_text('[autopilot]\nmode = "off"\n', encoding="utf-8")
    autopilot.main(["jobs", "--claim", "--root", str(root)], NOW)
    out = capsys.readouterr().out
    assert "not started: fix #72 cb6 (mode off (setting: autopilot.mode))" in out
    assert posted == []


# --- personal mode: `agk next` runs one job in the foreground and posts nothing ------------------

ADAPTER = """import os, pathlib, sys
sys.stdin.read()
w = pathlib.Path.cwd().resolve().parent / ("agk-" + os.environ["AGK_SESSION"])
w.mkdir(exist_ok=True)
(w / ".agk-session-pid").write_text("session=%s\\npid=1\\nstarted_utc=2026-11-16T12:00:00Z\\n"
    "brief=%s\\nkind=%s\\nitem=%s\\n" % (os.environ["AGK_SESSION"], os.environ.get("AGK_BRIEF", ""),
    os.environ["AGK_JOB_KIND"], os.environ["AGK_ITEM"]))
(w / ".agk-session-exit").write_text("exit_code=0\\nended_utc=2026-11-16T12:05:00Z\\n")
"""


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def sidecar(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "sidecar"
    ps.make_sidecar(path, "demo-dev")
    adapter = tmp_path / "adapter.py"
    adapter.write_text(ADAPTER, encoding="utf-8")
    with (path / "agk.toml").open("a", encoding="utf-8") as out:
        out.write(f'\n[flow]\nlaunch_adapter = "{sys.executable} {adapter}"\n')
    gh = tmp_path / "bin" / "gh"  # a `gh` that only records that it was called
    gh.parent.mkdir()
    gh.write_text(f"#!/bin/sh\necho called >> {tmp_path / 'gh.log'}\nexit 1\n", encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{gh.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(autopilot, "SLEEP", lambda s: None)
    return path


def test_next_in_personal_mode_runs_one_fix_job_and_posts_nothing(sidecar, tmp_path, capsys):
    """REQ-071 AC8: `agk next` reads the files forge, runs one job through the adapter in the
    foreground, waits for its end and posts nothing: no `gh`, no new forge comment."""
    files = FilesForge(sidecar, env={})
    number = files.create_issue("A page", "Size: S", ["agk-brief"])
    pull = files.record_pull("A page", f"Brief: #{number}", "a" * 40, "feature", "main")
    files.comment(pull, "Report: aaaaaaa ready for review")
    files.comment(pull, "Verdict: fix list aaaaaaa")
    data = json.loads((sidecar / "forge" / f"comments-{pull}.json").read_text(encoding="utf-8"))
    data[0]["created_at"], data[1]["created_at"] = at(-120), at(-60)
    (sidecar / "forge" / f"comments-{pull}.json").write_text(json.dumps(data), encoding="utf-8")
    before = git(sidecar, "log", "--oneline")
    assert autopilot.main(["next", "--root", str(sidecar)], NOW) == 0
    out = capsys.readouterr().out
    assert f"next: fix #{pull} cb{number}" in out and f"next: cb{number} ended (exit 0)" in out
    record = (tmp_path / f"agk-cb{number}" / ".agk-session-pid").read_text(encoding="utf-8")
    assert "kind=fix" in record and f"item=#{pull}" in record
    assert not (tmp_path / "gh.log").exists()
    assert git(sidecar, "log", "--oneline") == before
    assert len(json.loads((sidecar / "forge" / f"comments-{pull}.json").read_text())) == 2


def test_next_with_nothing_due_starts_nothing(sidecar, tmp_path, capsys):
    """REQ-071 AC8: no job due, no model start."""
    assert autopilot.main(["next", "--root", str(sidecar)], NOW) == 0
    assert capsys.readouterr().out.strip() == "next: nothing started (no job is due)"
    assert not list(tmp_path.glob("agk-*"))


# --- the task texts: the launcher is the supervisor, every job is short ---------------------------


def test_the_cloud_texts_run_the_same_pass_and_short_jobs():
    """REQ-071 AC8: the launcher runs `autopilot.py jobs --claim` as its pass and fires one cloud
    session per `job:` line; the conductor and builder cloud forms end after one job; no text
    waits in the foreground or changes a workflow, the ruleset or a required check."""
    launcher = (RUNTIME / "launcher.txt").read_text(encoding="utf-8")
    assert "python3 scripts/agk/autopilot.py jobs --claim" in launcher
    for kind in ("job: review", "job: build", "job: fix"):
        assert kind in launcher, kind
    builder = (RUNTIME / "builder.txt").read_text(encoding="utf-8")
    assert "in the foreground with a timeout of at most 9 minutes" not in builder
    assert "A cloud scheduled task keeps LIFETIME" not in builder
    conductor_text = (RUNTIME / "conductor.txt").read_text(encoding="utf-8")
    assert "conductor.py watch --since" not in conductor_text
    assert "end" in conductor_text.split("\n\n")[1]
    for text in (launcher, builder, conductor_text):
        assert "never change a workflow" in text.lower() or "change workflows" in text.lower()


def test_the_guide_starts_with_one_command_and_agk_next():
    """REQ-071 AC8: the guide's autopilot block, at most ten lines, names both commands."""
    guide = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    block = guide.split("**With the autopilot.**", 1)[1].split("\n\n", 1)[0]
    assert "agk autopilot on" in block and "agk next" in block
    assert len(block.splitlines()) <= 10
