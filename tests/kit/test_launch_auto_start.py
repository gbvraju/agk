"""launch.py at the end of a review pass: the settings, the capacity and a refused adapter.

Brief #331, ADR-0190; REQ-041. The pass re-plans with `session.py plan --json`; with `[flow]
auto_start` off (the default) it prints the prompts, and with it on it calls the project's
`launch_adapter` once per session to start, never through a shell. `launch.py` refuses a plan that
starts more sessions than its capacity, or one brief twice, and reports a refused adapter once,
never retrying it. No test uses the network."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_launch import SCRIPT, adapter, calls, launch, plan, run_adapter  # noqa: F401

sys.path.insert(0, str(SCRIPT.parent))

import launch as launch_module  # noqa: E402
from common import CheckError  # noqa: E402


def capped(slots: object, *sessions: tuple[str, int, str]) -> dict:
    return plan(*sessions) | {"capacity": {"slots": slots, "max_builders": 3}}


# --- the settings (answer 2) --------------------------------------------------------------------


def write(root: Path, text: str) -> Path:
    (root / "agk.toml").write_text(f'default_branch = "main"\n{text}', encoding="utf-8")
    return root


def test_auto_start_is_off_and_no_adapter_is_set_by_default(tmp_path):
    """REQ-041: brief #331 answer 2 (`auto_start` defaults to false)."""
    assert launch_module.launch_settings(tmp_path) == (False, None)
    assert launch_module.launch_settings(write(tmp_path, "")) == (False, None)


def test_the_two_settings_of_the_flow_table_are_read(tmp_path):
    """REQ-041: brief #331 answer 2 (`auto_start` and `launch_adapter`)."""
    write(tmp_path, '[flow]\nauto_start = true\nlaunch_adapter = "scripts/start.sh --cloud"\n')
    assert launch_module.launch_settings(tmp_path) == (True, "scripts/start.sh --cloud")
    write(tmp_path, '[flow]\nlaunch_adapter = "scripts/start.sh"\n')
    assert launch_module.launch_settings(tmp_path) == (False, "scripts/start.sh")
    write(tmp_path, '[flow]\nauto_start = false\nlaunch_adapter = ""\n')
    assert launch_module.launch_settings(tmp_path) == (False, None)


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ('[flow]\nauto_start = "yes-secretvalue"\n', "auto_start"),
        ("[flow]\nauto_start = 1\n", "auto_start"),
        ('[flow]\nlaunch_adapter = ["secretvalue"]\n', "launch_adapter"),
        ('[flow]\nlaunch_adapter = "   "\n', "launch_adapter"),
        ("[flow\n", "agk.toml"),
    ],
)
def test_a_setting_of_the_wrong_kind_is_refused_naming_the_setting_never_its_value(
    tmp_path, text, name
):
    """REQ-041: brief #331 answer 2 (refusals name the setting, never a value)."""
    write(tmp_path, text)
    with pytest.raises(CheckError) as found:
        launch_module.launch_settings(tmp_path)
    assert name in str(found.value) and "secretvalue" not in str(found.value)


# --- the capacity (answer 4) --------------------------------------------------------------------


def test_a_plan_within_its_capacity_starts_each_session(tmp_path, adapter):  # noqa: F811
    """REQ-041: brief #331 answers 4 and 5 (capacity is respected)."""
    doc = capped(2, ("builder-a", 5, "t"), ("builder-b", 7, "u"))
    out = run_adapter(tmp_path, adapter, doc)
    assert out.returncode == 0, out.stderr
    assert [c["session"] for c in calls(tmp_path)] == ["builder-a", "builder-b"]


@pytest.mark.parametrize("stdin", [False, True])
def test_a_plan_that_starts_more_than_its_capacity_starts_nothing(tmp_path, adapter, stdin):  # noqa: F811
    """REQ-041: brief #331 answers 4 and 5 (never more than the plan's capacity)."""
    doc = capped(1, ("builder-a", 5, "t"), ("builder-b", 7, "u"))
    out = run_adapter(tmp_path, adapter, doc)
    assert out.returncode == 2 and "(field capacity)" in out.stderr
    assert calls(tmp_path) == []
    printed = launch(tmp_path, doc, stdin=stdin)
    assert printed.returncode == 2 and printed.stdout == ""


@pytest.mark.parametrize("slots", [-1, "2", None, True, 1.5])
def test_a_capacity_that_is_not_a_count_is_refused(tmp_path, slots):
    """REQ-041: brief #331 answer 4 (the capacity is a whole number)."""
    out = launch(tmp_path, capped(slots, ("builder-a", 5, "t")))
    assert out.returncode == 2 and "(field capacity)" in out.stderr


def test_a_plan_that_names_one_brief_or_one_session_twice_is_refused(tmp_path, adapter):  # noqa: F811
    """REQ-041: brief #331 answer 4 (never two sessions for one brief)."""
    out = run_adapter(tmp_path, adapter, plan(("builder-a", 5, "t"), ("builder-b", 5, "t")))
    assert out.returncode == 2 and "(field brief)" in out.stderr and calls(tmp_path) == []
    out = run_adapter(tmp_path, adapter, plan(("builder-a", 5, "t"), ("builder-a", 7, "t")))
    assert out.returncode == 2 and "(field session)" in out.stderr and calls(tmp_path) == []


def test_two_builds_of_one_brief_are_two_sessions(tmp_path):
    """REQ-041: brief #331 answer 4 (a brief built in parts may start two independent builds)."""
    doc = {
        "start": [
            {"session": "builder-a", "brief": 5, "build": "a"},
            {"session": "builder-b", "brief": 5, "build": "b"},
        ]
    }
    assert launch(tmp_path, doc).returncode == 0


# --- a refused adapter (answer 5) ---------------------------------------------------------------


def test_a_refused_adapter_is_reported_once_and_never_retried(tmp_path, adapter):  # noqa: F811
    """REQ-041: brief #331 answer 5 (a refused adapter is reported, not retried)."""
    doc = capped(2, ("builder-a", 5, "t"), ("builder-b", 7, "u"))
    out = run_adapter(tmp_path, adapter, doc, ADAPTER_FAIL="builder-a")
    assert out.returncode == 1
    assert [c["session"] for c in calls(tmp_path)] == ["builder-a"]
    assert "FAIL launch: the adapter failed for builder-a" in out.stderr
    assert "not started: builder-b #7" in out.stderr
    assert "refused" not in out.stderr and "started builder" not in out.stdout
