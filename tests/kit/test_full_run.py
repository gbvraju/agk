"""An edited description cannot turn a failed governance green (brief #216, the verdict on 460dab3).

The required check reads the latest `governance` run on the head. A partial run for an `edited`
description, green on the body steps alone, would replace a failed full run of the same commit. So
its first step reads the latest completed full run on the head (the run name `governance full`, one
GET of the workflow runs) and `full_run.py` fails the job unless that run succeeded; an unreadable
or missing run fails too, and the next push re-runs in full. Saved responses; no network.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "full_run.py"
HEAD = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
OTHER = "0123456789abcdef0123456789abcdef01234567"


def run_of(title: str, conclusion: str | None, created: str, head: str = HEAD, status="completed"):
    return {
        "display_title": title,
        "head_sha": head,
        "status": status,
        "conclusion": conclusion,
        "created_at": created,
        "event": "pull_request",
    }


def check(tmp_path: Path, runs, *extra: str):
    path = tmp_path / "runs.json"
    path.write_text(runs if isinstance(runs, str) else json.dumps({"workflow_runs": runs}))
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--runs", str(path), "--head", HEAD, *extra],
        capture_output=True,
        text=True,
    )


FULL = "governance full"
PARTIAL = "governance edited"


def test_an_edited_description_after_a_green_full_run_passes(tmp_path):
    """Verdict on 460dab3, item 2: edited after a green full run (passes on the body steps)."""
    out = check(tmp_path, [run_of(FULL, "success", "2026-10-25T10:00:00Z")])
    assert (out.returncode, out.stdout) == (0, "ok full-run\n")


def test_an_edited_description_after_a_red_full_run_fails(tmp_path):
    """Verdict on 460dab3, item 2: edited after a red full run."""
    out = check(tmp_path, [run_of(FULL, "failure", "2026-10-25T10:00:00Z")])
    assert out.returncode == 1 and out.stdout.startswith("FAIL full-run: ")


def test_an_edited_description_with_no_full_run_fails(tmp_path):
    """Verdict on 460dab3, item 2: no full run yet (or only partial ones)."""
    assert check(tmp_path, []).returncode == 1
    only_partial = [run_of(PARTIAL, "success", "2026-10-25T10:00:00Z")]
    assert check(tmp_path, only_partial).returncode == 1


def test_the_latest_completed_full_run_decides(tmp_path):
    """Verdict on 460dab3, item 2: a red run that a later green run replaced does not count."""
    runs = [
        run_of(FULL, "failure", "2026-10-25T10:00:00Z"),
        run_of(FULL, "success", "2026-10-25T11:00:00Z"),
    ]
    assert check(tmp_path, runs).returncode == 0
    runs = [
        run_of(FULL, "success", "2026-10-25T10:00:00Z"),
        run_of(FULL, "failure", "2026-10-25T11:00:00Z"),
    ]
    assert check(tmp_path, runs).returncode == 1


def test_a_partial_run_never_stands_for_a_full_one(tmp_path):
    """Verdict on 460dab3, item 2: a green partial run after a red full run still fails."""
    runs = [
        run_of(FULL, "failure", "2026-10-25T10:00:00Z"),
        run_of(PARTIAL, "success", "2026-10-25T11:00:00Z"),
    ]
    assert check(tmp_path, runs).returncode == 1


def test_a_full_run_on_another_head_does_not_count(tmp_path):
    """Verdict on 460dab3, item 2: only a run of this head."""
    other = run_of(FULL, "success", "2026-10-25T11:00:00Z", head=OTHER)
    assert check(tmp_path, [other]).returncode == 1


@pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "pending", "requested"])
def test_a_latest_full_run_that_is_not_completed_is_a_wait_not_a_failure(tmp_path, status):
    """Verdict on 5aaaf17: the description is often edited while CI runs; the partial run waits."""
    running = run_of(FULL, None, "2026-10-25T11:00:00Z", status=status)
    older_green = run_of(FULL, "success", "2026-10-25T10:00:00Z")
    out = check(tmp_path, [older_green, running])
    assert out.returncode == 3, out.stdout
    assert out.stdout.startswith("waiting") and HEAD not in out.stdout


def test_a_running_full_run_older_than_a_completed_one_does_not_make_it_wait(tmp_path):
    """Verdict on 5aaaf17: the latest full run decides, as before."""
    stale = run_of(FULL, None, "2026-10-25T09:00:00Z", status="in_progress")
    done = run_of(FULL, "success", "2026-10-25T10:00:00Z")
    assert check(tmp_path, [stale, done]).returncode == 0


def test_a_running_partial_run_is_not_a_wait(tmp_path):
    """Verdict on 5aaaf17: only a full run is waited for (the partial run is this very job)."""
    mine = run_of(PARTIAL, None, "2026-10-25T11:00:00Z", status="in_progress")
    assert check(tmp_path, [mine]).returncode == 1


@pytest.mark.parametrize("text", ["", "not json", "[]", '{"workflow_runs": 3}', "{}"])
def test_an_unreadable_response_fails(tmp_path, text):
    """Verdict on 460dab3, item 2: unreadable fails; the next push re-runs in full."""
    assert check(tmp_path, text).returncode == 1


def test_the_message_names_the_rule_and_never_a_value(tmp_path):
    """CLAUDE.md rule 6: no sha, no title in a refusal."""
    out = check(tmp_path, [run_of(FULL, "failure", "2026-10-25T10:00:00Z")])
    assert HEAD not in out.stdout and "failure" not in out.stdout


def test_usage():
    """The script needs both options."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT)], capture_output=True, text=True
    )
    assert proc.returncode == 2


# --- the workflow -------------------------------------------------------------------------------

GOVERNANCE = ROOT / ".github" / "workflows" / "governance.yml"


def text() -> str:
    return GOVERNANCE.read_text(encoding="utf-8")


def test_the_run_names_tell_a_full_run_from_a_partial_one():
    """Verdict on 460dab3, item 2: `run-name` is what the one GET filters on."""
    match = re.search(r"^run-name: (.+)$", text(), flags=re.M)
    assert match
    assert "'edited'" in match.group(1) and "'full'" in match.group(1)
    assert match.group(1).startswith("governance ")


def test_an_edited_run_starts_by_reading_the_latest_full_run_with_one_get():
    """Verdict on 460dab3, item 2: before the body steps, only on `edited`, one GET, the script."""
    body = text().split("    steps:\n", 1)[1]
    names = re.findall(r"(?m)^      - name: (.+)$", body)
    assert names.index("Latest full run") < names.index("PR body file")
    block = body.split("      - name: Latest full run\n", 1)[1].split("\n      - ", 1)[0]
    assert "github.event.action == 'edited'" in block
    assert block.count("gh api --method GET") == 2  # the runs, and the jobs of a red run (build b)
    assert "actions/runs" in block and "head_sha=${{ github.event.pull_request.head.sha }}" in block
    assert "scripts/agk/full_run.py" in block


def test_the_job_can_read_the_workflow_runs_and_is_still_read_only():
    """Verdict on 460dab3, item 2: `actions: read`, no write permission."""
    perms = text().split("\npermissions:\n", 1)[1].split("\n\n", 1)[0]
    held = dict(re.findall(r"^\s{2}([a-z-]+): (read|write)$", perms, flags=re.M))
    assert held.get("actions") == "read"
    assert "write" not in held.values()


def test_the_script_is_installed_and_reads_a_file_only():
    """Verdict on 460dab3, item 2: no network in the script (the GET is in the workflow)."""
    manifest = json.loads((ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/full_run.py" in manifest["verbatim"]
    source = SCRIPT.read_text(encoding="utf-8")
    assert "subprocess" not in source and "urllib" not in source and "socket" not in source


# --- the wait of the step, run for real with a `gh` that answers in turn ------------------------

STEP = "      - name: Latest full run\n"


def step_script() -> str:
    block = text().split(STEP, 1)[1].split("\n      - ", 1)[0]
    body = block.split("run: |\n", 1)[1]
    script = "\n".join(line[10:] for line in body.splitlines())
    return (
        script.replace("${{ github.repository }}", "acme/widgets")
        .replace("${{ github.event.pull_request.head.sha }}", HEAD)
        .replace("$RUNNER_TEMP", "$TMP")
    )


def run_step(tmp_path: Path, answers: list, fail_gh: bool = False):
    """Run the step's shell with a gh that serves `answers` one per call (the last one repeats),
    a `sleep` that only counts, and `python` as this interpreter, run from the repository root."""
    import os
    import stat

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for i, answer in enumerate(answers):
        (tmp_path / f"answer-{i}.json").write_text(json.dumps({"workflow_runs": answer}))
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        f'n=$(cat "{tmp_path}/calls" 2>/dev/null || echo 0)\n'
        f'echo $((n + 1)) > "{tmp_path}/calls"\n'
        + ("exit 1\n" if fail_gh else "")
        + f'i=$n; [ "$i" -ge {len(answers) - 1} ] && i={len(answers) - 1}\n'
        f'cat "{tmp_path}/answer-$i.json"\n'
    )
    sleep = bin_dir / "sleep"
    sleep.write_text(f'#!/bin/sh\necho x >> "{tmp_path}/sleeps"\n')
    (bin_dir / "python").symlink_to(sys.executable)
    for tool in (gh, sleep):
        tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "TMP": str(tmp_path)}
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, a stubbed gh
        ["bash", "-c", step_script()], cwd=ROOT, env=env, capture_output=True, text=True
    )
    calls = int((tmp_path / "calls").read_text()) if (tmp_path / "calls").exists() else 0
    sleeps = (tmp_path / "sleeps").read_text().count("x") if (tmp_path / "sleeps").exists() else 0
    return proc, calls, sleeps


GREEN = [run_of(FULL, "success", "2026-10-25T10:00:00Z")]
RUNNING = [run_of(FULL, None, "2026-10-25T10:00:00Z", status="in_progress")]
RED = [run_of(FULL, "failure", "2026-10-25T10:00:00Z")]


def test_the_step_passes_at_once_after_a_green_full_run(tmp_path):
    """Verdict on 5aaaf17: no wait when the full run is done and green."""
    proc, calls, sleeps = run_step(tmp_path, [GREEN])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (calls, sleeps) == (1, 0)


def test_the_step_waits_for_a_running_full_run_and_then_decides(tmp_path):
    """Verdict on 5aaaf17: an in-progress response, then a completed one on the next call."""
    proc, calls, sleeps = run_step(tmp_path, [RUNNING, GREEN])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (calls, sleeps) == (2, 1)
    (tmp_path / "again").mkdir()
    proc, calls, sleeps = run_step(tmp_path / "again", [RUNNING, RUNNING, RED])
    assert proc.returncode == 1 and (calls, sleeps) == (3, 2)


def test_the_step_waits_at_most_twenty_minutes_and_then_fails(tmp_path):
    """Verdict on 5aaaf17: every 30 seconds, 40 waits, then a failure."""
    proc, calls, sleeps = run_step(tmp_path, [RUNNING])
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert sleeps == 40 and calls == 41
    assert "sleep 30" in step_script()


def test_the_step_fails_at_once_when_the_runs_cannot_be_read(tmp_path):
    """Verdict on 460dab3: unreadable fails; nothing is waited for."""
    proc, calls, sleeps = run_step(tmp_path, [GREEN], fail_gh=True)
    assert proc.returncode == 1 and (calls, sleeps) == (1, 0)


def test_the_get_no_longer_filters_on_completed_runs():
    """Verdict on 5aaaf17: a running run must be visible to be waited for."""
    assert "status=completed" not in step_script()


# --- steps the last full run never reached (brief #261) -----------------------------------------

RUN_ID = 2611
# Every step of the `governance` job of a full pull_request run, in the order the jobs GET lists.
FULL_STEPS = (
    "Set up job",
    "Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "Base of the merge ref",
    "Run actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    "Status-only final commit",
    "Latest full run",
    "Install tooling",
    "PR body file",
    "PR comments",
    "PR states and open pull requests",
    "check_protected_changes",
    "check_requirements",
    "check_adrs",
    "check_numbers",
    "check_specs",
    "check_neutrality",
    "check_build_state",
    "check_kit_tests",
    "check_design",
    "reviewers --check",
    "reviewers --check-codeowners",
    "check_pr_mode",
    "check_final_clearance",
    "Release check",
    "Open briefs",
    "PR body shape",
    "Lint",
    "Tests of the checks",
    "Project tests",
    "Secret scan",
    "Post Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "Complete job",
)
HIDDEN = ("Lint", "Tests of the checks", "Project tests", "Secret scan")


def jobs_with(failed=("PR body shape",), skipped=(), project=True) -> dict:
    """The jobs of a full run: `failed` failed, `skipped` skipped, every other step passed. A full
    run always skips `Latest full run` (edited only), and a project `Release check` (the kit's own
    repository has `kit/agk-kit.mk`) while the kit's repository skips `Project tests`."""
    own = {"Latest full run", "Release check" if project else "Project tests"}
    steps = []
    for number, name in enumerate(FULL_STEPS, start=1):
        conclusion = (
            "failure"
            if name in failed
            else "skipped"
            if name in skipped or name in own
            else "success"
        )
        steps.append(
            {"name": name, "status": "completed", "conclusion": conclusion, "number": number}
        )
    return {"total_count": 1, "jobs": [{"name": "governance", "steps": steps}]}


def check_jobs(tmp_path: Path, jobs: dict):
    red = {**run_of(FULL, "failure", "2026-10-26T10:00:00Z"), "id": RUN_ID}
    (tmp_path / "jobs.json").write_text(json.dumps(jobs))
    return check(tmp_path, [red], "--jobs", str(tmp_path / "jobs.json"))


def test_the_measured_run_a_body_failure_with_the_later_steps_skipped_is_not_cured(tmp_path):
    """Brief #261 Measured (REQ-039): `PR body shape` failed; Lint, the tests and the secret scan
    were skipped. An edited description must leave governance red."""
    out = check_jobs(tmp_path, jobs_with(skipped=HIDDEN))
    assert out.returncode == 1, out.stdout
    assert out.stdout == (
        "FAIL full-run: rule 2: the last full run did not reach Lint, Tests of the checks, "
        "Project tests, Secret scan; push a commit or re-run it\n"
    )


@pytest.mark.parametrize("project", [True, False])
@pytest.mark.parametrize(
    "failed", [("PR body shape",), ("check_specs",), ("check_pr_mode", "PR body shape")]
)
def test_a_body_failure_where_every_other_step_ran_and_passed_is_cured(tmp_path, failed, project):
    """Brief #261 answer 4 (REQ-039): as today, in a project and in the kit's own repository."""
    out = check_jobs(tmp_path, jobs_with(failed=failed, project=project))
    assert (out.returncode, out.stdout) == (
        0,
        "ok full-run (the failed steps read the body only)\n",
    )


@pytest.mark.parametrize(
    "skipped",
    [
        ("Lint",),
        ("Secret scan",),
        ("Project tests",),
        ("Open briefs",),
        ("PR comments",),
        ("check_adrs",),
        ("Install tooling", "check_kit_tests", "Lint", "Tests of the checks", "Project tests"),
    ],
)
def test_any_other_skipped_step_in_a_run_with_a_failure_is_not_cured(tmp_path, skipped):
    """Brief #261 answer 1 (REQ-039): GitHub shows a step skipped by its own `if:` and one skipped
    because an earlier step failed alike, so only the steps whose own condition skips them on a
    full run (`OWN_CONDITION`) may be skipped; a status-only skip is refused too (re-run it)."""
    out = check_jobs(tmp_path, jobs_with(skipped=skipped))
    assert out.returncode == 1
    assert out.stdout == (
        f"FAIL full-run: rule 2: the last full run did not reach {', '.join(skipped)}; "
        "push a commit or re-run it\n"
    )


def test_a_skipped_body_step_is_repeated_by_the_edited_run_and_does_not_block(tmp_path):
    """Brief #261 answer 1 (REQ-039): the partial run repeats a skipped body step."""
    out = check_jobs(tmp_path, jobs_with(failed=("check_specs",), skipped=("PR body shape",)))
    assert out.returncode == 0, out.stdout


def test_a_failure_of_another_step_still_gives_the_rule_and_names_no_step(tmp_path):
    """Brief #216 build b, unchanged: a lint failure is not a body failure."""
    out = check_jobs(tmp_path, jobs_with(failed=("PR body shape", "Lint"), skipped=HIDDEN[1:]))
    assert out.stdout == (
        "FAIL full-run: rule 2: the latest full governance run of the head did not succeed\n"
    )


def test_the_message_names_steps_and_never_a_value(tmp_path):
    """CLAUDE.md rule 6 (REQ-039): the step names of the workflow, never the head or the run id."""
    out = check_jobs(tmp_path, jobs_with(skipped=HIDDEN))
    assert HEAD not in out.stdout and str(RUN_ID) not in out.stdout


def test_the_steps_a_full_run_skips_by_their_own_condition_are_pinned_to_the_workflow():
    """Brief #261 answer 1 (REQ-039): each step of `OWN_CONDITION` is skipped on a full run only by
    its own condition (on an edit only, or by the tree of the repository, `kit/agk-kit.mk`), never
    by an earlier failure: it comes before any check or carries `!cancelled()`. `Project tests`
    is skipped by the tree in the kit's own repository, where `Release check` runs, only."""
    sys.path.insert(0, str(ROOT / "scripts" / "agk"))
    import full_run

    body = text().split("    steps:\n", 1)[1]
    blocks = {
        m.group(1): m.group(2)
        for m in re.finditer(r"(?ms)^      - name: (.+?)\n(.*?)(?=^      - |\Z)", body)
    }
    assert set(full_run.OWN_CONDITION) == {"Latest full run", "Release check"}
    assert full_run.KIT_ONLY == ("Project tests", "Release check")
    for name in (*full_run.OWN_CONDITION, full_run.KIT_ONLY[0]):
        cond = blocks[name].split("\n", 1)[0]
        assert cond.startswith("        if: "), name
        assert "github.event.action == 'edited'" in cond or "hashFiles('kit/agk-kit.mk')" in cond
        assert "!cancelled()" in cond or name == "Latest full run", name
    assert "hashFiles('kit/agk-kit.mk') == ''" in blocks["Project tests"].split("\n", 1)[0]
    assert "hashFiles('kit/agk-kit.mk') != ''" in blocks["Release check"].split("\n", 1)[0]
    names = list(blocks)
    assert names.index("Latest full run") < names.index("PR body file")


# --- a cancelled full run is never the latest (brief #272) --------------------------------------

SAME = "2026-10-26T20:52:15Z"


def full_of(conclusion: str | None, rid: int, created: str = SAME, status: str = "completed"):
    return {**run_of(FULL, conclusion, created, status=status), "id": rid}


@pytest.mark.parametrize("order", ["cancelled first", "success first"])
def test_the_tie_of_pull_request_271_reads_the_run_that_completed(tmp_path, order):
    """Brief #272 Measured (REQ-039): two full runs of one second, one cancelled by the
    concurrency group, one green; in either list order the edited run passes."""
    cancelled, green = full_of("cancelled", 40399457998), full_of("success", 40399458037)
    runs = [cancelled, green] if order == "cancelled first" else [green, cancelled]
    out = check(tmp_path, runs)
    assert (out.returncode, out.stdout) == (0, "ok full-run\n"), out.stdout


def test_a_cancelled_run_is_not_the_latest_even_when_it_is_newer(tmp_path):
    """Brief #272 answer 1 (REQ-039): a cancelled run never beats one that is not cancelled."""
    runs = [full_of("success", 1, "2026-10-26T10:00:00Z"), full_of("cancelled", 2, SAME)]
    assert check(tmp_path, runs).returncode == 0


def test_a_tie_of_two_runs_that_are_not_cancelled_goes_to_the_larger_id(tmp_path):
    """Brief #272 answer 1 (REQ-039): ties broken by the larger run `id`."""
    for runs in (
        [full_of("success", 1), full_of("failure", 2)],
        [full_of("failure", 2), full_of("success", 1)],
    ):
        out = check(tmp_path, runs)
        assert (out.returncode, out.stdout) == (4, "jobs 2\n"), out.stdout


def test_cancelled_runs_alone_behave_as_today(tmp_path):
    """Brief #272 answer 2 (REQ-039): with only cancelled runs, the latest of them is asked for,
    and its jobs then refuse with rule 2, as today; a running run is still waited for."""
    out = check(tmp_path, [full_of("cancelled", 1), full_of("cancelled", 2)])
    assert (out.returncode, out.stdout) == (4, "jobs 2\n"), out.stdout
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps({"jobs": [{"name": "governance", "steps": []}]}))
    out = check(tmp_path, [full_of("cancelled", 2)], "--jobs", str(jobs))
    assert out.returncode == 1 and out.stdout.startswith("FAIL full-run: rule 2:"), out.stdout
    running = full_of(None, 3, "2026-10-26T20:53:00Z", status="in_progress")
    assert check(tmp_path, [full_of("cancelled", 1), running]).returncode == 3


def test_a_newer_failed_run_still_beats_an_older_success(tmp_path):
    """Brief #272 answer 3 (REQ-039): only cancelled runs are set aside."""
    runs = [full_of("success", 1, "2026-10-26T10:00:00Z"), full_of("failure", 2, SAME)]
    assert check(tmp_path, runs).stdout == "jobs 2\n"
