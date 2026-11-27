"""Every builder a supervisor or the conductor starts is told it is one short job (brief #2057).

REQ-071 AC2: *every AI session is a short job that ends* (SPEC-0064 rules 2, 4 and 9, ADR-0855).
`launch.start_with` adds the build or fix job line to every start it makes, once; `launch.py prompts
--plan F --job` prints the same text, first a `Job:` line, for a starter with no adapter (a cloud
runtime); the conductor guard allows that one extra word; and the one-hour restart gap holds a
short job only after a counted failure. An adapter double records its stdin and environment, the
`gh` stub serves saved answers; invented names, no network, no model.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_autopilot_build_jobs import fix_list
from test_conductor_guard_launch import allowed, denied, plan_file, project, run_hook, tmp  # noqa: F401
from test_conductor_watchdog import starts, stub, world  # noqa: F401
from test_session import comment, iso
from test_watchdog_builders import builder_line, builders, pr_comments, watchdog  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
AGK = ROOT / "scripts" / "agk"
sys.path.insert(0, str(AGK))

import conductor  # noqa: E402
import launch  # noqa: E402

SCRIPT = AGK / "launch.py"
RECORDER = (
    "import json, os, sys\n"
    "with open(os.environ['ADAPTER_LOG'], 'a') as f:\n"
    "    f.write(json.dumps({'kind': os.environ.get('AGK_JOB_KIND'),\n"
    "                        'item': os.environ.get('AGK_ITEM'), 'prompt': sys.stdin.read()}) + '\\n')\n"
)


@pytest.fixture
def recorder(tmp_path, monkeypatch) -> tuple[str, Path]:
    script = tmp_path / "adapter.py"
    script.write_text(RECORDER, encoding="utf-8")
    log = tmp_path / "calls.log"
    monkeypatch.setenv("ADAPTER_LOG", str(log))
    return f"{sys.executable} {script}", log


def calls(log: Path) -> list[dict]:
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


# --- answer 1: every start through the adapter says it --------------------------------------


def test_a_build_start_through_the_adapter_carries_the_build_job_line_once(tmp_path, recorder):
    """REQ-071 AC2: brief #2057 answer 1 (the build start says one short job)."""
    command, log = recorder
    assert launch.start_with(command, [("cb1", 1, None)], root=tmp_path) == 0
    (got,) = calls(log)
    assert got["kind"] == "build" and got["item"] == "#1"
    assert got["prompt"].count(launch.BUILD_JOB) == 1
    assert "one short job" in got["prompt"] and launch.FIX_JOB not in got["prompt"]


@pytest.mark.parametrize("already", [False, True])
def test_a_fix_start_carries_the_fix_job_line_once(tmp_path, recorder, already):
    """REQ-071 AC2: brief #2057 answers 1 and 5 (a prompt that already holds it gets it once)."""
    command, log = recorder
    prompt = launch.resume_for("cb1", 1, None, 70, None) + (launch.FIX_JOB if already else "")
    launch.start_with(command, [("cb1", 1, None)], [prompt], root=tmp_path, jobs=[("fix", 70)])
    (got,) = calls(log)
    assert got["kind"] == "fix" and got["item"] == "#70"
    assert got["prompt"].count(launch.FIX_JOB) == 1 and launch.BUILD_JOB not in got["prompt"]


def test_a_note_after_the_job_line_does_not_repeat_it(tmp_path, recorder):
    """REQ-071 AC2: brief #2057 answer 4 (`PERSONAL_NOTE` follows the job line, once)."""
    import autopilot

    command, log = recorder
    prompt = launch.prompt_for("cb1", 1) + launch.BUILD_JOB + autopilot.PERSONAL_NOTE
    launch.start_with(command, [("cb1", 1, None)], [prompt], root=tmp_path, jobs=[("build", 1)])
    text = calls(log)[0]["prompt"]
    assert text.count(launch.BUILD_JOB) == 1 and text.endswith(autopilot.PERSONAL_NOTE)


def test_a_printed_prompt_a_person_pastes_keeps_watch():
    """REQ-071 AC2: brief #2057 answer 1 (`prompt_for` and `resume_for` alone are unchanged)."""
    assert "one short job" not in launch.prompt_for("cb1", 1)
    assert "one short job" not in launch.resume_for("cb1", 1, None, 70, None)


# --- answer 2: a start with no adapter takes the --job text ---------------------------------


def run(tmp_path: Path, doc: dict, *args: str):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "prompts", "--plan", str(path), *args],
        capture_output=True, text=True, env=env, timeout=60, cwd=tmp_path,
    )  # fmt: skip


START = {"start": [{"session": "cb7", "brief": 7}], "waits": [], "skipped": []}
RUNNING = {
    "start": [],
    "running": [{"session": "cb5", "brief": 5, "pull_request": 41}, {"session": "cb6", "brief": 6}],
    "waits": [],
    "skipped": [],
}


def test_the_job_option_prints_the_job_line_and_the_build_text(tmp_path):
    """REQ-071 AC2: brief #2057 answer 2 (`prompts --plan F --job`)."""
    out = run(tmp_path, START, "--job")
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("Job: build #7 (AGK_JOB_KIND build, AGK_ITEM #7)\n")
    assert out.stdout.count(launch.BUILD_JOB) == 1 and "--brief 7" in out.stdout


def test_the_job_option_of_resume_names_each_kind(tmp_path):
    """REQ-071 AC2: brief #2057 answer 2 (`prompts --resume --plan F --job`)."""
    out = run(tmp_path, RUNNING, "--resume", "--job")
    assert out.returncode == 0, out.stderr
    first, second = [p for p in out.stdout.split(launch.SEPARATOR + "\n") if p.strip()]
    assert first.startswith("Job: fix #41 (AGK_JOB_KIND fix, AGK_ITEM #41)\n")
    assert first.count(launch.FIX_JOB) == 1 and "resume --pr 41" in first
    assert second.startswith("Job: build #6 (AGK_JOB_KIND build, AGK_ITEM #6)\n")
    assert second.count(launch.BUILD_JOB) == 1


@pytest.mark.parametrize("doc, extra", [(START, []), (RUNNING, ["--resume"])])
def test_without_the_job_option_neither_line_is_printed(tmp_path, doc, extra):
    """REQ-071 AC2: brief #2057 answers 2 and 4 (`auto_start` off: the person's text)."""
    out = run(tmp_path, doc, *extra)
    assert out.returncode == 0, out.stderr
    assert "Job:" not in out.stdout and "one short job" not in out.stdout


@pytest.mark.parametrize(
    "extra", [["--job", "--adapter", "x"], ["--adapter", "x", "--job"], ["--job", "--job"]]
)
def test_the_job_option_with_an_adapter_is_refused_naming_it(tmp_path, extra):
    """REQ-071 AC2: brief #2057 answer 4 (an adapter start is always a job)."""
    out = run(tmp_path, START, *extra)
    assert out.returncode == 2 and "--job" in out.stderr and out.stdout == ""


# --- answer 2: the conductor guard allows the one extra word ---------------------------------


def test_the_guard_allows_the_job_text_of_a_scratch_plan(project, tmp):  # noqa: F811
    """REQ-071 AC2: brief #2057 answer 2 (`prompts --plan <scratch> --job`)."""
    plan = plan_file(tmp)
    assert allowed(run_hook(f"python3 scripts/agk/launch.py prompts --plan {plan} --job", project, tmp))


@pytest.mark.parametrize("extra", ["--jobs", "--job --job", "--job x", "--resume --job", "-j"])
def test_the_guard_refuses_any_other_extra_word(project, tmp, extra):  # noqa: F811
    """REQ-071 AC2: brief #2057 answer 2 (nothing else after the scratch plan)."""
    plan = plan_file(tmp)
    command = f"python3 scripts/agk/launch.py prompts --plan {plan} {extra}"
    assert denied(run_hook(command, project, tmp))


# --- answer 3: the hour only after a failed or empty job -------------------------------------


def restarted_ago(builders, minutes: int) -> None:  # noqa: F811
    root = builders["repo"].root
    memo = conductor.builder_memo(root)
    stamp = datetime.now(UTC) - timedelta(minutes=minutes)
    memo["restarts"][builders["name"]] = conductor.stamp_of(stamp)
    conductor.keep_builder_memo(root, memo)


def test_a_second_fix_job_starts_28_minutes_after_a_first_with_progress(builders, capsys):  # noqa: F811
    """REQ-071 AC2: brief #2057 answer 3 (#2037's second fix list, in the pass it appears)."""
    builders["table"].clear()
    name = builders["name"]
    fix_list(builders)
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {name} #7 ended -> restarted"
    restarted_ago(builders, 28)
    done = comment(5, "builder", "Report: aaaaaaa fix list applied", iso(timedelta(minutes=-20)))
    again = comment(6, "boss", "Verdict: fix list aaaaaaa", iso(timedelta(minutes=-1)))
    fix_list(builders, 60, done, again)
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {name} #7 ended -> restarted"
    got = starts(builders)
    assert len(got) == 2 and got[1]["prompt"].count(launch.FIX_JOB) == 1


def test_a_first_failure_within_the_hour_is_held(builders, capsys):  # noqa: F811
    """REQ-071 AC2: brief #2057 answer 3 (a job with no progress waits the hour)."""
    builders["table"].clear()
    name = builders["name"]
    fix_list(builders)
    watchdog(builders, capsys)
    restarted_ago(builders, 28)
    _, out = watchdog(builders, capsys)
    assert builder_line(out) == f"watchdog: builder {name} #7 ended -> held (restarted within the hour)"
    assert len(starts(builders)) == 1


@pytest.mark.parametrize(
    "short, job, held",
    [
        (True, {"fails": 0}, False),  # a job with progress: the next starts on its event
        (True, {"fails": 1}, True),  # a counted failure keeps the hour
        (True, None, True),  # an older builder with no job record keeps the hour
        (False, {"fails": 0}, True),  # an idle builder or one with no pull request keeps it
        (False, None, True),
    ],
)
def test_the_gap_holds_only_after_a_counted_failure(short, job, held):
    """REQ-071 AC2: brief #2057 answers 3 and 5 (the gap, read in one place)."""
    now = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
    assert conductor.gap_holds(now - timedelta(minutes=28), now, short, job) is held
    assert conductor.gap_holds(now - timedelta(minutes=61), now, short, job) is False
    assert conductor.gap_holds(None, now, short, job) is False


# --- answer 7: the class stays closed ---------------------------------------------------------


def functions_naming(name: str) -> set[str]:
    """`<module>.<function>` of every function in scripts/agk/ whose body names NAME."""
    found = set()
    for path in sorted(AGK.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) or node.name == name:
                continue
            names = {getattr(x, "attr", None) or getattr(x, "id", None) for x in ast.walk(node)}
            if name in names:
                found.add(f"{path.stem}.{node.name}")
    return found


def test_every_caller_of_start_with_is_a_known_start_through_it():
    """REQ-071 AC2: brief #2057 answer 7 (each start reaches the job line inside start_with)."""
    assert functions_naming("start_with") == {
        "launch.main",
        "launch.resume_main",
        "conductor.watch_builders",
        "autopilot.next_command",
    }
    source = ast.get_source_segment(SCRIPT.read_text(encoding="utf-8"), function("start_with"))
    assert "with_job(" in source


def function(name: str) -> ast.FunctionDef:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


def test_the_restart_gap_is_read_only_by_gap_holds():
    """REQ-071 AC2: brief #2057 answer 7 (no second reader of the hour)."""
    assert functions_naming("RESTART_GAP") == {"conductor.gap_holds"}
