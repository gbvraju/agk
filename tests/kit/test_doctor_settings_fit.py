# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Brief #1617 (ADR-0686): doctor warns when the start settings do not fit how the project runs."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "agk"))

import doctor  # noqa: E402

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
PROTECTED = "scripts/agk/\ntests/\n"
BUILD = "Size: M\nTouches: scripts/agk/doctor.py\n"
SMALL = "Size: S\nTouches: docs/guides/x.md\n"


class Saved:
    """Saved reads by name, as `--api-dir` gives them; records the names read."""

    def __init__(self, **data) -> None:
        self.data = data
        self.repo = "example/project"
        self.names: list[str] = []

    def get(self, name: str, path: str, not_found=None, raw: bool = False):
        self.names.append(name)
        if name not in self.data:
            return None, "bad-response"
        return self.data[name], ""


def project(tmp_path: Path, toml: str = "") -> Path:
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "protected-paths.txt").write_text(PROTECTED, encoding="utf-8")
    (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    return tmp_path


def briefs(*bodies: str) -> list[dict]:
    return [{"number": n + 1, "body": b} for n, b in enumerate(bodies)]


# --- tier-use -----------------------------------------------------------------------------------


def test_only_build_briefs_warn_that_mid_gets_none(tmp_path):
    """REQ-072: answer 1; every brief touches a protected path, so `mid` is never routed."""
    res = doctor.tier_use_result(project(tmp_path), Saved(**{"briefs-open": briefs(BUILD, BUILD)}))
    assert res.status == "fail"
    assert "mid: 0 of 2 open briefs" in res.message
    assert "strongest 2" in res.message


def test_a_small_brief_uses_mid_and_nothing_warns(tmp_path):
    """REQ-072: answer 3; a brief that touches no protected path is `small` and runs on `mid`."""
    res = doctor.tier_use_result(project(tmp_path), Saved(**{"briefs-open": briefs(BUILD, SMALL)}))
    assert res.status == "ok" and "mid 1" in res.message


def test_no_open_briefs_is_ok_and_pull_requests_are_not_briefs(tmp_path):
    """REQ-072: answer 4."""
    found = [{"number": 9, "body": BUILD, "pull_request": {}}]
    res = doctor.tier_use_result(project(tmp_path), Saved(**{"briefs-open": found}))
    assert res.status == "ok" and res.message == " (no open briefs)"


def test_briefs_that_cannot_be_read_are_cannot_check(tmp_path):
    """REQ-072: answer 4; unknown is never ok."""
    assert doctor.tier_use_result(project(tmp_path), Saved()).status == "cannot-check"


def test_a_refused_models_entry_names_the_setting(tmp_path):
    """REQ-072: answer 2."""
    root = project(tmp_path, '[models]\nbuild = { tier = "huge", effort = "low" }\n')
    res = doctor.tier_use_result(root, Saved(**{"briefs-open": briefs(BUILD)}))
    assert res.status == "fail" and "(setting: models" in res.message and "huge" not in res.message


def test_a_models_table_that_routes_build_to_mid_is_quiet(tmp_path):
    """REQ-072: answer 2; the tiers the kinds use come from `[models]` when it is set."""
    toml = (
        '[models]\nbuild = { tier = "mid", effort = "medium" }\n'
        'small = { tier = "mid", effort = "low" }\nmechanical = { tier = "mid", effort = "low" }\n'
        'design = { tier = "mid", effort = "high" }\n'
    )
    res = doctor.tier_use_result(project(tmp_path, toml), Saved(**{"briefs-open": briefs(BUILD)}))
    assert res.status == "ok"


# --- launch-adapter -----------------------------------------------------------------------------

PS1 = '[flow]\nauto_start = true\nlaunch_adapter = "pwsh -File scripts/start.ps1"\n'


def adapter_project(tmp_path: Path, toml: str = PS1) -> Path:
    root = project(tmp_path, toml)
    (root / "scripts").mkdir()
    (root / "scripts" / "start.ps1").write_text('claude --agent "$env:AGK_AGENT"\n', "utf-8")
    return root


def test_a_cloud_session_says_auto_start_starts_nothing_here(tmp_path):
    """REQ-072: answer 1, Q-1617-2; information, `not run here`, never an error."""
    res = doctor.launch_adapter_result(adapter_project(tmp_path), platform="win32", cloud=True)
    assert res.status == "fail"
    assert "auto_start starts nothing from a cloud session" in res.message
    assert "not run here" in res.message and "(setting: [flow] launch_adapter)" in res.message
    assert "(verify)" in res.message
    assert "pwsh" not in res.message
    assert doctor.CHECKS["launch-adapter"][0] == "warn"


def test_a_windows_adapter_on_another_platform_warns(tmp_path):
    """REQ-072: answer 1."""
    res = doctor.launch_adapter_result(adapter_project(tmp_path), platform="linux", cloud=False)
    assert res.status == "fail"
    assert "the adapter is for Windows (setting: [flow] launch_adapter)" in res.message
    assert "cloud" not in res.message


def test_a_windows_adapter_on_windows_outside_the_cloud_is_ok(tmp_path):
    """REQ-072: the line of today is unchanged."""
    res = doctor.launch_adapter_result(adapter_project(tmp_path), platform="win32", cloud=False)
    assert res.status == "ok" and res.message == "auto_start on, the adapter is there"


def test_auto_start_off_is_ok_even_in_the_cloud(tmp_path):
    """REQ-072: answer 2."""
    root = adapter_project(tmp_path, "[flow]\nauto_start = false\n")
    res = doctor.launch_adapter_result(root, platform="linux", cloud=True)
    assert res.status == "ok" and res.message == "auto_start off"


def test_the_cloud_is_read_from_the_runtime_variable(tmp_path, monkeypatch):
    """REQ-072: answer 4; with the variable unset the session is treated as not cloud."""
    root = adapter_project(tmp_path)
    monkeypatch.setenv(doctor.REMOTE_RUNTIME, "true")
    assert "cloud session" in doctor.launch_adapter_result(root, platform="win32").message
    monkeypatch.delenv(doctor.REMOTE_RUNTIME)
    assert doctor.launch_adapter_result(root, platform="win32").status == "ok"


# --- review-ceiling -----------------------------------------------------------------------------


def test_reviews_under_builders_prints_the_difference(tmp_path):
    """REQ-072: answer 1, Q-1617-3; information only, no proposed value."""
    root = project(tmp_path, "[flow]\nmax_builders = 12\nreviews_in_flight = 9\n")
    res = doctor.review_ceiling_result(root)
    assert res.status == "fail"
    assert "3 builds may wait for a review" in res.message
    assert "reviews_in_flight" in res.message and "max_builders" in res.message
    assert doctor.CHECKS["review-ceiling"][0] == "warn"


def test_fixed_profile_sets_reviews_to_builders_and_is_quiet(tmp_path):
    """REQ-072: answer 2."""
    toml = '[flow]\nmax_builders = 12\nreviews_in_flight = 9\n[capacity]\nprofile = "fixed"\n'
    assert doctor.review_ceiling_result(project(tmp_path, toml)).status == "ok"


def test_reviews_above_builders_is_quiet(tmp_path):
    """REQ-072: answer 4."""
    root = project(tmp_path, "[flow]\nmax_builders = 2\nreviews_in_flight = 5\n")
    assert doctor.review_ceiling_result(root).status == "ok"


def test_a_bad_ceiling_is_refused_naming_the_setting(tmp_path):
    """REQ-072: answer 2."""
    res = doctor.review_ceiling_result(project(tmp_path, "[flow]\nreviews_in_flight = 0\n"))
    assert res.status == "fail" and "reviews_in_flight" in res.message


# --- slot-use -----------------------------------------------------------------------------------

ASSIGN = '[flow]\nbuilder_start = "assign"\nbuilder_slots = 3\n'


def marker(cid: int, slot: str, hours: float, decided: str = "#5") -> dict:
    at = (NOW - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = f"Slot: released {at} {slot} run{cid}\nlast run: {at} to {at}\ndecided: {decided}"
    return {"id": cid, "body": body}


def slot_reads(*markers: dict) -> Saved:
    return Saved(**{"conductor-issue": [{"number": 204}], "slot-markers-day": list(markers)})


def test_stale_and_idle_slots_warn(tmp_path):
    """REQ-072: answer 1; a marker over 24 hours old is stale, a `decided: none` run is idle."""
    reads = slot_reads(
        marker(1, "s1", 1, "none"), marker(2, "s2", 2), marker(3, "s3", 30), marker(4, "s1", 50)
    )
    res = doctor.slot_use_result(project(tmp_path, ASSIGN), reads, now=NOW)
    assert res.status == "fail"
    assert "stale: s3" in res.message
    assert "idle: 1 of 2 runs in the last 24 hours decided none" in res.message
    assert "(verify)" in res.message


def test_slots_that_ran_and_decided_are_ok(tmp_path):
    """REQ-072."""
    reads = slot_reads(marker(1, "s1", 1), marker(2, "s2", 2), marker(3, "s3", 3))
    assert doctor.slot_use_result(project(tmp_path, ASSIGN), reads, now=NOW).status == "ok"


def test_slot_use_reads_nothing_without_assign(tmp_path):
    """REQ-072: answer 2."""
    reads = slot_reads()
    res = doctor.slot_use_result(project(tmp_path, "[flow]\n"), reads, now=NOW)
    assert res.status == "ok" and res.message == " (builder_start is not assign)"
    assert reads.names == []


def test_a_bad_builder_start_is_refused_naming_the_setting(tmp_path):
    """REQ-072: answer 2."""
    res = doctor.slot_use_result(project(tmp_path, '[flow]\nbuilder_start = "x"\n'), slot_reads())
    assert res.status == "fail" and "builder_start" in res.message and '"x"' not in res.message


def test_markers_that_cannot_be_read_are_cannot_check(tmp_path):
    """REQ-072: answer 4."""
    root = project(tmp_path, ASSIGN)
    assert doctor.slot_use_result(root, Saved(), now=NOW).status == "cannot-check"


@pytest.mark.parametrize("check", ["tier-use", "launch-adapter", "review-ceiling", "slot-use"])
def test_each_row_is_a_warning_in_the_report(check):
    """REQ-072: answer 1; information only, never a failure of the run."""
    assert doctor.CHECKS[check][0] == "warn"


def test_saved_reads_print_the_same_bytes_on_every_run(tmp_path):
    """REQ-072: answer 4."""
    root = project(tmp_path, ASSIGN)
    first = doctor.slot_use_result(root, slot_reads(marker(1, "s1", 30)), now=NOW)
    again = doctor.slot_use_result(root, slot_reads(marker(1, "s1", 30)), now=NOW)
    assert first == again
