"""One autopilot setting, one command and a relaxed budget (brief #1390, ADR-0587).

REQ-071. SPEC-0064 build (d), rules 7, 8 and 11. `[autopilot] mode` is `off`, `assist` or `on`
(`assist` when the table has no `mode`; today's settings while the table is absent), refused naming
the setting; `daily_budget` is absent or `"off"` by default and limits nothing; a figure reached
stops new build and fix jobs only, and `autopilot.py budget off [--today]` relaxes it in the git
directory. `autopilot.py on|off` installs or removes the one scheduler entry and runs the machine
checks, which warn naming the setting and change no power setting; `agk doctor` warns
`autopilot-settings` while the old settings are set. The scheduler, `gh`, the adapter, the memory,
the spend and the clock are test doubles; data is invented (`example.com`, `cb-example-1`).
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
KINDS = ("review", "build", "fix", "steward", "conductor")


def project(tmp_path, toml: str = ""):
    root = tmp_path / "proj"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # nosec B603 B607 - fixed list
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    return root


def tracked_changes(root) -> str:
    done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    return done.stdout


class Machine:
    """The commands a machine answers: a crontab, `gh`, the sleep state; every call is kept."""

    def __init__(self, crontab: str = "", gh: int = 0, sleep: str = "masked"):
        self.crontab, self.gh, self.sleep, self.calls = crontab, gh, sleep, []
        self.read = (0, "")  # (code, error output) of `crontab -l` when it fails

    def __call__(self, argv, given=None):
        self.calls.append(list(argv))
        if argv[:2] == ["crontab", "-l"]:
            return self.read if self.read[0] else (0, self.crontab)
        if argv == ["crontab", "-"]:
            self.crontab = given
            return 0, ""
        if argv[:2] == ["gh", "auth"]:
            return self.gh, ""
        if argv[:1] == ["systemctl"]:
            return 0, self.sleep + "\n"
        return 0, ""


@pytest.fixture
def machine(monkeypatch):
    import autopilot
    import conductor

    found = Machine()
    monkeypatch.setattr(autopilot, "run_command", found)
    monkeypatch.setattr(conductor, "memory_line", lambda root: ("watchdog: memory 16 GB", True))
    monkeypatch.setattr(autopilot, "day_spend", lambda root, day: 1000)
    monkeypatch.setattr(autopilot, "PROC_VERSION", Path("/nonexistent/agk-example"))  # not WSL
    return found


ON = '[autopilot]\nmode = "on"\n'
ADAPTER = f'[flow]\nlaunch_adapter = "{sys.executable} -c pass"\n'


# --- rule 7: the setting ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "toml, mode",
    [
        ("", None),
        ("[autopilot]\n", "assist"),
        ('[autopilot]\nmode = "off"\n', "off"),
        ('[autopilot]\nmode = "assist"\n', "assist"),
        ('[autopilot]\nmode = "on"\n', "on"),
    ],
)
def test_the_mode_is_read_with_assist_when_unset_and_none_without_the_table(tmp_path, toml, mode):
    """REQ-071 AC5: rule 7 (Q-S0064-2: assist for a new table; no table keeps today's settings)."""
    import config

    found = config.autopilot_settings(project(tmp_path, toml))
    assert found["mode"] == mode and found["interval_minutes"] == 5
    assert found["daily_budget"] is None


@pytest.mark.parametrize(
    "toml, setting",
    [
        ('[autopilot]\nmode = "turbo-secret"\n', "autopilot.mode"),
        ('[autopilot]\nmode = "turbo-secret"\nshow_jobs = 3\n', "autopilot.mode"),
        ("[autopilot]\ninterval_minutes = 0\n", "autopilot.interval_minutes"),
        ('[autopilot]\ndaily_budget = "turbo-secret"\n', "autopilot.daily_budget"),
        ("[autopilot]\ndaily_budget = 0\n", "autopilot.daily_budget"),
        ("[autopilot]\ndaily_budget = true\n", "autopilot.daily_budget"),
        ('[autopilot]\ncolour = "turbo-secret"\n', "autopilot.colour"),
        ('autopilot = "turbo-secret"\n', "autopilot"),
    ],
)
def test_another_value_is_refused_naming_the_setting_never_the_value(tmp_path, toml, setting):
    """REQ-071 AC5: rule 7 (refused naming the setting)."""
    import config

    with pytest.raises(config.AutopilotSettingError) as caught:
        config.autopilot_settings(project(tmp_path, toml))
    assert f"(setting: {setting})" in str(caught.value)
    assert "turbo-secret" not in str(caught.value)


def test_the_budget_is_a_whole_number_of_tokens_or_off(tmp_path):
    """REQ-071 AC6: rule 8 (absent or "off" is no limit)."""
    import config

    assert config.autopilot_settings(project(tmp_path, '[autopilot]\ndaily_budget = "off"\n'))[
        "daily_budget"
    ] is None  # fmt: skip
    other = tmp_path / "other"
    other.mkdir()
    assert config.autopilot_settings(project(other, "[autopilot]\ndaily_budget = 50000\n"))[
        "daily_budget"
    ] == 50000  # fmt: skip


@pytest.mark.parametrize(
    "mode, allowed",
    [
        ("off", set()),
        ("assist", {"review", "steward", "conductor"}),
        ("on", set(KINDS)),
        (None, set(KINDS)),  # no table: today's settings decide, as before this build
    ],
)
def test_off_starts_nothing_assist_needs_the_yes_for_a_builder_on_starts_all(mode, allowed):
    """REQ-071 AC5: rule 7 (Q-S0064-8: in assist only the owner's recorded yes starts a builder)."""
    import autopilot

    assert {k for k in KINDS if autopilot.mode_allows(mode, k)} == allowed
    assert autopilot.mode_allows("assist", "build", owner_yes=True)
    assert not autopilot.mode_allows("off", "build", owner_yes=True)


def test_off_prints_the_commands_a_person_would_run(tmp_path, machine, monkeypatch, capsys):
    """REQ-071 AC5: rule 7 (`off`: nothing starts by itself; the commands are printed)."""
    import autopilot

    root = project(tmp_path, '[autopilot]\nmode = "off"\n')
    monkeypatch.setattr(autopilot, "status", lambda root: 0)
    assert autopilot.main(["status", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "autopilot: mode off; nothing starts by itself" in out
    assert "python3 scripts/agk/conductor.py watchdog --pass" in out


def test_the_old_settings_are_named_while_no_autopilot_table_is_set(tmp_path):
    """REQ-071 AC5: rule 7 (read for one release; doctor's `autopilot-settings` names them)."""
    import doctor

    import config

    root = project(tmp_path, '[flow]\nauto_start = true\nlaunch_adapter = "x"\n[capacity]\n')
    assert config.autopilot_settings(root)["legacy"] == ["auto_start", "launch_adapter", "capacity"]
    found = doctor.autopilot_settings_result(root)
    assert found.status == "fail"
    assert "auto_start" in found.message and "[capacity]" in found.message
    assert '"x"' not in found.message and doctor.CHECKS["autopilot-settings"][0] == "warn"
    quiet = tmp_path / "quiet"
    quiet.mkdir()
    assert doctor.autopilot_settings_result(
        project(quiet, '[autopilot]\nmode = "on"\n')
    ).status == ("ok")


# --- rule 8: the budget -----------------------------------------------------------------------


def test_with_no_budget_nothing_is_stopped_and_the_spend_is_shown(tmp_path, machine):
    """REQ-071 AC6: rule 8 (the default limits nothing; the day's spend still shows)."""
    import autopilot

    root = project(tmp_path, '[autopilot]\nmode = "on"\n')
    for kind in KINDS:
        assert autopilot.job_allowed(root, kind, NOW)[0]
    assert autopilot.budget_line(root, NOW) == "budget: off; spend 2026-11-16: 1000 tokens"


def test_a_reached_budget_stops_build_and_fix_only_and_says_so_once(tmp_path, machine, monkeypatch):
    """REQ-071 AC6: rule 8 (review and owner-answer jobs still run; the owner is told once)."""
    import autopilot

    root = project(tmp_path, '[autopilot]\nmode = "on"\ndaily_budget = 1000\n')
    allowed = {k: autopilot.job_allowed(root, k, NOW) for k in KINDS}
    assert {k for k, (ok, _) in allowed.items() if ok} == {"review", "steward", "conductor"}
    assert "budget reached (setting: autopilot.daily_budget)" in allowed["build"][1]
    assert autopilot.budget_note(root, NOW) and not autopilot.budget_note(root, NOW)
    assert autopilot.budget_note(root, NOW + timedelta(days=1))  # a new UTC day tells again
    monkeypatch.setattr(autopilot, "day_spend", lambda root, day: 999)
    assert autopilot.job_allowed(root, "build", NOW)[0]


def test_an_unreadable_spend_is_unknown_never_zero_and_stops_a_set_budget(
    tmp_path, machine, monkeypatch
):
    """REQ-071 AC6: rule 8 (Q-S0064-6: unknown stops new build jobs only while a figure is set)."""
    import autopilot

    monkeypatch.setattr(autopilot, "day_spend", lambda root, day: None)
    root = project(tmp_path, ON + "daily_budget = 1000\n")
    assert "spend 2026-11-16: unknown" in autopilot.budget_line(root, NOW)
    assert " 0 tokens" not in autopilot.budget_line(root, NOW)
    assert not autopilot.job_allowed(root, "fix", NOW)[0]
    assert autopilot.job_allowed(root, "review", NOW)[0]


def test_budget_off_relaxes_at_once_and_today_ends_with_the_utc_day(tmp_path, machine, capsys):
    """REQ-071 AC6: rule 8 (kept in the git directory; no tracked file changes)."""
    import autopilot

    root = project(tmp_path, ON + "daily_budget = 1000\n")
    before = tracked_changes(root)
    assert autopilot.main(["budget", "off", "--today", "--root", str(root)], now=NOW) == 0
    assert autopilot.job_allowed(root, "build", NOW)[0]
    assert "relaxed for 2026-11-16" in autopilot.budget_line(root, NOW)
    assert not autopilot.job_allowed(root, "build", NOW + timedelta(days=1))[0]
    assert autopilot.main(["budget", "off", "--root", str(root)], now=NOW) == 0
    assert autopilot.job_allowed(root, "build", NOW + timedelta(days=9))[0]
    assert "relaxed until set again" in autopilot.budget_line(root, NOW)
    assert autopilot.main(["budget", "on", "--root", str(root)], now=NOW) == 0
    assert not autopilot.job_allowed(root, "build", NOW)[0]
    assert tracked_changes(root) == before
    assert (root / ".git" / "agk" / "autopilot.json").is_file()


# --- rules 7 and 11: the command and the machine checks ---------------------------------------


def test_on_installs_one_entry_and_edits_no_tracked_file(tmp_path, machine, capsys, monkeypatch):
    """REQ-071 AC5: rule 7 (one command, no file edit; the protected mode change is printed)."""
    import autopilot

    monkeypatch.setattr(autopilot, "PLATFORM", "linux")
    root = project(tmp_path, ADAPTER)
    machine.crontab = "0 1 * * * echo kept-example\n"
    before = tracked_changes(root)
    assert autopilot.main(["on", "--root", str(root)], now=NOW) == 0
    assert autopilot.main(["on", "--root", str(root)], now=NOW) == 0
    lines = machine.crontab.splitlines()
    assert lines[0] == "0 1 * * * echo kept-example"
    ours = [x for x in lines if x.endswith(autopilot.ENTRY_TAG)]
    assert len(ours) == 1 and ours[0].startswith("*/5 * * * * ")
    assert "conductor.py watchdog --pass" in ours[0]
    out = capsys.readouterr().out
    assert 'mode = "on"' in out and "ADR" in out  # printed, never written
    assert tracked_changes(root) == before
    assert autopilot.main(["off", "--root", str(root)], now=NOW) == 0
    assert machine.crontab.splitlines() == ["0 1 * * * echo kept-example"]


@pytest.mark.parametrize(
    "answer, written",
    [
        ((1, "no crontab for cb-example-1\n"), True),  # no crontab yet: an empty one
        ((1, "crontab: cannot open the spool (permission denied)\n"), False),
        ((127, ""), False),  # crontab does not run
    ],
)
def test_a_failed_crontab_read_writes_nothing_but_no_crontab_is_empty(
    tmp_path, machine, monkeypatch, capsys, answer, written
):
    """REQ-071 AC5: rule 7 (a failed read never wipes the person's other entries)."""
    import autopilot

    monkeypatch.setattr(autopilot, "PLATFORM", "linux")
    root = project(tmp_path, ADAPTER)
    machine.crontab, machine.read = "0 1 * * * echo kept-example\n", answer
    code = autopilot.main(["on", "--root", str(root)], now=NOW)
    wrote = ["crontab", "-"] in machine.calls
    assert wrote is written and code == (0 if written else 1)
    if written:
        assert machine.crontab.endswith(autopilot.ENTRY_TAG + "\n")
        assert "kept-example" not in machine.crontab  # the double's empty crontab was read
    else:
        assert machine.crontab == "0 1 * * * echo kept-example\n"
        assert "(setting: crontab)" in capsys.readouterr().out


def test_on_and_off_on_windows_use_one_named_task(tmp_path, machine, monkeypatch):
    """REQ-071 AC5: rule 7 (the Windows Task Scheduler entry, created and removed by name)."""
    import autopilot

    monkeypatch.setattr(autopilot, "PLATFORM", "win32")
    root = project(tmp_path, ADAPTER + '[autopilot]\nmode = "assist"\ninterval_minutes = 7\n')
    autopilot.main(["on", "--root", str(root)], now=NOW)
    autopilot.main(["off", "--root", str(root)], now=NOW)
    made = [c for c in machine.calls if c[:1] == ["schtasks"]]
    assert made[0][:6] == ["schtasks", "/Create", "/SC", "MINUTE", "/MO", "7"]
    assert autopilot.TASK_NAME in made[0] and made[1][:2] == ["schtasks", "/Delete"]


def test_the_machine_checks_warn_naming_the_setting(tmp_path, machine, monkeypatch, capsys):
    """REQ-071 AC7: rule 11 (gh, the adapter, memory, sleep; each warning names its setting)."""
    import autopilot
    import conductor

    monkeypatch.setattr(autopilot, "PLATFORM", "linux")
    machine.gh, machine.sleep = 1, "enabled"
    monkeypatch.setattr(conductor, "memory_line", lambda root: ("watchdog: memory 1 GB", False))
    root = project(tmp_path, '[flow]\nlaunch_adapter = "no-such-adapter-example"\n')
    warnings = [x for x in autopilot.machine_checks(root) if x.startswith("warn:")]
    joined = "\n".join(warnings)
    assert "(setting: gh auth login)" in joined
    assert "(setting: flow.launch_adapter)" in joined
    assert "(setting: capacity.builder_memory_gb)" in joined
    assert "sleep" in joined and "(verify" in joined
    assert len(warnings) == 4


def test_the_checks_pass_on_a_ready_machine_and_never_change_a_power_setting(
    tmp_path, machine, monkeypatch
):
    """REQ-071 AC7: rule 11 (only reads: never powercfg, pmset or a systemctl change)."""
    import autopilot

    for platform in ("linux", "darwin", "win32"):
        monkeypatch.setattr(autopilot, "PLATFORM", platform)
        root = project(tmp_path / platform, ADAPTER)
        lines = autopilot.machine_checks(root)
        assert lines and all(x.startswith(("ok:", "warn:")) for x in lines)
        if platform == "linux":
            assert not [x for x in lines if x.startswith("warn:")]
    for call in machine.calls:
        assert call[0] not in ("powercfg", "pmset", "caffeinate")
        assert call[:1] != ["systemctl"] or call[1] == "is-enabled"


def test_retry_records_the_pull_request_and_refuses_another_word(tmp_path, machine, capsys):
    """REQ-071 AC2: rule 9 (`agk autopilot retry <n>` lifts a hold; kept in the git directory)."""
    import autopilot

    root = project(tmp_path)
    before = tracked_changes(root)
    assert autopilot.main(["retry", "41", "--root", str(root)], now=NOW) == 0
    assert autopilot.retries(root) == {"41": "2026-11-16T12:00:00Z"}
    assert autopilot.main(["retry", "forty", "--root", str(root)], now=NOW) == 2
    assert tracked_changes(root) == before
