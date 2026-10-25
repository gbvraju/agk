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


def test_a_full_run_still_running_or_on_another_head_does_not_count(tmp_path):
    """Verdict on 460dab3, item 2: only a completed run of this head."""
    running = run_of(FULL, None, "2026-10-25T11:00:00Z", status="in_progress")
    assert check(tmp_path, [running]).returncode == 1
    other = run_of(FULL, "success", "2026-10-25T11:00:00Z", head=OTHER)
    assert check(tmp_path, [other]).returncode == 1
    older_green = run_of(FULL, "success", "2026-10-25T10:00:00Z")
    assert check(tmp_path, [older_green, running]).returncode == 0


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
    assert block.count("gh api --method GET") == 1
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
