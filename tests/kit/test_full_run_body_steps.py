"""A full governance run that failed only on the steps that read the body (brief #216, build b).

An edited description starts a partial run of those steps. When the latest full run of the head
failed, and every failed step of it is a step the partial run repeats, editing the body can cure it,
so `full_run.py` lets the partial run decide; any other failed step still fails. The workflow makes
one more GET (`actions/runs/<id>/jobs`) for it. Saved responses; no network.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_full_run import FULL, GOVERNANCE, HEAD, ROOT, SCRIPT, run_of, step_script, text

RUN_ID = 4242
BODY = (
    "PR body file",
    "PR states and open pull requests",
    "check_specs",
    "check_pr_mode",
    "PR body shape",
)


def full(conclusion: str | None, created: str = "2026-10-26T10:00:00Z", rid: object = RUN_ID):
    return {**run_of(FULL, conclusion, created), "id": rid}


def step(name: str, conclusion: str = "success") -> dict:
    return {"name": name, "status": "completed", "conclusion": conclusion}


def jobs_of(*failed: str, others: tuple[str, ...] = ("Lint", "check_adrs")) -> dict:
    steps = [step("Set up job"), *(step(n) for n in others), *(step(n, "failure") for n in failed)]
    return {"total_count": 1, "jobs": [{"name": "governance", "steps": steps}]}


def check(tmp_path: Path, runs: list, jobs: object = None):
    (tmp_path / "runs.json").write_text(json.dumps({"workflow_runs": runs}))
    args = ["--runs", str(tmp_path / "runs.json"), "--head", HEAD]
    if jobs is not None:
        (tmp_path / "jobs.json").write_text(jobs if isinstance(jobs, str) else json.dumps(jobs))
        args += ["--jobs", str(tmp_path / "jobs.json")]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def test_a_red_full_run_without_the_jobs_asks_for_them_by_run_id(tmp_path):
    """Brief #216 build b: exit 4 and the run id, so that the workflow makes one more GET."""
    out = check(tmp_path, [full("failure")])
    assert (out.returncode, out.stdout) == (4, f"jobs {RUN_ID}\n")


@pytest.mark.parametrize("rid", [None, "abc", "12 34", "1; rm -rf x", -5, True, ""])
def test_a_run_id_that_is_not_a_plain_number_is_never_printed(tmp_path, rid):
    """The id comes from a response: a value that is not digits fails, never reaching a shell."""
    out = check(tmp_path, [full("failure", rid=rid)])
    assert out.returncode == 1 and "jobs" not in out.stdout


@pytest.mark.parametrize("failed", [("PR body shape",), ("check_specs",), ("check_pr_mode",), BODY])
def test_a_failure_of_body_steps_only_passes_and_lets_the_partial_run_decide(tmp_path, failed):
    """Brief #216 build b: a body-only failure followed by a fixed body passes."""
    out = check(tmp_path, [full("failure")], jobs_of(*failed))
    assert out.returncode == 0 and out.stdout.startswith("ok full-run"), out.stdout


@pytest.mark.parametrize(
    "failed",
    [
        ("Lint",),
        ("Tests of the checks",),
        ("check_adrs",),
        ("PR body shape", "Lint"),
        ("Secret scan",),
    ],
)
def test_a_failure_of_any_other_step_still_fails(tmp_path, failed):
    """Brief #216 build b: a lint failure followed by an edit fails."""
    out = check(tmp_path, [full("failure")], jobs_of(*failed, others=()))
    assert out.returncode == 1 and out.stdout.startswith("FAIL full-run: ")


@pytest.mark.parametrize(
    "jobs",
    [
        jobs_of(),
        {"jobs": []},
        {"total_count": 0},
        {"jobs": [{"name": "governance"}]},
        {"jobs": [{"name": "governance", "steps": [step("Set up job", "failure")]}]},
        {"jobs": [{"name": "governance", "steps": [step("Checkout", "failure")]}]},
        "not json",
        "[]",
        "",
    ],
)
def test_jobs_that_show_no_failed_body_step_or_cannot_be_read_fail(tmp_path, jobs):
    """Brief #216 build b: unreadable, empty, or an infrastructure step failed: fail."""
    out = check(tmp_path, [full("failure")], jobs)
    assert out.returncode == 1


def test_a_cancelled_step_is_not_a_body_step_and_a_cancelled_body_step_is_not_a_cure(tmp_path):
    """Brief #216 build b: only a failed step of the body steps passes; cancelled ones do not."""
    jobs = {"jobs": [{"name": "governance", "steps": [step("PR body shape", "cancelled")]}]}
    assert check(tmp_path, [full("cancelled")], jobs).returncode == 1


def test_the_jobs_are_ignored_when_the_latest_full_run_succeeded_or_is_running(tmp_path):
    """Brief #216 build b: the earlier outcomes are unchanged."""
    ok = check(tmp_path, [full("success")], jobs_of("Lint"))
    assert (ok.returncode, ok.stdout) == (0, "ok full-run\n")
    running = {**run_of(FULL, None, "2026-10-26T10:00:00Z", status="in_progress"), "id": RUN_ID}
    assert check(tmp_path, [running], jobs_of()).returncode == 3


def test_the_latest_full_run_is_the_one_whose_jobs_are_asked_for(tmp_path):
    """Brief #216 build b: an older red run is not asked for."""
    older = full("failure", "2026-10-26T09:00:00Z", rid=1)
    newer = full("failure", "2026-10-26T11:00:00Z", rid=2)
    assert check(tmp_path, [newer, older]).stdout == "jobs 2\n"


def test_the_message_names_the_rule_and_never_a_step_or_a_value(tmp_path):
    """CLAUDE.md rule 6"""
    out = check(tmp_path, [full("failure")], jobs_of("Lint", others=()))
    assert "Lint" not in out.stdout and HEAD not in out.stdout and str(RUN_ID) not in out.stdout


# --- the body steps are the steps of the workflow that read the body and run on an edit ----------


def steps_of() -> dict[str, str]:
    body = text().split("    steps:\n", 1)[1]
    parts = re.split(r"(?m)^      - (?=name: |uses: )", body)[1:]
    found = {}
    for part in parts:
        name = re.match(r"name: (.+)", part)
        if name:
            found[name.group(1).strip()] = part
    return found


def test_the_body_steps_are_exactly_the_steps_that_read_the_body_and_run_on_an_edit():
    """The constant of the script cannot drift from the workflow."""
    sys.path.insert(0, str(ROOT / "scripts" / "agk"))
    import full_run

    runs_on_edit = {
        name
        for name, part in steps_of().items()
        if "action != 'edited'" not in part.split("run:", 1)[0] and name != "Latest full run"
    }
    reads_body = {
        name
        for name, part in steps_of().items()
        if re.search(r"pr-body\.md|PR_BODY|pull_request\.body", part)
    }
    assert set(full_run.BODY_STEPS) == (runs_on_edit & reads_body)
    assert set(full_run.BODY_STEPS) == set(BODY)


# --- the step of the workflow, run for real with a gh that answers by endpoint -------------------


def run_step(tmp_path: Path, runs: list, jobs: object, fail_jobs: bool = False):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fixtures = tmp_path / "fixtures"  # not the files the step writes (`$TMP/runs.json`)
    fixtures.mkdir()
    (fixtures / "runs.json").write_text(json.dumps({"workflow_runs": runs}))
    (fixtures / "jobs.json").write_text(json.dumps(jobs))
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        f'echo "$*" >> "{tmp_path}/calls"\n'
        'case "$*" in\n'
        + ("  */jobs*) exit 1;;\n" if fail_jobs else f'  */jobs*) cat "{fixtures}/jobs.json";;\n')
        + f'  *) cat "{fixtures}/runs.json";;\n'
        "esac\n"
    )
    sleep = bin_dir / "sleep"
    sleep.write_text("#!/bin/sh\n")
    (bin_dir / "python").symlink_to(sys.executable)
    for tool in (gh, sleep):
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "TMP": str(tmp_path)}
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, a stubbed gh
        ["bash", "-c", step_script()], cwd=ROOT, env=env, capture_output=True, text=True
    )
    calls = (tmp_path / "calls").read_text().splitlines()
    return proc, calls


def test_the_step_makes_one_more_get_for_the_jobs_of_the_red_run_and_passes_on_body_steps(tmp_path):
    """Brief #216 build b: the second GET is `actions/runs/<id>/jobs` of the run it names."""
    proc, calls = run_step(tmp_path, [full("failure")], jobs_of("PR body shape"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(calls) == 2 and f"actions/runs/{RUN_ID}/jobs" in calls[1]
    assert calls[1].startswith("api --method GET") and "acme/widgets" in calls[1]


def test_the_step_fails_when_a_step_other_than_a_body_step_failed(tmp_path):
    """Brief #216 build b: a lint failure followed by an edit fails."""
    proc, calls = run_step(tmp_path, [full("failure")], jobs_of("Lint", others=()))
    assert proc.returncode == 1 and len(calls) == 2


def test_the_step_fails_when_the_jobs_cannot_be_read(tmp_path):
    """Brief #216 build b: an unreadable jobs response fails; nothing else is asked for."""
    proc, calls = run_step(tmp_path, [full("failure")], jobs_of(), fail_jobs=True)
    assert proc.returncode == 1 and len(calls) == 2


def test_the_step_makes_no_second_get_after_a_green_full_run(tmp_path):
    """Brief #216 build b: the jobs are asked for only when the latest full run is red."""
    proc, calls = run_step(tmp_path, [full("success")], jobs_of())
    assert proc.returncode == 0 and len(calls) == 1


def test_the_workflow_still_has_two_gets_at_most_in_the_step_and_stays_read_only():
    """Brief #216 build b: no write permission is added."""
    block = text().split("      - name: Latest full run\n", 1)[1].split("\n      - ", 1)[0]
    assert block.count("gh api --method GET") == 2 and "actions/runs/" in block
    perms = text().split("\npermissions:\n", 1)[1].split("\n\n", 1)[0]
    assert "write" not in perms and GOVERNANCE.exists()
