"""A fresh reviewer gives every gating verdict, in local mode too (brief #1248, ADR-0528).

REQ-046. `[flow] reviewer_slots` (a whole number, 0 by default) puts a reviewer slot at the gate:
`conductor.py review --pr N [--start]` asks a free slot with one `Review: r<k> #<n> <head>` line
and, in local mode (`auto_start` and `launch_adapter` set), starts one fresh reviewer session per
head through the adapter; `conductor.py check-verdict --pr N` then refuses the conductor's own
verdict while that reviewer has the head, and accepts a `(conductor fallback)` verdict only after
`review_minutes` with no reviewer verdict. The review guard lets the slot save its bundle in its
scratch folder. The adapter is a test double that records its call; the `gh` stub serves saved
copies of the GitHub responses: no terminal, no network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from test_session import REPO, SCRIPTS, SHA, Stub, comment, iso

ROOT = SCRIPTS.parents[1]
GUARD = ROOT / ".claude" / "hooks" / "architect_guard.py"
GIB = 1024**3
PR = f"repos/{REPO}/pulls/7"
PR_COMMENTS = f"repos/{REPO}/issues/7/comments"
ISSUES = f"repos/{REPO}/issues"
CONDUCTOR = f"repos/{REPO}/issues/204/comments"
OTHER = "b" * 40
ADAPTER = """import json, os, sys
keys = ("AGK_SESSION", "AGK_ROLE", "AGK_AGENT", "AGK_TIER", "AGK_PR", "AGK_SHA", "AGK_BRIEF")
with open(sys.argv[1], "a", encoding="utf-8") as log:
    env = {k: os.environ.get(k) for k in keys}
    log.write(json.dumps({**env, "prompt": sys.stdin.read()}) + "\\n")
sys.exit(int(os.environ.get("ADAPTER_EXIT", "0")))
"""
MARKERS = "agent: architect-review\ntier: strongest\nsession: r1\n"


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


def toml_of(adapter: str, slots: int | None = 1, extra: str = "") -> str:
    count = "" if slots is None else f"reviewer_slots = {slots}\n"
    return (
        'default_branch = "main"\nexperimental_reviewer = true\n[flow]\nauto_start = true\n'
        f"launch_adapter = {json.dumps(adapter)}\n{count}{extra}"
    )


@pytest.fixture
def world(repo, stub, tmp_path, monkeypatch):
    """A project in local mode with one reviewer slot: `auto_start` on, an adapter double, the same
    settings on `origin/main`, one open `agk-conductor` issue; `gh` is the stub, memory plenty."""
    import common

    double = tmp_path / "adapter.py"
    double.write_text(ADAPTER, encoding="utf-8")
    log = tmp_path / "adapter.log"
    adapter = f"{sys.executable} {double} {log}"
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    monkeypatch.setenv("PATH", f"{stub.bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_STUB_DIR", str(stub.dir))
    monkeypatch.delenv("ADAPTER_EXIT", raising=False)
    monkeypatch.setattr(common, "available_memory", lambda: 16 * GIB)
    stub.serve(PR, {"number": 7, "state": "open", "head": {"sha": SHA}, "draft": False})
    stub.serve(PR_COMMENTS, [comment(1, "builder", f"Report: {SHA[:7]} ready for review")])
    stub.serve(ISSUES, [{"number": 204, "title": "Assign", "labels": [{"name": "agk-conductor"}]}])
    stub.serve(CONDUCTOR, [])
    world = {"repo": repo, "stub": stub, "log": log, "adapter": adapter, "tmp": tmp_path}
    settle(world, toml_of(adapter))
    return world


def settle(world, toml: str) -> None:
    """Commit agk.toml and make `origin/main` the same commit (settings read in both places)."""
    world["repo"].commit(
        {
            "config/reviewers.yaml": "version: 1\nverdict_authors: [boss]\nspec_approvers: [o]\n",
            "agk.toml": toml,
        }
    )
    world["repo"].git("update-ref", "refs/remotes/origin/main", "HEAD")


def conductor(world, capsys, *args: str) -> tuple[int, str, str]:
    import conductor as module

    code = module.main(list(args), root=world["repo"].root)
    out = capsys.readouterr()
    return code, out.out, out.err


def starts(world) -> list[dict]:
    log = world["log"]
    if not log.exists():
        return []
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]


def writes(stub) -> list[list]:
    return [c for c in stub.calls() if c[0] != "GET"]


def review_line(minutes: int, slot: str = "r1", pr: int = 7, sha: str = SHA, cid: int = 30):
    when = iso(timedelta(minutes=-minutes))
    return comment(cid, "boss", f"Review: {slot} #{pr} {sha}", when)


def verdict_file(world, text: str) -> str:
    path = world["tmp"] / "v.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


def check(world, capsys, text: str) -> tuple[int, str]:
    path = verdict_file(world, text)
    code, out, err = conductor(world, capsys, "check-verdict", path, "--pr", "7")
    return code, out + err


# --- answer 3: local mode starts one fresh reviewer per ready head through the adapter -------


def test_a_ready_head_starts_one_reviewer_through_the_adapter(world, capsys):
    """REQ-046: brief #1248 answers 3 and 5 (one start, the prompt names only slot, pr and head)."""
    code, out, err = conductor(world, capsys, "review", "--pr", "7", "--start")
    assert code == 0, err
    got = starts(world)
    assert len(got) == 1
    run = got[0]
    assert run["AGK_SESSION"] == "r1" and run["AGK_ROLE"] == "reviewer"
    assert run["AGK_AGENT"] == "architect-review" and run["AGK_TIER"] == "strongest"
    assert run["AGK_PR"] == "7" and run["AGK_SHA"] == SHA and run["AGK_BRIEF"] is None
    assert "r1" in run["prompt"] and "#7" in run["prompt"] and SHA in run["prompt"]
    assert "review_bundle.py --pr 7 --sha " + SHA in run["prompt"]
    assert "slot --release r1" in run["prompt"]
    assert "architect-review" in run["prompt"]
    assert f"review: started r1 for #7 {SHA[:12]}" in out
    posted = writes(world["stub"])
    assert [c[1] for c in posted] == [CONDUCTOR]  # the one `Review:` line, and no verdict
    assert f"body=Review: r1 #7 {SHA}" in posted[0][2]


def test_while_the_reviewer_has_the_head_the_conductor_gives_no_verdict(world, capsys):
    """REQ-046: brief #1248 answers 1, 3 and 5 (the conductor's verdict is refused meanwhile)."""
    world["stub"].serve(CONDUCTOR, [review_line(3)])
    code, out, _ = conductor(world, capsys, "review", "--pr", "7", "--start")
    assert code == 0
    assert starts(world) == [] and writes(world["stub"]) == []  # never a second start
    assert "review: #7 " in out and "with r1" in out and "no verdict" in out
    for text in (
        f"Verdict: cleared {SHA} (conductor fallback)\n\nRead: all\n",
        f"Verdict: cleared {SHA}\n\nRead: all\n",
    ):
        code, said = check(world, capsys, text)
        assert code == 1, text
        assert "reviewer_slots" in said or "review_minutes" in said


def test_no_reviewer_answer_within_review_minutes_allows_one_fallback(world, capsys):
    """REQ-046: brief #1248 answers 1 and 5 (`(conductor fallback)` only after review_minutes)."""
    world["stub"].serve(CONDUCTOR, [review_line(16)])
    code, out, _ = conductor(world, capsys, "review", "--pr", "7")
    assert code == 0
    assert "fallback" in out and "review_minutes" in out
    code, said = check(world, capsys, f"Verdict: cleared {SHA} (conductor fallback)\n\nRead: all\n")
    assert code == 0, said
    code, said = check(world, capsys, f"Verdict: cleared {SHA}\n\nRead: all\n")
    assert code == 1  # past the time, the conductor's verdict still says it is the fallback
    assert starts(world) == []


def test_the_flow_review_minutes_sets_the_wait(world, capsys):
    """REQ-046: brief #1248 answer 1 (`[flow] review_minutes`, read before `[capacity]`)."""
    extra = "review_minutes = 30\n[capacity]\nreview_minutes = 5\n"
    settle(world, toml_of(world["adapter"], extra=extra))
    world["stub"].serve(CONDUCTOR, [review_line(16)])
    code, _ = check(world, capsys, f"Verdict: cleared {SHA} (conductor fallback)\n")
    assert code == 1


def test_the_reviewer_verdict_with_its_marker_lines_is_accepted(world, capsys):
    """REQ-046: brief #1248 answer 4 (the slot's `agent:`, `tier:` and `session:` lines)."""
    world["stub"].serve(CONDUCTOR, [review_line(3)])
    code, said = check(world, capsys, f"Verdict: cleared {SHA}\n{MARKERS}\nRead: bundle\n")
    assert code == 0, said
    wrong = MARKERS.replace("session: r1", "session: r2")  # r2 is not one of the 1 slots
    code, _ = check(world, capsys, f"Verdict: cleared {SHA}\n{wrong}\nRead: bundle\n")
    assert code == 1


def test_a_fallback_with_no_review_line_is_refused(world, capsys):
    """REQ-046: brief #1248 answer 1 (the reviewer is asked first)."""
    code, said = check(world, capsys, f"Verdict: cleared {SHA} (conductor fallback)\n")
    assert code == 1 and "reviewer_slots" in said


def test_a_busy_slot_starts_nothing_more(world, capsys):
    """REQ-046: brief #1248 answer 3 (one reviewer per slot; another head waits)."""
    world["stub"].serve(CONDUCTOR, [review_line(2, pr=8, sha=OTHER)])
    world["stub"].serve(f"repos/{REPO}/issues/8/comments", [])
    code, out, _ = conductor(world, capsys, "review", "--pr", "7", "--start")
    assert code == 0
    assert starts(world) == [] and writes(world["stub"]) == []
    assert "no reviewer slot is free" in out


def test_the_memory_floor_applies_to_a_reviewer_start(world, capsys, monkeypatch):
    """REQ-046: brief #1248 answer 3 (`[flow] min_free_memory_mb`, as for builders)."""
    import launch

    settle(world, toml_of(world["adapter"], extra="min_free_memory_mb = 4096\n"))
    monkeypatch.setattr(launch, "available_memory", lambda: 1 * GIB)
    code, _, err = conductor(world, capsys, "review", "--pr", "7", "--start")
    assert code == 1
    assert "min_free_memory_mb" in err
    assert starts(world) == [] and writes(world["stub"]) == []


def test_a_failing_adapter_is_reported_once(world, capsys, monkeypatch):
    """REQ-046: brief #1248 answer 3 (the `Review:` line stays; the fallback follows its time)."""
    monkeypatch.setenv("ADAPTER_EXIT", "3")
    code, _, err = conductor(world, capsys, "review", "--pr", "7", "--start")
    assert code == 1
    assert "the adapter failed for r1" in err
    assert len(starts(world)) == 1


def test_without_the_adapter_the_start_is_refused_and_the_ask_printed(world, capsys):
    """REQ-046: brief #1248 answer 3 (local mode needs `auto_start` and `launch_adapter`)."""
    settle(world, toml_of(world["adapter"]).replace("auto_start = true", "auto_start = false"))
    code, out, _ = conductor(world, capsys, "review", "--pr", "7", "--start")
    assert code == 1
    assert "auto_start" in out and "launch_adapter" in out
    assert starts(world) == [] and writes(world["stub"]) == []
    code, out, _ = conductor(world, capsys, "review", "--pr", "7")
    assert code == 0
    assert f"review: ask Review: r1 #7 {SHA}" in out
    assert writes(world["stub"]) == []


def test_a_head_with_its_verdict_needs_no_review(world, capsys):
    """REQ-046: brief #1248 answer 3."""
    verdict = comment(9, "boss", f"Verdict: cleared {SHA}\n{MARKERS}")
    world["stub"].serve(PR_COMMENTS, [verdict])
    code, out, _ = conductor(world, capsys, "review", "--pr", "7", "--start")
    assert code == 0 and "has its verdict" in out
    assert starts(world) == []


# --- answer 1: `reviewer_slots = 0` (the default) behaves as today ---------------------------


@pytest.mark.parametrize("slots", [None, 0])
def test_no_reviewer_slots_keeps_todays_behaviour(world, capsys, slots):
    """REQ-046: brief #1248 answers 1 and 5 (no start, no ask, the conductor's verdict as today)."""
    settle(world, toml_of(world["adapter"], slots=slots))
    code, out, _ = conductor(world, capsys, "review", "--pr", "7", "--start")
    assert code == 0
    assert "review: off" in out and "reviewer_slots" in out
    assert starts(world) == [] and writes(world["stub"]) == []
    code, said = check(world, capsys, f"Verdict: cleared {SHA}\n\nRead: all\n")
    assert code == 0, said


@pytest.mark.parametrize("value", ["-1", '"two"', "true"])
def test_a_reviewer_slots_of_the_wrong_kind_is_refused_by_name(world, capsys, value):
    """REQ-046: brief #1248 answer 1 (the setting is named, never the value)."""
    settle(world, toml_of(world["adapter"], slots=None, extra=f"reviewer_slots = {value}\n"))
    code, _, err = conductor(world, capsys, "review", "--pr", "7")
    assert code == 1
    assert "reviewer_slots" in err and value not in err.replace("reviewer_slots", "")


# --- answer 1: session.py reads the count -----------------------------------------------------


def session_run(world, *args: str):
    env = {k: v for k, v in os.environ.items() if k not in ("CI", "GITHUB_BASE_REF", "AGK_BASE")}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "session.py"), *args],
        cwd=world["repo"].root,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_session_runs_the_reviewer_slots_the_count_names(world):
    """REQ-046: brief #1248 answer 1 (a reviewer slot needs no builder pool once counted)."""
    proc = session_run(world, "slot", "--release", "r1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "slot: r1 free" in proc.stdout
    proc = session_run(world, "slot", "--next", "r2")
    assert proc.returncode != 0
    assert "reviewer_slots" in proc.stdout + proc.stderr


def test_session_without_a_count_keeps_the_reviewer_slots_behind_the_pool(world):
    """REQ-046: brief #1248 answer 1 (`reviewer_slots = 0`: as today, `builder_start` decides)."""
    settle(world, toml_of(world["adapter"], slots=None))
    proc = session_run(world, "slot", "--next", "r1")
    assert proc.returncode == 3 and "slot: off" in proc.stdout


# --- answer 1 and the co-owner's note: doctor names both settings ----------------------------


def test_doctor_fails_reviewer_slots_without_the_reviewer_agent(world):
    """REQ-046: brief #1248 answer 1 (the note of 2026-11-14: `experimental_reviewer` too)."""
    import doctor

    root = world["repo"].root
    assert doctor.reviewer_slots_result(root).status == "ok"
    settle(world, toml_of(world["adapter"]).replace("experimental_reviewer = true", ""))
    found = doctor.reviewer_slots_result(root)
    assert found.status == "fail"
    assert "reviewer_slots" in found.message and "experimental_reviewer" in found.message
    settle(world, toml_of(world["adapter"], slots=0).replace("experimental_reviewer = true", ""))
    assert doctor.reviewer_slots_result(root).status == "ok"
    assert doctor.CHECKS["reviewer-slots"][0] == "error"


# --- answer 2: the review guard lets the slot save its bundle in its scratch folder ----------


class Guard:
    def __init__(self, root: Path) -> None:
        self.root = root / "work"
        self.tmp = root / "tmp"
        self.root.mkdir()
        self.tmp.mkdir()
        self.scratch = self.tmp / "agk-review-r1"
        self.scratch.mkdir()

    def bash(self, command: str, *flags: str) -> bool:
        """Whether the guard allows COMMAND."""
        return self.decide({"tool_name": "Bash", "tool_input": {"command": command}}, *flags)

    def write(self, path: object) -> bool:
        return self.decide({"tool_name": "Write", "tool_input": {"file_path": str(path)}})

    def decide(self, payload: dict, *flags: str) -> bool:
        proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
            [sys.executable, str(GUARD), *(flags or ("--review",))],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin",
                "CLAUDE_PROJECT_DIR": str(self.root),
                "TMPDIR": str(self.tmp),
            },
        )
        assert proc.returncode == 0
        return proc.stdout == ""


@pytest.fixture
def guard(tmp_path):
    return Guard(tmp_path)


BUNDLE = f"python3 scripts/agk/review_bundle.py --pr 7 --sha {SHA}"


def test_the_guard_allows_saving_the_bundle_in_the_scratch_folder(guard):
    """REQ-046: brief #1248 answers 2 and 5 (Q-1013-3: the bundle and verdict files)."""
    assert guard.bash(f"{BUNDLE} > {guard.scratch}/bundle.md")
    assert guard.bash(f"{BUNDLE} --base origin/main > {guard.scratch}/bundle.md")
    assert guard.bash(f"{BUNDLE} >{guard.scratch}/b.md")
    assert guard.write(guard.scratch / "v.md")


def test_the_guard_refuses_every_other_write_and_redirect(guard):
    """REQ-046: brief #1248 answers 2 and 5 (the checkout, another folder, another form)."""
    (guard.tmp / "other").mkdir()
    for command in (
        f"{BUNDLE} > {guard.root}/bundle.md",
        f"{BUNDLE} > bundle.md",
        f"{BUNDLE} > {guard.tmp}/other/bundle.md",
        f"{BUNDLE} > {guard.scratch}",
        f"{BUNDLE} >> {guard.scratch}/bundle.md",
        f"{BUNDLE} 2> {guard.scratch}/bundle.md",
        f"{BUNDLE} > {guard.scratch}/a.md > {guard.scratch}/b.md",
        f"{BUNDLE} > {guard.scratch}/a.md; date",
        f"{BUNDLE} > {guard.scratch}/../other/a.md",
        f"{BUNDLE} --write > {guard.scratch}/a.md",
        f"python3 scripts/agk/review_bundle.py --pr 7 --sha abc > {guard.scratch}/a.md",
        f"python3 scripts/agk/review_context.py > {guard.scratch}/a.md",
        f"git log > {guard.scratch}/a.md",
        f"{BUNDLE} > '{guard.scratch}/a.md'",
    ):
        assert not guard.bash(command), command
    assert not guard.write(guard.root / "v.md")
    assert not guard.bash(f"{BUNDLE} > {guard.scratch}/bundle.md", "--other")  # not the reviewer


# --- the conductor's guard runs the new routine ------------------------------------------------


def test_the_conductor_guard_allows_the_review_routine():
    """REQ-046: brief #1248 answer 3 (`review --pr <n>` reads; `--start` needs the adapter)."""
    sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
    import conductor_guard

    assert conductor_guard.routine_form(["review", "--pr", "7"])
    assert conductor_guard.routine_form(["review", "--pr", "7", "--start"])
    assert not conductor_guard.routine_form(["review", "--pr", "x"])
    assert not conductor_guard.routine_form(["review", "--pr", "7", "--apply"])


# --- answer 4: the checklist names the setting beside the slots alive -------------------------


def test_the_checklist_names_the_reviewer_slots_setting():
    """REQ-046: brief #1248 answer 4 (point 2 shows the count beside the slots alive)."""
    import checklist

    class View:
        comments = []
        authors = {"boss"}
        conductor_issues = {204}
        flow = {"reviewer_slots": 2}
        end = __import__("datetime").datetime(2026, 11, 14, tzinfo=__import__("datetime").UTC)

    assert checklist.slots_alive(View()) == "reviewer slots alive 0 of 2 (reviewer_slots)"
    View.flow = {}
    assert checklist.slots_alive(View()) == "reviewer slots alive 0"
