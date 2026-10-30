"""Tests of scripts/agk/local_mode.py (brief #371, ADR-0213): one command enters and leaves local
mode, and `leave` lists the merges made on local evidence and the state of the catch-up run.
Saved API responses (`--api-dir`), no network, no `gh`. REQ-039"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = "octo/project"
SINCE = "2026-10-28T09:00:00Z"


def workflow(wid: int, path: str, state: str, updated: str = SINCE) -> dict:
    return {
        "id": wid,
        "name": path.rsplit("/", 1)[-1].removesuffix(".yml"),
        "path": f".github/workflows/{path}",
        "state": state,
        "updated_at": updated,
    }


def pull(n: int, merged: str | None, sha: str, base: str = "main", title: str = "a change") -> dict:
    return {
        "number": n,
        "title": title,
        "merged_at": merged,
        "updated_at": merged or "2026-10-29T00:00:00Z",
        "merge_commit_sha": sha,
        "base": {"ref": base},
    }


def check(name: str, conclusion: str | None, sha: str, started: str, rid: int = 1) -> dict:
    return {
        "id": rid,
        "name": name,
        "head_sha": sha,
        "status": "completed" if conclusion else "in_progress",
        "conclusion": conclusion,
        "started_at": started,
    }


HEAD = "c" * 40


def api(tmp_path: Path, workflows: list[dict], pulls=(), checks=(), head: str = HEAD) -> Path:
    """A folder of saved responses: one `<name>.json` per read."""
    folder = tmp_path / "api"
    folder.mkdir(exist_ok=True)
    data = {
        "workflows": {"total_count": len(workflows), "workflows": workflows},
        "pulls": list(pulls),
        "commit": {"sha": head},
        "check-runs": {"total_count": len(checks), "check_runs": list(checks)},
    }
    for name, value in data.items():
        (folder / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
    return folder


def refuse(folder: Path, name: str, status: int = 403) -> None:
    (folder / f"{name}.json").unlink(missing_ok=True)
    (folder / f"{name}.status").write_text(f"{status}\n", encoding="utf-8")


def calls(folder: Path) -> list[str]:
    log = folder / "calls.log"
    return log.read_text(encoding="utf-8").splitlines() if log.is_file() else []


def local_mode(repo, folder: Path, *args: str):
    if not (repo.root / "agk.toml").exists():
        repo.write(
            "agk.toml", 'default_branch = "main"\nrequired_checks = ["proof", "governance"]\n'
        )
    return repo.run("local_mode.py", *args, "--repo", REPO, "--api-dir", str(folder))


ACTIVE = [
    workflow(101, "agk-route.yml", "active"),
    workflow(102, "governance.yml", "active"),
    workflow(103, "project-build.yml", "active"),
    workflow(104, "old.yml", "disabled_manually"),
]


# --- enter ----------------------------------------------------------------------------------------


def test_enter_dry_run_lists_every_active_workflow_and_its_call_and_writes_nothing(repo, tmp_path):
    """REQ-039: brief #371 answers 1 and 4 (the dry run writes nothing)."""
    folder = api(tmp_path, ACTIVE)
    proc = local_mode(repo, folder, "enter")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout
    assert "dry run" in out
    for wid, name in ((101, "agk-route.yml"), (102, "governance.yml"), (103, "project-build.yml")):
        line = f"gh api --method PUT repos/{REPO}/actions/workflows/{wid}/disable"
        assert line in out, line
        assert name in out, name
    assert "workflows/104/" not in out, "a workflow that is already disabled is not listed"
    assert calls(folder) == []
    assert not any(p.name.startswith("put-") for p in folder.iterdir())


def test_enter_write_makes_one_call_per_workflow_and_prints_one_line_each(repo, tmp_path):
    """REQ-039: brief #371 answers 1 and 4 (`--write` makes one call per workflow)."""
    folder = api(tmp_path, ACTIVE)
    proc = local_mode(repo, folder, "enter", "--write")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls(folder) == [
        f"PUT /repos/{REPO}/actions/workflows/101/disable",
        f"PUT /repos/{REPO}/actions/workflows/102/disable",
        f"PUT /repos/{REPO}/actions/workflows/103/disable",
    ]
    done = [ln for ln in proc.stdout.splitlines() if ln.startswith("disabled ")]
    assert len(done) == 3, proc.stdout
    assert "dry run" not in proc.stdout


def test_a_refused_call_is_reported_and_the_rest_are_still_made(repo, tmp_path):
    """REQ-039: brief #371 answer 4 (a refused call (403) is reported and the rest still listed)."""
    folder = api(tmp_path, ACTIVE)
    refuse(folder, "put-102-disable", 403)
    proc = local_mode(repo, folder, "enter", "--write")
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert len(calls(folder)) == 3
    out = proc.stdout
    assert "refused governance.yml (id 102): HTTP 403" in out
    assert f"gh api --method PUT repos/{REPO}/actions/workflows/102/disable" in out
    assert "disabled agk-route.yml (id 101)" in out
    assert "disabled project-build.yml (id 103)" in out


def test_enter_with_nothing_active_says_so(repo, tmp_path):
    """REQ-039: brief #371 answer 1 (nothing to disable)."""
    folder = api(tmp_path, [workflow(104, "old.yml", "disabled_manually")])
    proc = local_mode(repo, folder, "enter", "--write")
    assert proc.returncode == 0, proc.stdout
    assert "active workflows: 0" in proc.stdout
    assert calls(folder) == []


def test_workflows_that_cannot_be_read_are_refused_by_class(repo, tmp_path):
    """REQ-039: brief #371 answer 1 (a refusal names the class, never a value)."""
    folder = api(tmp_path, ACTIVE)
    refuse(folder, "workflows", 404)
    proc = local_mode(repo, folder, "enter")
    assert proc.returncode == 1, proc.stdout
    assert "the workflows cannot be read (missing" in proc.stdout
    assert REPO not in proc.stdout


# --- leave ----------------------------------------------------------------------------------------

DISABLED = [
    workflow(101, "agk-route.yml", "disabled_manually", "2026-10-28T09:05:00Z"),
    workflow(102, "governance.yml", "disabled_manually", SINCE),
    workflow(103, "project-build.yml", "disabled_manually", "2026-10-28T09:10:00Z"),
    workflow(105, "nightly.yml", "disabled_inactivity", "2026-08-01T00:00:00Z"),
    workflow(106, "proof.yml", "active", "2026-01-01T00:00:00Z"),
]
MERGES = [
    pull(41, "2026-10-29T10:00:00Z", "a" * 40, title="first local merge"),
    pull(42, "2026-10-30T11:00:00Z", HEAD, title="second local merge"),
    pull(40, "2026-10-27T10:00:00Z", "9" * 40, title="before local mode"),
    pull(43, None, "8" * 40, title="closed unmerged"),
    pull(44, "2026-10-29T12:00:00Z", "7" * 40, base="release", title="another base"),
]


def test_leave_dry_run_lists_each_disabled_workflow_and_its_enable_call(repo, tmp_path):
    """REQ-039: brief #371 answers 1 and 4 (`leave` lists the disabled workflows; dry run)."""
    folder = api(tmp_path, DISABLED, MERGES)
    proc = local_mode(repo, folder, "leave")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout
    for wid in (101, 102, 103):
        assert f"gh api --method PUT repos/{REPO}/actions/workflows/{wid}/enable" in out, wid
    assert "workflows/105/enable" not in out, "a workflow GitHub disabled for inactivity stays"
    assert "nightly.yml (id 105, disabled_inactivity)" in out
    assert "workflows/106/" not in out
    assert calls(folder) == []


def test_leave_lists_the_merges_since_the_oldest_disabled_workflow_and_no_catch_up(repo, tmp_path):
    """REQ-039: brief #371 answers 2 and 4 (`leave` with merges and no catch-up)."""
    folder = api(tmp_path, DISABLED, MERGES)
    out = local_mode(repo, folder, "leave").stdout
    assert f"local mode since: {SINCE} (the oldest workflow disabled by hand)" in out
    assert "merged on local evidence: 2" in out
    first = out.index("#41 2026-10-29T10:00:00Z aaaaaaa first local merge")
    second = out.index("#42 2026-10-30T11:00:00Z ccccccc second local merge")
    assert first < second
    for absent in ("#40 ", "#43 ", "#44 "):
        assert absent not in out, absent
    assert "catch-up: not run yet" in out


def test_leave_with_a_green_catch_up_names_each_required_check(repo, tmp_path):
    """REQ-039: brief #371 answers 2 and 4 (`leave` with a green catch-up)."""
    checks = [
        check("governance", "success", HEAD, "2026-10-30T12:00:00Z", 7),
        check("proof", "success", HEAD, "2026-10-30T12:01:00Z", 8),
        check("governance", "failure", HEAD, "2026-10-28T08:00:00Z", 3),
    ]
    folder = api(tmp_path, DISABLED, MERGES, checks)
    proc = local_mode(repo, folder, "leave")
    assert proc.returncode == 0, proc.stdout
    out = proc.stdout
    assert "catch-up proof: success on ccccccc" in out
    assert "catch-up governance: success on ccccccc" in out
    assert "catch-up: green" in out
    assert "priority-0" not in out


def test_leave_with_a_red_catch_up_says_to_file_a_priority_0_brief(repo, tmp_path):
    """REQ-039: brief #371 answers 2 and 4 (`leave` with a red catch-up)."""
    checks = [
        check("governance", "failure", HEAD, "2026-10-30T12:00:00Z", 7),
        check("proof", "success", HEAD, "2026-10-30T12:01:00Z", 8),
    ]
    folder = api(tmp_path, DISABLED, MERGES, checks)
    proc = local_mode(repo, folder, "leave")
    assert proc.returncode == 3, proc.stdout
    out = proc.stdout
    assert "catch-up governance: failure on ccccccc" in out
    assert "catch-up: red" in out and "file a priority-0 brief" in out


def test_a_run_before_local_mode_is_no_catch_up(repo, tmp_path):
    """REQ-039: brief #371 answer 2 (only a run after local mode began counts; a run refused by a
    billing block before the workflows were disabled is not the catch-up)."""
    checks = [check("governance", "failure", HEAD, "2026-10-28T08:00:00Z", 3)]
    folder = api(tmp_path, DISABLED, MERGES, checks)
    proc = local_mode(repo, folder, "leave")
    assert proc.returncode == 0, proc.stdout
    assert "catch-up: not run yet" in proc.stdout
    assert "failure" not in proc.stdout


def test_a_catch_up_still_running_is_named_and_not_green(repo, tmp_path):
    """REQ-039: brief #371 answer 2 (a run in progress)."""
    checks = [
        check("governance", None, HEAD, "2026-10-30T12:00:00Z", 7),
        check("proof", "success", HEAD, "2026-10-30T12:01:00Z", 8),
    ]
    folder = api(tmp_path, DISABLED, MERGES, checks)
    out = local_mode(repo, folder, "leave").stdout
    assert "catch-up governance: running on ccccccc" in out
    assert "catch-up: green" not in out


def test_a_required_check_without_a_run_is_not_run_yet(repo, tmp_path):
    """REQ-039: brief #371 answer 2 (one required check ran, the other did not)."""
    checks = [check("governance", "success", HEAD, "2026-10-30T12:00:00Z", 7)]
    folder = api(tmp_path, DISABLED, MERGES, checks)
    out = local_mode(repo, folder, "leave").stdout
    assert "catch-up governance: success on ccccccc" in out
    assert "catch-up proof: not run yet" in out
    assert "catch-up: green" not in out


def test_leave_write_enables_each_disabled_workflow_after_listing_the_merges(repo, tmp_path):
    """REQ-039: brief #371 answers 1, 2 and 4 (`--write` makes one call per workflow)."""
    folder = api(tmp_path, DISABLED, MERGES)
    proc = local_mode(repo, folder, "leave", "--write")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls(folder) == [
        f"PUT /repos/{REPO}/actions/workflows/101/enable",
        f"PUT /repos/{REPO}/actions/workflows/102/enable",
        f"PUT /repos/{REPO}/actions/workflows/103/enable",
    ]
    out = proc.stdout
    assert "enabled governance.yml (id 102)" in out
    assert "merged on local evidence: 2" in out


def test_leave_write_reports_a_refused_enable_and_makes_the_rest(repo, tmp_path):
    """REQ-039: brief #371 answer 4 (a refused call on leave)."""
    folder = api(tmp_path, DISABLED, MERGES)
    refuse(folder, "put-101-enable", 403)
    proc = local_mode(repo, folder, "leave", "--write")
    assert proc.returncode == 3, proc.stdout
    assert len(calls(folder)) == 3
    assert "refused agk-route.yml (id 101): HTTP 403" in proc.stdout
    assert "enabled project-build.yml (id 103)" in proc.stdout


def test_leave_after_the_workflows_are_enabled_takes_the_start_from_since(repo, tmp_path):
    """REQ-039: brief #371 answer 2 (once nothing is disabled, `--since` gives the start)."""
    enabled = [workflow(101, "agk-route.yml", "active", "2026-10-30T11:30:00Z")]
    folder = api(tmp_path, enabled, MERGES)
    out = local_mode(repo, folder, "leave").stdout
    assert "merged on local evidence: unknown" in out and "--since" in out
    out = local_mode(repo, folder, "leave", "--since", "2026-10-28").stdout
    assert "local mode since: 2026-10-28T00:00:00Z (--since)" in out
    assert "merged on local evidence: 2" in out


def test_pull_requests_that_cannot_be_read_are_unknown_not_zero(repo, tmp_path):
    """REQ-039: brief #371 answer 2 (an unreadable list is never 0)."""
    folder = api(tmp_path, DISABLED, MERGES)
    refuse(folder, "pulls", 403)
    out = local_mode(repo, folder, "leave").stdout
    assert "merged on local evidence: unknown (the pull requests cannot be read: refused)" in out


def test_check_runs_that_cannot_be_read_are_unknown(repo, tmp_path):
    """REQ-039: brief #371 answer 2 (an unreadable catch-up is never green)."""
    folder = api(tmp_path, DISABLED, MERGES)
    refuse(folder, "check-runs", 403)
    out = local_mode(repo, folder, "leave").stdout
    assert "catch-up: unknown (the check runs cannot be read: refused)" in out


def test_the_required_checks_are_read_from_the_setting(repo, tmp_path):
    """REQ-039: brief #371 answer 2 (each required check: `required_checks` in agk.toml)."""
    repo.write("agk.toml", 'default_branch = "main"\nrequired_checks = ["build"]\n')
    checks = [check("build", "success", HEAD, "2026-10-30T12:00:00Z", 7)]
    folder = api(tmp_path, DISABLED, MERGES, checks)
    out = local_mode(repo, folder, "leave").stdout
    assert "catch-up build: success on ccccccc" in out
    assert "catch-up: green" in out
    assert "governance" not in out.split("catch-up", 1)[1]


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["start"],
        ["enter", "--since", "2026-10-28"],
        ["leave", "--since", "yesterday"],
        ["enter", "--bogus"],
    ],
)
def test_usage(repo, tmp_path, args):
    """REQ-039: brief #371 answer 1 (usage)."""
    repo.write("agk.toml", 'default_branch = "main"\n')
    proc = repo.run("local_mode.py", *args)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "usage: local_mode.py" in proc.stderr


def test_the_script_makes_no_network_call_of_its_own():
    """REQ-039: brief #371 answer 1 (`gh` holds the credential; the script holds none)."""
    from conftest import SCRIPTS

    text = (SCRIPTS / "local_mode.py").read_text(encoding="utf-8")
    for word in ("urllib", "http.client", "requests", "socket", "token"):
        assert f"import {word}" not in text and f"from {word}" not in text, word
    assert "shell=True" not in text
