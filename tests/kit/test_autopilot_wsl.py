"""Inside WSL, `agk autopilot on` installs one Windows task that runs signed out (brief #1448,
ADR-0606).

REQ-071. Criterion: `on` inside a WSL double registers one task through `schtasks.exe`, never a
crontab line; the task runs whether or not the person is signed in, with the stored sign-in asked by
Windows itself (never this script); a declined sign-in leaves a signed-in-only task and a warning
naming the setting; interop off refuses naming `[interop] enabled`; `off` removes that task by name
only; a native Linux machine keeps its crontab line; `/agk:wsl` hands its watchdog step to
`autopilot.py on` when `[autopilot]` is set and keeps today's task otherwise. A stub `schtasks.exe`,
a fake `/proc/version` and `/etc/wsl.conf`, a fake clock; invented names (example.com).
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_autopilot_settings import ADAPTER, project  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PS1 = ROOT / "scripts" / "agk" / "wsl_setup.ps1"
NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
ON = ADAPTER + '[autopilot]\nmode = "on"\ninterval_minutes = 7\n'
KERNEL = "Linux version 6.6.0-microsoft-standard-WSL2 (example@example.com)\n"


class Windows:
    """`schtasks.exe`, `whoami.exe` and `crontab` of a WSL machine; every call is kept."""

    def __init__(self, signed_out: int = 0):
        self.calls, self.shown, self.signed_out = [], [], signed_out

    def __call__(self, argv, given=None):
        self.calls.append(list(argv))
        if argv == ["whoami.exe"]:
            return 0, "example-pc\\member-example-1\r\n"
        return (0, "") if argv[0] == "schtasks.exe" else (1, "crontab: not expected\n")

    def run_shown(self, argv):
        self.shown.append(list(argv))
        return self.signed_out


@pytest.fixture
def wsl(tmp_path, monkeypatch):
    import autopilot
    import conductor

    version, conf = tmp_path / "version", tmp_path / "wsl.conf"
    version.write_text(KERNEL, encoding="utf-8")
    found = Windows()
    monkeypatch.setattr(autopilot, "PLATFORM", "linux")
    monkeypatch.setattr(autopilot, "PROC_VERSION", version)
    monkeypatch.setattr(autopilot, "WSL_CONF", conf)
    monkeypatch.setattr(autopilot, "run_command", found)
    monkeypatch.setattr(autopilot, "run_shown", found.run_shown)
    monkeypatch.setattr(conductor, "memory_line", lambda root: ("watchdog: memory 16 GB", True))
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-example")
    found.conf = conf
    return found


def test_on_in_wsl_registers_one_signed_out_task_and_no_crontab(tmp_path, wsl, capsys):
    """REQ-071: answers 1 and 2 (one task through `schtasks.exe`; Windows asks the sign-in)."""
    import autopilot

    root = project(tmp_path, ON)
    assert autopilot.main(["on", "--root", str(root)], now=NOW) == 0
    assert not [c for c in wsl.calls if c[0] == "crontab"]
    (call,) = wsl.shown
    assert call[:6] == ["schtasks.exe", "/Create", "/SC", "MINUTE", "/MO", "7"]
    assert call[call.index("/TN") + 1] == autopilot.WSL_TASK == "agk-autopilot (WSL)"
    assert call[-4:] == ["/RU", "example-pc\\member-example-1", "/RP", "*"]  # Windows prompts
    run = call[call.index("/TR") + 1]
    assert run.startswith(f"wsl.exe -d Ubuntu-example --cd {root.resolve()} -- bash -lc ")
    assert '"git fetch -q origin && python3 scripts/agk/conductor.py watchdog --pass"' in run
    out = capsys.readouterr().out
    assert "schtasks.exe /Create" in out and "warn: runs only" not in out
    assert "ok: the task runs whether or not you are signed in" in out
    assert "cron entry" not in out


def test_a_second_on_replaces_the_one_task(tmp_path, wsl):
    """REQ-071: answer 6 (a second `on`: no second task)."""
    import autopilot

    root = project(tmp_path, ON)
    autopilot.main(["on", "--root", str(root)], now=NOW)
    autopilot.main(["on", "--root", str(root)], now=NOW)
    names = {c[c.index("/TN") + 1] for c in wsl.shown}
    assert names == {autopilot.WSL_TASK} and all("/F" in c for c in wsl.shown)


def test_a_declined_sign_in_registers_signed_in_only_and_warns(tmp_path, wsl, capsys):
    """REQ-071: answer 2 (the person declines the signed-out option)."""
    import autopilot

    wsl.signed_out = 1
    root = project(tmp_path, ON)
    assert autopilot.main(["on", "--root", str(root)], now=NOW) == 0
    made = [c for c in wsl.calls if c[:2] == ["schtasks.exe", "/Create"]]
    assert len(made) == 1 and "/RU" not in made[0] and "/RP" not in made[0]
    out = capsys.readouterr().out
    assert "warn: runs only while you are signed in (setting: the task's sign-in option)" in out


@pytest.mark.parametrize("conf", ["[interop]\nenabled = false\n", "[interop]\nenabled=False\n"])
def test_interop_off_refuses_and_writes_nothing(tmp_path, wsl, capsys, conf):
    """REQ-071: answer 4 (one line naming the setting, no task, no crontab)."""
    import autopilot

    wsl.conf.write_text(conf, encoding="utf-8")
    root = project(tmp_path, ON)
    assert autopilot.main(["on", "--root", str(root)], now=NOW) == 1
    assert wsl.shown == [] and not [c for c in wsl.calls if c[0] in ("schtasks.exe", "crontab")]
    assert "(setting: [interop] enabled in /etc/wsl.conf)" in capsys.readouterr().out


def test_off_after_a_wsl_on_removes_that_task_only(tmp_path, wsl):
    """REQ-071: answer 1 (`off` removes the task by name and nothing else)."""
    import autopilot

    root = project(tmp_path, ON)
    autopilot.main(["on", "--root", str(root)], now=NOW)
    wsl.calls.clear()
    assert autopilot.main(["off", "--root", str(root)], now=NOW) == 0
    assert wsl.calls == [["schtasks.exe", "/Delete", "/TN", autopilot.WSL_TASK, "/F"]]


def test_a_native_linux_machine_still_gets_its_crontab_line(tmp_path, wsl, monkeypatch):
    """REQ-071: answer 5 (native Linux unchanged)."""
    import autopilot

    Path(autopilot.PROC_VERSION).write_text("Linux version 6.6.0-generic\n", encoding="utf-8")
    monkeypatch.setattr(autopilot, "run_command", lambda argv, given=None: (0, ""))
    root = project(tmp_path, ON)
    assert not autopilot.inside_wsl()
    assert autopilot.entry_line(root, 7).endswith(autopilot.ENTRY_TAG)
    assert autopilot.main(["on", "--root", str(root)], now=NOW) == 0
    assert wsl.shown == []


def ps1_function(name: str) -> str:
    text = PS1.read_text(encoding="utf-8")
    start = text.index(f"function {name}")
    return text[start : text.index("\n}\n", start)]


def test_agk_wsl_hands_its_watchdog_step_to_autopilot_on():
    """REQ-071: answer 3 (with `[autopilot]` on the default branch, `autopilot.py on` in WSL;
    the older task disabled, never deleted; without it, today's task kept)."""
    probe = ps1_function("Test-AutopilotSet")
    assert "origin/HEAD:agk.toml" in probe and r"^\[autopilot\]" in probe
    step = ps1_function("Set-WslWatchdog")
    hand, today = step.split("Register-ScheduledTask", 1)[0], step
    assert "if (Test-AutopilotSet)" in hand and "scripts/agk/autopilot.py on" in hand
    assert re.search(r"Disable-ScheduledTask -TaskName \$old", hand)
    assert "Unregister-ScheduledTask" not in step
    assert "Register-ScheduledTask -TaskName $WslTask" in today  # without [autopilot]
    assert "Test-AutopilotSet" in ps1_function("Test-WslTasks")
