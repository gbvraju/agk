"""Brief #1554 answer 4 (REQ-039, ADR-0654): the doctor's `merger-variable` line.

Where the merger would stop at its gate anyway (`auto_merge` not `true`, or `execution = "local"`),
the doctor offers the one command that keeps the merger's comment and scheduled jobs from starting,
with the scheduled starts a day it saves; where auto-merge is on in GitHub mode and the repository
variable is `off`, it warns that only the router's dispatch merges. It names the setting, never
runs the command, and reads the variable with one GET (a 404 is unset). Saved answers only
(example names), no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import doctor
import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
# The schedule part of merger.yml (a copy: a project tree under test may hold no workflow file).
MERGER = 'name: merger\non:\n  schedule:\n    - cron: "*/15 * * * *"\n'
ON = {"flow": {"auto_merge": True, "auto_merge_method": "squash"}}
OFF_DEFAULT: dict = {}
LOCAL = {"execution": "local", **ON}
COMMAND = "gh variable set AGK_MERGER --body off"


def world(tmp_path: Path, variable: object, merger: bool = True) -> tuple[Path, doctor.Reads]:
    """A project root (with or without merger.yml) and the saved answer for the variable."""
    root = tmp_path / "root"
    (root / ".github" / "workflows").mkdir(parents=True)
    if merger:
        (root / ".github" / "workflows" / "merger.yml").write_text(MERGER, encoding="utf-8")
    api = tmp_path / "api"
    api.mkdir()
    if variable is not None:
        (api / "variable-agk-merger.json").write_text(json.dumps(variable), encoding="utf-8")
    return root, doctor.Reads("example-owner/example-repo", api)


UNSET = {"message": "Not Found", "status": "404"}


@pytest.mark.parametrize("config", [OFF_DEFAULT, LOCAL, {"flow": {"auto_merge": False}}])
def test_a_merger_that_only_reads_off_is_offered_the_command(tmp_path, config):
    """REQ-039: brief #1554 answer 4 (the defaults, and local mode, are offered `off`)."""
    root, reads = world(tmp_path, UNSET)
    res = doctor.merger_variable_result(root, reads, config)
    assert res.status == "fail"
    assert COMMAND in res.message and "up to 96 scheduled jobs" in res.message
    assert "setting: auto_merge and execution" in res.message


def test_the_variable_off_where_the_merger_stops_anyway_is_ok(tmp_path):
    """REQ-039: brief #1554 answer 4 (nothing to change)."""
    root, reads = world(tmp_path, {"name": "AGK_MERGER", "value": "off"})
    assert doctor.merger_variable_result(root, reads, OFF_DEFAULT).status == "ok"


def test_auto_merge_on_with_the_variable_off_warns(tmp_path):
    """REQ-039: brief #1554 answer 4 (only the router's dispatch merges; no schedule sweep)."""
    root, reads = world(tmp_path, {"name": "AGK_MERGER", "value": "off"})
    res = doctor.merger_variable_result(root, reads, ON)
    assert res.status == "fail" and "only the router's dispatch merges" in res.message
    assert COMMAND not in res.message


@pytest.mark.parametrize("variable", [UNSET, {"name": "AGK_MERGER", "value": "on"}])
def test_auto_merge_on_without_the_variable_off_is_ok(tmp_path, variable):
    """REQ-039: brief #1554 answer 4 (unset, or any other value, reads as before)."""
    root, reads = world(tmp_path, variable)
    assert doctor.merger_variable_result(root, reads, ON).status == "ok"


def test_without_the_merger_workflow_nothing_is_read(tmp_path):
    """REQ-039: brief #1554 answer 6 (personal mode and a project without it: no change)."""
    root, reads = world(tmp_path, None, merger=False)
    res = doctor.merger_variable_result(root, reads, OFF_DEFAULT)
    assert res.status == "ok" and "not applicable" in res.message
    assert reads.seen == {}


def test_an_unread_variable_is_cannot_check_never_ok(tmp_path):
    """REQ-039: brief #1554 answer 4 (an unknown answer is never ok)."""
    root, reads = world(tmp_path, None)
    res = doctor.merger_variable_result(root, reads, OFF_DEFAULT)
    assert (res.status, res.reason) == ("cannot-check", "bad-response")


def test_the_row_is_a_warning_of_the_report_and_never_runs_the_command():
    """REQ-039: brief #1554 answer 4 (one row; the owner runs it, session rule 30)."""
    severity, _, _, fix = doctor.CHECKS["merger-variable"]
    assert severity == "warn" and "never runs it" in fix
    source = (KIT_ROOT / "scripts" / "agk" / "doctor.py").read_text(encoding="utf-8")
    assert '"variable", "set"' not in source and "gh variable set" not in source


def test_the_schedule_rate_is_read_from_the_workflow():
    """REQ-039: brief #1554 answer 4 (the starts a day at the project's own schedule)."""
    assert doctor.scheduled_per_day(MERGER) == 96
    kit = KIT_ROOT / ".github" / "workflows" / "merger.yml"
    if kit.is_file():  # the kit's own file, where it is there
        assert doctor.scheduled_per_day(kit.read_text(encoding="utf-8")) == 96
    assert doctor.scheduled_per_day('cron: "*/30 * * * *"') == 48
    assert doctor.scheduled_per_day('cron: "5 * * * *"') is None
