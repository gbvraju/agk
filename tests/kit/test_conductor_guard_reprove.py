"""The conductor guard admits `conductor.py reprove` (brief #2056 answers 1 and 9, ADR-0854).

REQ-057. Exactly `reprove --pr <n>`, with `--apply`, `--record` or `--record --apply` after it, the
project's own regular file or, in a clean project, the plugin's form; every other form, the shadow
mode and any `prepush.py` form stay denied. No test uses the network."""

from __future__ import annotations

import pytest
from test_conductor_guard_queue import RULE, reason, run_hook
from test_guard_plugin_forms import CLEAN, FLOW_ON, PLUGIN, allowed, decision, denied, make_project

SCRIPT = "scripts/agk/conductor.py"

ALLOWED = ["--pr 7", "--pr 7 --apply", "--pr 7 --record", "--pr 7 --record --apply"]

DENIED = [
    "",
    "--pr",
    "--pr x",
    "--pr 0",
    "--pr 7 8",
    "--pr 7 --force",
    "--pr 7 --apply --record",
    "--pr 7 --apply --apply",
    "--pr 7 --record --record",
    "--pr 7 --record --apply x",
    "--apply --pr 7",
    "--record --pr 7",
    "--pr 7 --apply; gh pr merge 7",
]


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    (root / "scripts" / "agk").mkdir(parents=True)
    (root / SCRIPT).write_text("print('the project script')\n", encoding="utf-8")
    (root / "scripts" / "agk" / "prepush.py").write_text("print(1)\n", encoding="utf-8")
    (root / ".git").mkdir()
    return root


@pytest.mark.parametrize("args", ALLOWED)
def test_req057_the_four_reprove_forms_are_allowed(project, args):
    """REQ-057: answer 1: the four forms of `reprove`, the project's own regular file."""
    result = run_hook(f"python3 {SCRIPT} reprove {args}", project)
    assert result.returncode == 0 and result.stdout == "", result.stdout


@pytest.mark.parametrize("args", DENIED)
def test_req057_every_other_reprove_form_is_denied_by_rule_6(project, args):
    """REQ-057: answer 1: any other option, order or a second number stays `BASH_RULE`."""
    assert reason(run_hook(f"python3 {SCRIPT} reprove {args}".rstrip(), project).stdout) == RULE


def test_req057_another_copy_of_the_script_is_denied(project, tmp_path):
    other = tmp_path / "elsewhere" / SCRIPT
    other.parent.mkdir(parents=True)
    other.write_text("print(1)\n", encoding="utf-8")
    assert reason(run_hook(f"python3 {other} reprove --pr 7 --apply", project).stdout) == RULE


def test_req057_a_linked_script_is_denied(project, tmp_path):
    (project / SCRIPT).unlink()
    other = tmp_path / "other.py"
    other.write_text("print(1)\n", encoding="utf-8")
    (project / SCRIPT).symlink_to(other)
    assert reason(run_hook(f"python3 {SCRIPT} reprove --pr 7", project).stdout) == RULE


@pytest.mark.parametrize("args", ALLOWED)
def test_req057_the_shadow_runs_no_reprove(project, args):
    """REQ-057: answer 1: not in shadow mode."""
    result = run_hook(f"python3 {SCRIPT} reprove {args}", project, shadow=True)
    assert reason(result.stdout) is not None


def test_req057_the_update_branch_put_stays_denied(project):
    """REQ-057: answer 1: the PUT is the script's own call, never the session's."""
    command = "gh api -X PUT repos/o/r/pulls/7/update-branch -f expected_head_sha=" + "a" * 40
    assert reason(run_hook(command, project).stdout) is not None


@pytest.mark.parametrize(
    "command",
    [
        "python3 scripts/agk/prepush.py --quick --record",
        "python3 scripts/agk/prepush.py --quick --record --body /tmp/body.md",
        "python3 scripts/agk/prepush.py",
    ],
)
def test_req057_the_guard_admits_no_prepush_form(project, command):
    """REQ-057: answer 9: the conductor never runs prepush.py from its session."""
    assert reason(run_hook(command, project).stdout) is not None


@pytest.mark.parametrize("args", ALLOWED)
def test_req057_the_plugin_form_of_reprove_is_admitted(tmp_path, args):
    """REQ-057: answer 6 (`[kit] layout = "plugin"`): the plugin's form passes (ADR-0631)."""
    root = make_project(tmp_path, CLEAN + FLOW_ON)
    found = decision("conductor_guard.py", root, f'python3 {PLUGIN}conductor.py" reprove {args}')
    assert allowed(found), found


def test_req057_the_plugin_form_keeps_the_refusals(tmp_path):
    root = make_project(tmp_path, CLEAN + FLOW_ON)
    for args in ("--pr 7 --force", "--apply --pr 7"):
        found = decision(
            "conductor_guard.py", root, f'python3 {PLUGIN}conductor.py" reprove {args}'
        )
        assert denied(found), args
