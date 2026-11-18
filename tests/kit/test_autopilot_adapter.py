"""With the autopilot on, the launch adapter lives in its own table (brief #1480, ADR-0628).

REQ-071. Follow-up to Q-1451-2 (b): `[autopilot] adapter` names the launch adapter, in the
command form `[flow] launch_adapter` takes. With `[autopilot]` set, `autopilot.py` (`on`'s machine
check and `agk next`'s start) reads it and never `[flow] launch_adapter`; with no table, today's
setting decides. `doctor.py` `autopilot-settings` still names `launch_adapter` as replaced and its
fix names `[autopilot] adapter`; `model-names` warns when the autopilot is on with an adapter and
`[models.names]` is unset. Saved trees, a stub adapter and a fake clock only; invented data
(`cb-example-1`, `example.com`); no network.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import autopilot  # noqa: E402
import conductor  # noqa: E402
import doctor  # noqa: E402
import launch  # noqa: E402
import personal_state as ps  # noqa: E402
from common import CheckError  # noqa: E402
from forge import FilesForge  # noqa: E402

import config  # noqa: E402

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
RUNS = f"{sys.executable} -c pass"


def project(tmp_path: Path, toml: str) -> Path:
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed list
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    return root


# --- answer 1: the key ------------------------------------------------------------------------


def test_the_adapter_is_read_from_the_autopilot_table(tmp_path):
    """REQ-071: `[autopilot] adapter` is read; unset is None, as with no table."""
    root = project(tmp_path, f'[autopilot]\nmode = "on"\nadapter = "{RUNS}"\n')
    assert config.autopilot_settings(root)["adapter"] == RUNS
    assert config.autopilot_settings(project(tmp_path / "b", "[autopilot]\n"))["adapter"] is None
    assert config.autopilot_settings(project(tmp_path / "c", ""))["adapter"] is None


@pytest.mark.parametrize("value", ["3", "true", "[\"turbo-secret\"]", '"   "'])
def test_a_wrong_kind_of_adapter_is_refused_naming_the_key(tmp_path, value):
    """REQ-071: a non-string or blank adapter is refused naming the key, never the value."""
    root = project(tmp_path, f"[autopilot]\nadapter = {value}\n")
    with pytest.raises(CheckError) as err:
        config.autopilot_settings(root)
    said = str(err.value)
    assert "adapter of the autopilot table" in said and "autopilot.adapter" in said
    assert "turbo-secret" not in said


# --- answer 2: who reads it -------------------------------------------------------------------


@pytest.mark.parametrize(
    "toml, found",
    [
        (f'[autopilot]\nadapter = "{RUNS}"\n', (RUNS, "autopilot.adapter")),
        (f'[flow]\nlaunch_adapter = "x-old"\n[autopilot]\nadapter = "{RUNS}"\n',
         (RUNS, "autopilot.adapter")),
        ('[flow]\nlaunch_adapter = "x-old"\n[autopilot]\n', (None, "autopilot.adapter")),
        ('[flow]\nlaunch_adapter = "x-old"\n', ("x-old", "flow.launch_adapter")),
        ("", (None, "flow.launch_adapter")),
    ],
)  # fmt: skip
def test_the_autopilot_table_decides_the_adapter_when_set(tmp_path, toml, found):
    """REQ-071: with `[autopilot]` its adapter, never `[flow] launch_adapter`; else today's."""
    assert launch.autopilot_adapter(project(tmp_path, toml)) == found


def test_the_machine_check_reads_the_autopilot_adapter(tmp_path, monkeypatch):
    """REQ-071: `on`'s check passes with `[autopilot] adapter` alone and warns naming
    `autopilot.adapter` when the table has none, even beside `[flow] launch_adapter`."""
    monkeypatch.setattr(autopilot, "run_command", lambda argv, given=None: (0, "masked\n"))
    monkeypatch.setattr(conductor, "memory_line", lambda root: ("watchdog: memory 16 GB", True))
    good = project(tmp_path, f'[autopilot]\nmode = "on"\nadapter = "{RUNS}"\n')
    assert "ok: the adapter is set and runs" in autopilot.machine_checks(good)
    bare = project(tmp_path / "b", f'[flow]\nlaunch_adapter = "{RUNS}"\n[autopilot]\n')
    lines = autopilot.machine_checks(bare)
    assert "warn: the adapter is unset or does not run (setting: autopilot.adapter)" in lines


# --- answer 6: a pass starts a job, or names the setting --------------------------------------

ADAPTER = """import os, pathlib, sys
sys.stdin.read()
w = pathlib.Path.cwd().resolve().parent / ("agk-" + os.environ["AGK_SESSION"])
w.mkdir(exist_ok=True)
(w / ".agk-session-pid").write_text("session=%s\\npid=1\\nstarted_utc=2026-11-16T12:00:00Z\\n"
    "brief=%s\\nkind=%s\\nitem=%s\\n" % (os.environ["AGK_SESSION"], os.environ.get("AGK_BRIEF", ""),
    os.environ["AGK_JOB_KIND"], os.environ["AGK_ITEM"]))
(w / ".agk-session-exit").write_text("exit_code=0\\nended_utc=2026-11-16T12:05:00Z\\n")
"""


def at(minutes: int) -> str:
    return (NOW + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def sidecar_with(tmp_path: Path, monkeypatch, table: str) -> tuple[Path, int, int]:
    """A sidecar with one fix job due and TABLE appended to its agk.toml."""
    path = tmp_path / "sidecar"
    ps.make_sidecar(path, "demo-dev")
    adapter = tmp_path / "adapter.py"
    adapter.write_text(ADAPTER, encoding="utf-8")
    command = f"{sys.executable} {adapter}"
    with (path / "agk.toml").open("a", encoding="utf-8") as out:
        out.write("\n" + table.replace("ADAPTER", command))
    gh = tmp_path / "bin" / "gh"  # a `gh` that only records that it was called
    gh.parent.mkdir()
    gh.write_text(f"#!/bin/sh\necho called >> {tmp_path / 'gh.log'}\nexit 1\n", encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{gh.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(autopilot, "SLEEP", lambda s: None)
    files = FilesForge(path, env={})
    number = files.create_issue("A page", "Size: S", ["agk-brief"])
    pull = files.record_pull("A page", f"Brief: #{number}", "a" * 40, "feature", "main")
    files.comment(pull, "Report: aaaaaaa ready for review")
    files.comment(pull, "Verdict: fix list aaaaaaa")
    saved = path / "forge" / f"comments-{pull}.json"
    data = json.loads(saved.read_text(encoding="utf-8"))
    data[0]["created_at"], data[1]["created_at"] = at(-120), at(-60)
    saved.write_text(json.dumps(data), encoding="utf-8")
    return path, number, pull


def test_a_pass_starts_a_job_through_the_autopilot_adapter(tmp_path, monkeypatch, capsys):
    """REQ-071: `[autopilot]` with `adapter` and no `[flow] launch_adapter` starts the job."""
    root, number, pull = sidecar_with(tmp_path, monkeypatch, '[autopilot]\nmode = "on"\n'
                                      'adapter = "ADAPTER"\n')  # fmt: skip
    assert autopilot.main(["next", "--root", str(root)], NOW) == 0
    out = capsys.readouterr().out
    assert f"next: fix #{pull} cb{number}" in out and f"next: cb{number} ended (exit 0)" in out


def test_a_pass_uses_the_autopilot_adapter_beside_the_old_one(tmp_path, monkeypatch, capsys):
    """REQ-071: with both set the pass uses `[autopilot] adapter`, never `launch_adapter`."""
    table = '[flow]\nlaunch_adapter = "no-such-adapter-example"\n[autopilot]\nmode = "on"\n'
    root, number, _ = sidecar_with(tmp_path, monkeypatch, table + 'adapter = "ADAPTER"\n')
    assert autopilot.main(["next", "--root", str(root)], NOW) == 0
    assert f"next: cb{number} ended (exit 0)" in capsys.readouterr().out


def test_a_pass_without_the_autopilot_adapter_names_its_key(tmp_path, monkeypatch, capsys):
    """REQ-071: `[autopilot]` with neither adapter starts nothing, naming `autopilot.adapter`."""
    root, _, _ = sidecar_with(tmp_path, monkeypatch, '[autopilot]\nmode = "on"\n')
    assert autopilot.main(["next", "--root", str(root)], NOW) == 2
    out = capsys.readouterr().out
    assert "next: nothing started (setting: autopilot.adapter)" in out
    assert not list(tmp_path.glob("agk-*"))


def test_without_the_table_the_pass_reads_the_flow_adapter(tmp_path, monkeypatch, capsys):
    """REQ-071: no `[autopilot]` table: today's `[flow] launch_adapter`, for one release."""
    root, number, _ = sidecar_with(tmp_path, monkeypatch, '[flow]\nlaunch_adapter = "ADAPTER"\n')
    assert autopilot.main(["next", "--root", str(root)], NOW) == 0
    assert f"next: cb{number} ended (exit 0)" in capsys.readouterr().out


# --- answers 3 and 4: the health check --------------------------------------------------------


def test_the_doctor_passes_with_the_autopilot_adapter_alone(tmp_path):
    """REQ-071: `[autopilot]` with `adapter` and no old setting passes `autopilot-settings`."""
    root = project(tmp_path, f'[autopilot]\nmode = "on"\nadapter = "{RUNS}"\n')
    assert doctor.autopilot_settings_result(root).status == "ok"


def test_the_doctor_names_launch_adapter_beside_the_table_and_fixes_to_the_new_key(tmp_path):
    """REQ-071: both set fails naming `launch_adapter`; the fix names `[autopilot] adapter`."""
    toml = f'[flow]\nlaunch_adapter = "{RUNS}"\n[autopilot]\nadapter = "{RUNS}"\n'
    found = doctor.autopilot_settings_result(project(tmp_path, toml))
    assert found.status == "fail"
    assert "launch_adapter (not read: [autopilot] is set)" in found.message
    assert RUNS not in found.message
    assert "[autopilot] adapter" in doctor.CHECKS["autopilot-settings"][3]


@pytest.mark.parametrize(
    "toml, status",
    [
        (f'[autopilot]\nmode = "on"\nadapter = "{RUNS}"\n', "fail"),
        (f'[autopilot]\nmode = "on"\nadapter = "{RUNS}"\n[models.names]\nstrongest = "m-example"\n'
         'mid = "m-example"\nfast = "m-example"\n', "ok"),
        (f'[autopilot]\nmode = "off"\nadapter = "{RUNS}"\n', "ok"),
        ('[autopilot]\nmode = "on"\n', "ok"),
    ],
)  # fmt: skip
def test_model_names_warn_when_the_autopilot_is_on_with_an_adapter(tmp_path, toml, status):
    """REQ-071: the autopilot on with `[autopilot] adapter` and no `[models.names]` warns."""
    assert doctor.model_names_result(project(tmp_path, toml)).status == status


# --- answer 7: the guide ----------------------------------------------------------------------


def test_the_guide_names_the_autopilot_adapter():
    """REQ-071: getting-started names `[autopilot] adapter` beside `agk autopilot on`."""
    text = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    line = next(x for x in text.splitlines() if "agk autopilot on" in x and "scheduler" in x)
    assert "[autopilot] adapter" in line
