# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The evidence check reads a run that differs only by its worker count as the same run (brief
#2005, ADR-0829, REQ-051).

`prepush.without_workers` takes the worker part out of a test command (a trailing ` -n <n>`, or
the number in a filled `[testing] parallel_command`), `evidence.rebuild` compares the recorded and
the planned command through it, replays the planned command and notes `workers: <name> recorded
<r>, replayed <p>`. Anything else in the command still differs by `field: command`.
Invented data only (example.com); no network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - the fake git result only
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import evidence  # noqa: E402
import prepush  # noqa: E402

PY = ".venv/bin/python -m pytest -q tests/test_a.py"
TWO = {("whole", "whole"): f"{PY} -n 2"}
TEMPLATE = "make test-parallel JOBS={workers} SITE=https://example.com"


def tree(tmp_path: Path, parallel: str | None = None) -> Path:
    text = "[testing]\n" + (f'parallel_command = "{parallel}"\n' if parallel else "")
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def record(runs: list[dict]) -> dict:
    argv = ["python3", "scripts/agk/test_plan.py", "--json", "--base", "mb", "--head", "HEAD"]
    step = {"name": "tests", "argv": argv, "cwd": ".", "exit": 0, "outcome": "ok"}
    quick = all(item["set"] == "whole" for item in runs)  # a whole run only in a quick record
    step.update({"output_sha256": "0" * 64, "quick": quick, "runs": runs})
    return {"head": "a" * 40, "base": "b" * 40, "steps": [step]}


def run(name: str, command: str, set_: str = "whole") -> dict:
    return {"set": set_, "name": name, "command": command, "cwd": ".", "exit": 0}


@pytest.fixture
def rebuilt(monkeypatch):
    def go(root: Path, runs: list[dict], planned: dict) -> tuple[dict, list[str], list[str]]:
        done = subprocess.CompletedProcess([], 0, "mb\n", "")
        monkeypatch.setattr(evidence, "git", lambda *a: done)
        plan = {key: (command, root) for key, command in planned.items()}
        monkeypatch.setattr(evidence, "planned_runs", lambda *a: plan)
        return evidence.rebuild(root, record(runs), {}, 60)

    return go


def test_without_workers_takes_out_a_trailing_n(tmp_path):
    """REQ-051: answer 1 (the ` -n <digits>` that `pytest_workers` adds)."""
    root = tree(tmp_path)
    assert prepush.without_workers(f"{PY} -n 4", root) == PY
    assert prepush.without_workers(PY, root) == PY


@pytest.mark.parametrize("tail", [" -n auto", " -n 0", " -n 4 -x", " -n"])
def test_another_worker_form_is_left_as_written(tmp_path, tail):
    """REQ-051: answers 3 and 7 (`-n auto`, `-n 0`, `-n` in the middle are not the kit's form)."""
    root = tree(tmp_path)
    assert prepush.without_workers(PY + tail, root) == PY + tail


def test_a_filled_parallel_command_reads_as_its_template(tmp_path):
    """REQ-051: answers 1 and 6 (`parallel_command` with `{workers}` matches any number)."""
    root = tree(tmp_path, TEMPLATE)
    four, two = TEMPLATE.replace("{workers}", "4"), TEMPLATE.replace("{workers}", "2")
    assert prepush.without_workers(four, root) == prepush.without_workers(two, root) == TEMPLATE
    assert prepush.without_workers(four + " -k slow", root) == four + " -k slow"


def test_a_parallel_command_without_workers_is_compared_as_written(tmp_path):
    """REQ-051: answer 6 (without `{workers}` the command is compared as written)."""
    root = tree(tmp_path, "make test-parallel")
    assert prepush.without_workers("make test-parallel", root) == "make test-parallel"


def test_without_a_testing_table_only_the_trailing_n_is_read(tmp_path):
    """REQ-051: answer 6 (a project with no `[testing]` table: no template to read)."""
    assert prepush.without_workers(f"{PY} -n 3", tmp_path) == PY
    assert prepush.without_workers("make test", tmp_path) == "make test"


def test_whole_and_regression_runs_with_four_agree_with_a_plan_of_two(tmp_path, rebuilt):
    """REQ-051: answers 1, 2 and 9 (every planned set with another count; the replay is the
    plan's command and the note names the two counts)."""
    root = tree(tmp_path)
    for name, set_, label in [
        ("whole", "whole", "tests/whole/whole"),
        ("app", "regression", "tests/regression/app"),
        ("full", "proof", "tests/full"),
    ]:
        planned = {(set_, name): f"{PY} -n 2"}
        units, diffs, notes = rebuilt(root, [run(name, f"{PY} -n 4", set_)], planned)
        assert diffs == []
        assert units[label].command == f"{PY} -n 2"
        assert f"workers: {label} recorded 4, replayed 2" in notes


def test_a_single_run_agrees_with_a_plan_in_workers_and_the_reverse(tmp_path, rebuilt):
    """REQ-051: answers 3 and 7 (one machine had one worker or no xdist)."""
    root = tree(tmp_path)
    units, diffs, notes = rebuilt(root, [run("whole", PY)], {("whole", "whole"): f"{PY} -n 2"})
    assert diffs == [] and "workers: tests/whole/whole recorded 1, replayed 2" in notes
    units, diffs, notes = rebuilt(root, [run("whole", f"{PY} -n 2")], {("whole", "whole"): PY})
    assert diffs == [] and units["tests/whole/whole"].command == PY


def test_the_same_count_adds_no_note(tmp_path, rebuilt):
    """REQ-051: answer 2 (the note only where the counts differ)."""
    root = tree(tmp_path)
    _, diffs, notes = rebuilt(root, [run("whole", f"{PY} -n 2")], TWO)
    assert diffs == [] and not [n for n in notes if n.startswith("workers:")]


def test_filled_parallel_commands_with_four_and_two_agree(tmp_path, rebuilt):
    """REQ-051: answer 6 (`parallel_command` with `{workers}` filled on two machines)."""
    root = tree(tmp_path, TEMPLATE)
    four, two = TEMPLATE.replace("{workers}", "4"), TEMPLATE.replace("{workers}", "2")
    units, diffs, notes = rebuilt(root, [run("whole", four)], {("whole", "whole"): two})
    assert diffs == [] and units["tests/whole/whole"].command == two
    assert "workers: tests/whole/whole recorded 4, replayed 2" in notes


@pytest.mark.parametrize(
    "recorded",
    [
        ".venv/bin/python -m pytest -q tests/test_b.py -n 4",
        f"{PY} -n auto",
        ".venv/bin/python -m pytest -n 4 -q tests/test_a.py",
        "python3 -m pytest -q tests/test_a.py -n 4",
        f"{PY} -x -n 4",
    ],
)
def test_anything_else_still_differs_by_command(tmp_path, rebuilt, recorded):
    """REQ-051: answer 3 (another file, option, interpreter or worker form still differs)."""
    root = tree(tmp_path)
    units, diffs, notes = rebuilt(root, [run("whole", recorded)], TWO)
    assert diffs == ["not what prepush runs: tests/whole/whole (field: command)"]
    assert "tests/whole/whole" not in units
    assert not [n for n in notes if n.startswith("workers:")]
